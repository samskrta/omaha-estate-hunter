import { NextResponse } from 'next/server';

// Omaha metro coordinates
const OMAHA_LAT = 41.252363;
const OMAHA_LNG = -95.997988;
const SEARCH_RADIUS_MILES = 100;

const API_URL = `https://www.estatesales.net/api/sale-details?bypass=bycoordinatesanddistance:${OMAHA_LAT}_${OMAHA_LNG}_${SEARCH_RADIUS_MILES}&include=mainpicture,dates,salecategories&select=id,orgName,address,cityName,name,type,typeName,pictureCount,mainPicture,dates,postalCodeNumber,stateCode,firstLocalStartDate,lastLocalEndDate,phoneNumbers,orgLogoUrl,description,saleCategories&explicitTypes=DateTime`;

export async function GET() {
  try {
    const response = await fetch(API_URL, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; OmahaEstateHunter/1.0)',
      },
      next: { revalidate: 300 } // Cache for 5 minutes
    });

    if (!response.ok) {
      throw new Error(`EstateSales.NET API returned ${response.status}`);
    }

    const data = await response.json();

    return NextResponse.json(data, {
      headers: {
        'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=600',
      },
    });
  } catch (error) {
    console.error('Error fetching sales:', error);
    return NextResponse.json(
      { error: 'Failed to fetch sales data' },
      { status: 500 }
    );
  }
}
