import SalesClient from './SalesClient';
import { transformSaleData } from './lib/transformSale';

// Omaha metro coordinates
const OMAHA_LAT = 41.252363;
const OMAHA_LNG = -95.997988;
const SEARCH_RADIUS_MILES = 100;

async function getSales() {
  try {
    // Fetch directly from EstateSales.NET during SSR (no CORS issues on server)
    const API_URL = `https://www.estatesales.net/api/sale-details?bypass=bycoordinatesanddistance:${OMAHA_LAT}_${OMAHA_LNG}_${SEARCH_RADIUS_MILES}&include=mainpicture,dates,salecategories&explicitTypes=DateTime`;

    const response = await fetch(API_URL, {
      cache: 'no-store', // Always fetch fresh data
      headers: {
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (compatible)',
      },
    });

    if (!response.ok) {
      console.error('Failed to fetch sales:', response.status);
      return [];
    }

    const data = await response.json();

    if (data.error) {
      console.error('API returned error:', data.message);
      return [];
    }

    return data.map(transformSaleData);
  } catch (error) {
    console.error('Error fetching sales:', error);
    return [];
  }
}

export default async function OmahaEstateSales() {
  const sales = await getSales();
  const timestamp = Date.now();

  return <SalesClient initialSales={sales} initialTimestamp={timestamp} />;
}
