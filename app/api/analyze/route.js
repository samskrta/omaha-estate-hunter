import { NextResponse } from 'next/server';
import Anthropic from '@anthropic-ai/sdk';
import { batchPriceLookup } from '../../lib/ebay';

export const dynamic = 'force-dynamic';
export const maxDuration = 120; // Allow up to 2 minutes for vision analysis

const SYSTEM_PROMPT = `You are an expert estate sale appraiser and eBay reseller. Analyze this estate sale photo and identify every item that could have meaningful resale value on eBay.

For each item, provide:
- name: The most specific name possible (brand + model + descriptor)
- category: One of [furniture, electronics, appliances, kitchenware, art, collectibles, tools, clothing, jewelry, books, toys, sporting_goods, other]
- brand: Exact brand if visible or identifiable from design
- model: Model name/number if visible or identifiable
- era: Approximate decade or style period
- condition_estimate: Based on visible wear [excellent, good, fair, poor, unknown]
- notable_features: Array of distinguishing details (color, material, included accessories, original packaging, etc.)
- search_query: The exact query you'd type into eBay to find comparable sold listings
- confidence: high (exact brand/model), medium (category + era), low (generic only)
- confidence_reasoning: Brief explanation
- estimated_value_hint: Your rough estimate of resale value (e.g., "$50-100")

Skip items with negligible resale value (<$5 estimated) unless they appear vintage or collectible.

Respond ONLY with a JSON array of items. Be specific — "Pyrex 401 Primary Blue mixing bowl" not "glass bowl".`;

const client = new Anthropic();

// Fetch an image and convert to base64
async function imageToBase64(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Failed to fetch image: ${url}`);
  const buffer = await response.arrayBuffer();
  const base64 = Buffer.from(buffer).toString('base64');
  const contentType = response.headers.get('content-type') || 'image/jpeg';
  return { base64, mediaType: contentType };
}

// Parse Claude's response to extract JSON items
function parseItemsFromResponse(text) {
  // Strip markdown code blocks if present
  let cleaned = text.trim();
  if (cleaned.startsWith('```')) {
    cleaned = cleaned.replace(/^```(?:json)?\n?/, '').replace(/\n?```$/, '');
  }

  try {
    const parsed = JSON.parse(cleaned);
    return Array.isArray(parsed) ? parsed : [parsed];
  } catch {
    // Try to find JSON array in the text
    const match = cleaned.match(/\[[\s\S]*\]/);
    if (match) {
      return JSON.parse(match[0]);
    }
    throw new Error('Could not parse items from Claude response');
  }
}

// Simple string similarity (Dice coefficient - fast and good enough)
function similarity(a, b) {
  const aLower = a.toLowerCase();
  const bLower = b.toLowerCase();
  if (aLower === bLower) return 1;
  if (aLower.length < 2 || bLower.length < 2) return 0;

  const bigrams = new Map();
  for (let i = 0; i < aLower.length - 1; i++) {
    const bigram = aLower.substring(i, i + 2);
    bigrams.set(bigram, (bigrams.get(bigram) || 0) + 1);
  }

  let intersections = 0;
  for (let i = 0; i < bLower.length - 1; i++) {
    const bigram = bLower.substring(i, i + 2);
    const count = bigrams.get(bigram) || 0;
    if (count > 0) {
      bigrams.set(bigram, count - 1);
      intersections++;
    }
  }

  return (2.0 * intersections) / (aLower.length + bLower.length - 2);
}

// Parse a dollar estimate string like "$50-100" → 50
function parseEstimate(hint) {
  if (!hint) return 0;
  const match = hint.match(/\$(\d+)/);
  return match ? parseInt(match[1]) : 0;
}

// Deduplicate items across photos
function deduplicateItems(items, nameThreshold = 0.75, queryThreshold = 0.70) {
  const confidenceRank = { high: 3, medium: 2, low: 1 };
  const sorted = [...items].sort(
    (a, b) => (confidenceRank[b.confidence] || 0) - (confidenceRank[a.confidence] || 0)
  );

  const kept = [];
  for (const item of sorted) {
    let isDuplicate = false;
    for (const existing of kept) {
      if (item.category !== existing.category) continue;
      const nameSim = similarity(item.name, existing.name);
      const querySim = similarity(item.search_query, existing.search_query);
      if (nameSim >= nameThreshold || querySim >= queryThreshold) {
        // Merge notable features
        const existingFeatures = new Set(existing.notable_features || []);
        for (const f of item.notable_features || []) {
          existingFeatures.add(f);
        }
        existing.notable_features = [...existingFeatures];
        isDuplicate = true;
        break;
      }
    }
    if (!isDuplicate) {
      kept.push({ ...item });
    }
  }
  return kept;
}

export async function POST(request) {
  try {
    const { saleId, saleTitle, saleAddress, maxPhotos = 10 } = await request.json();

    if (!saleId) {
      return NextResponse.json({ error: 'saleId is required' }, { status: 400 });
    }

    if (!process.env.ANTHROPIC_API_KEY) {
      return NextResponse.json(
        { error: 'ANTHROPIC_API_KEY not configured' },
        { status: 500 }
      );
    }

    // 1. Fetch all photos for this sale
    const saleResponse = await fetch(
      `https://www.estatesales.net/api/sale-details/${saleId}?include=pictures`,
      {
        headers: {
          'Accept': 'application/json',
          'User-Agent': 'Mozilla/5.0 (compatible)',
        },
      }
    );

    if (!saleResponse.ok) {
      throw new Error(`Failed to fetch sale details: ${saleResponse.status}`);
    }

    const saleData = await saleResponse.json();
    const pictures = saleData.pictures || [];

    if (pictures.length === 0) {
      return NextResponse.json({ items: [], message: 'No photos found for this sale' });
    }

    // Limit photos to avoid huge API costs
    const photosToAnalyze = pictures.slice(0, maxPhotos);

    // 2. Analyze each photo with Claude Vision (concurrent, max 3 at a time)
    const allItems = [];
    const concurrency = 3;
    const context = `Estate sale: "${saleTitle || 'Unknown'}" at ${saleAddress || 'Unknown location'}`;

    for (let i = 0; i < photosToAnalyze.length; i += concurrency) {
      const batch = photosToAnalyze.slice(i, i + concurrency);
      const results = await Promise.allSettled(
        batch.map(async (photo, batchIdx) => {
          const photoIdx = i + batchIdx;
          try {
            const { base64, mediaType } = await imageToBase64(photo.url);

            const response = await client.messages.create({
              model: 'claude-sonnet-4-5-20250929',
              max_tokens: 4096,
              system: SYSTEM_PROMPT,
              messages: [
                {
                  role: 'user',
                  content: [
                    {
                      type: 'image',
                      source: {
                        type: 'base64',
                        media_type: mediaType,
                        data: base64,
                      },
                    },
                    {
                      type: 'text',
                      text: `Analyze this estate sale photo and identify all items with resale value.\n\nContext: ${context}\nPhoto ${photoIdx + 1} of ${photosToAnalyze.length}.\n\nReturn a JSON array of items.`,
                    },
                  ],
                },
              ],
            });

            const text = response.content[0]?.text || '[]';
            const items = parseItemsFromResponse(text);
            return items.map((item) => ({
              ...item,
              photoIndex: photoIdx,
              photoUrl: photo.thumbnailUrl || photo.url,
            }));
          } catch (err) {
            console.error(`Error analyzing photo ${photoIdx}:`, err.message);
            return [];
          }
        })
      );

      for (const result of results) {
        if (result.status === 'fulfilled') {
          allItems.push(...result.value);
        }
      }
    }

    // 3. Deduplicate across photos
    const deduplicated = deduplicateItems(allItems);

    // 4. Look up real eBay sold prices for each item
    let ebayAvailable = false;
    if (process.env.EBAY_APP_ID) {
      try {
        const priceLookups = await batchPriceLookup(deduplicated, 3);

        // Merge eBay data into items
        for (let i = 0; i < deduplicated.length; i++) {
          const lookup = priceLookups.find(
            (r) => r.itemName === deduplicated[i].name
          );
          if (lookup?.ebay?.available && lookup.ebay.count > 0) {
            deduplicated[i].ebay = {
              median: lookup.ebay.median,
              mean: lookup.ebay.mean,
              low: lookup.ebay.low,
              high: lookup.ebay.high,
              count: lookup.ebay.count,
              totalResults: lookup.ebay.totalResults,
              recentSales: lookup.ebay.recentSales,
            };
            ebayAvailable = true;
          }
        }
      } catch (err) {
        console.error('eBay batch lookup failed:', err.message);
      }
    }

    // 5. Sort by value — prefer eBay median, fall back to Claude's estimate
    deduplicated.sort((a, b) => {
      const valueA = a.ebay?.median || parseEstimate(a.estimated_value_hint);
      const valueB = b.ebay?.median || parseEstimate(b.estimated_value_hint);
      return valueB - valueA;
    });

    // 6. Calculate summary stats
    let totalLow = 0;
    let totalHigh = 0;
    let totalEbayMedian = 0;
    for (const item of deduplicated) {
      if (item.ebay) {
        totalLow += item.ebay.low;
        totalHigh += item.ebay.high;
        totalEbayMedian += item.ebay.median;
      } else if (item.estimated_value_hint) {
        const matches = item.estimated_value_hint.match(/\$(\d+)/g);
        if (matches) {
          totalLow += parseInt(matches[0].replace('$', ''));
          totalHigh += parseInt((matches[1] || matches[0]).replace('$', ''));
        }
      }
    }

    return NextResponse.json({
      items: deduplicated,
      summary: {
        photosAnalyzed: photosToAnalyze.length,
        totalPhotos: pictures.length,
        itemsFound: deduplicated.length,
        ebayAvailable,
        estimatedTotalValue: {
          low: totalLow,
          high: totalHigh,
          ...(ebayAvailable && { ebayMedian: totalEbayMedian }),
        },
      },
    });
  } catch (error) {
    console.error('Analysis error:', error);
    return NextResponse.json(
      { error: 'Analysis failed', message: error.message },
      { status: 500 }
    );
  }
}
