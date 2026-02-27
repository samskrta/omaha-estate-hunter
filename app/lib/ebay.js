/**
 * eBay Finding API integration for sold/completed listings lookup.
 *
 * Uses findCompletedItems to get actual sold prices.
 * Requires EBAY_APP_ID environment variable.
 *
 * Get your AppID at: https://developer.ebay.com/my/keys
 * (Production keys → AppID/Client ID)
 */

const FINDING_API_URL = 'https://svcs.ebay.com/services/search/FindingService/v1';

/**
 * Search eBay completed/sold listings for an item.
 * Returns recent sold prices to validate Claude's estimates.
 */
export async function findSoldListings(searchQuery, options = {}) {
  const appId = process.env.EBAY_APP_ID;
  if (!appId) {
    return { available: false, reason: 'EBAY_APP_ID not configured' };
  }

  const {
    maxResults = 8,
    categoryId = null,
    minPrice = null,
    maxPrice = null,
  } = options;

  // Build item filters for SOLD items only
  const itemFilters = [
    { name: 'SoldItemsOnly', value: 'true' },
    { name: 'Condition', value: ['1000', '1500', '2000', '2500', '3000', '4000', '5000', '6000'] },
  ];

  if (minPrice) {
    itemFilters.push({ name: 'MinPrice', value: String(minPrice), paramName: 'Currency', paramValue: 'USD' });
  }
  if (maxPrice) {
    itemFilters.push({ name: 'MaxPrice', value: String(maxPrice), paramName: 'Currency', paramValue: 'USD' });
  }

  // Build URL params
  const params = new URLSearchParams({
    'OPERATION-NAME': 'findCompletedItems',
    'SERVICE-VERSION': '1.13.0',
    'SECURITY-APPNAME': appId,
    'RESPONSE-DATA-FORMAT': 'JSON',
    'REST-PAYLOAD': 'true',
    'keywords': searchQuery,
    'paginationInput.entriesPerPage': String(maxResults),
    'sortOrder': 'EndTimeSoonest',
  });

  if (categoryId) {
    params.set('categoryId', categoryId);
  }

  // Add item filters
  itemFilters.forEach((filter, idx) => {
    params.set(`itemFilter(${idx}).name`, filter.name);
    if (Array.isArray(filter.value)) {
      filter.value.forEach((v, vIdx) => {
        params.set(`itemFilter(${idx}).value(${vIdx})`, v);
      });
    } else {
      params.set(`itemFilter(${idx}).value`, filter.value);
    }
    if (filter.paramName) {
      params.set(`itemFilter(${idx}).paramName`, filter.paramName);
      params.set(`itemFilter(${idx}).paramValue`, filter.paramValue);
    }
  });

  const url = `${FINDING_API_URL}?${params.toString()}`;

  try {
    const response = await fetch(url, {
      headers: { 'Accept': 'application/json' },
    });

    if (!response.ok) {
      throw new Error(`eBay API error: ${response.status}`);
    }

    const data = await response.json();
    const result = data.findCompletedItemsResponse?.[0];

    if (result?.ack?.[0] !== 'Success') {
      const errorMsg = result?.errorMessage?.[0]?.error?.[0]?.message?.[0] || 'Unknown eBay API error';
      throw new Error(errorMsg);
    }

    const items = result?.searchResult?.[0]?.item || [];
    const totalResults = parseInt(result?.paginationOutput?.[0]?.totalEntries?.[0] || '0');

    const soldItems = items.map(item => ({
      title: item.title?.[0] || '',
      soldPrice: parseFloat(item.sellingStatus?.[0]?.currentPrice?.[0]?.__value__ || '0'),
      currency: item.sellingStatus?.[0]?.currentPrice?.[0]?.['@currencyId'] || 'USD',
      soldDate: item.listingInfo?.[0]?.endTime?.[0] || null,
      condition: item.condition?.[0]?.conditionDisplayName?.[0] || 'Unknown',
      listingType: item.listingInfo?.[0]?.listingType?.[0] || 'Unknown',
      imageUrl: item.galleryURL?.[0] || null,
      itemUrl: item.viewItemURL?.[0] || null,
    }));

    // Calculate price statistics
    const prices = soldItems.map(i => i.soldPrice).filter(p => p > 0);
    const stats = prices.length > 0 ? {
      count: prices.length,
      totalResults,
      median: median(prices),
      mean: Math.round(prices.reduce((a, b) => a + b, 0) / prices.length),
      low: Math.min(...prices),
      high: Math.max(...prices),
      recentSales: soldItems.slice(0, 5),
    } : {
      count: 0,
      totalResults,
      median: 0,
      mean: 0,
      low: 0,
      high: 0,
      recentSales: [],
    };

    return { available: true, ...stats };
  } catch (err) {
    console.error(`eBay lookup failed for "${searchQuery}":`, err.message);
    return { available: false, reason: err.message };
  }
}

function median(arr) {
  const sorted = [...arr].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 !== 0
    ? Math.round(sorted[mid])
    : Math.round((sorted[mid - 1] + sorted[mid]) / 2);
}

/**
 * Batch lookup for multiple items. Runs concurrently with a concurrency limit.
 */
export async function batchPriceLookup(items, concurrency = 3) {
  const results = [];

  for (let i = 0; i < items.length; i += concurrency) {
    const batch = items.slice(i, i + concurrency);
    const batchResults = await Promise.allSettled(
      batch.map(async (item) => {
        if (!item.search_query) {
          return { itemName: item.name, ebay: { available: false, reason: 'No search query' } };
        }

        // Parse Claude's estimate to set a reasonable price range filter
        let minPrice = null;
        let maxPrice = null;
        if (item.estimated_value_hint) {
          const matches = item.estimated_value_hint.match(/\$(\d+)/g);
          if (matches) {
            const low = parseInt(matches[0].replace('$', ''));
            const high = parseInt((matches[1] || matches[0]).replace('$', ''));
            // Widen the range to catch more comps
            minPrice = Math.max(1, Math.round(low * 0.3));
            maxPrice = Math.round(high * 3);
          }
        }

        const ebay = await findSoldListings(item.search_query, { minPrice, maxPrice });
        return { itemName: item.name, ebay };
      })
    );

    for (const result of batchResults) {
      if (result.status === 'fulfilled') {
        results.push(result.value);
      } else {
        results.push({ itemName: 'unknown', ebay: { available: false, reason: result.reason?.message } });
      }
    }
  }

  return results;
}
