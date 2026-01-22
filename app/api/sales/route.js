import { NextResponse } from 'next/server';

// Omaha metro coordinates
const OMAHA_LAT = 41.252363;
const OMAHA_LNG = -95.997988;
const SEARCH_RADIUS_MILES = 100;

const API_URL = `https://www.estatesales.net/api/sale-details?bypass=bycoordinatesanddistance:${OMAHA_LAT}_${OMAHA_LNG}_${SEARCH_RADIUS_MILES}&include=mainpicture,dates,salecategories&explicitTypes=DateTime`;

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET() {
  try {
    const response = await fetch(API_URL, {
      method: 'GET',
      headers: {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.estatesales.net/NE-IA/Omaha-Council-Bluffs',
        'Origin': 'https://www.estatesales.net',
      },
      cache: 'no-store',
    });

    if (!response.ok) {
      console.error(`EstateSales.NET API error: ${response.status} ${response.statusText}`);
      const text = await response.text();
      console.error('Response body:', text.substring(0, 500));
      throw new Error(`EstateSales.NET API returned ${response.status}`);
    }

    const data = await response.json();

    return NextResponse.json(data, {
      headers: {
        'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=600',
      },
    });
  } catch (error) {
    console.error('Error fetching sales:', error.message);

    // Return a more detailed error for debugging
    return NextResponse.json(
      {
        error: 'Failed to fetch sales data',
        message: error.message,
        hint: 'EstateSales.NET may be blocking requests from this server'
      },
      { status: 500 }
    );
  }
}
