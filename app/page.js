import SalesClient from './SalesClient';

// Sale type mapping
const saleTypeNames = {
  1: 'Estate Sale',
  4: 'Moving Sale',
  64: 'Online Only Auction',
  256: 'Moved Offsite To Store',
  512: 'By Appointment',
  1024: 'Online Estate Sale',
};

// Transform API data to our format
function transformSaleData(apiSale) {
  const now = new Date();
  const firstStart = apiSale.firstLocalStartDate?._value ? new Date(apiSale.firstLocalStartDate._value) : null;
  const lastEnd = apiSale.lastLocalEndDate?._value ? new Date(apiSale.lastLocalEndDate._value) : null;

  const isOnline = apiSale.type === 64 || apiSale.type === 1024;
  const isGoingNow = firstStart && lastEnd && now >= firstStart && now <= lastEnd;
  const startsTomorrow = firstStart && !isGoingNow &&
    firstStart.toDateString() === new Date(now.getTime() + 86400000).toDateString();

  const formatDate = (date) => {
    if (!date) return '';
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const formatTime = (date) => {
    if (!date) return '';
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }).toLowerCase();
  };

  let dateDisplay = '';
  if (apiSale.dates && apiSale.dates.length > 0) {
    const firstDate = new Date(apiSale.dates[0].localStartDate._value);
    const lastDate = new Date(apiSale.dates[apiSale.dates.length - 1].localEndDate._value);
    const firstTime = formatTime(firstDate);
    const lastTime = formatTime(new Date(apiSale.dates[0].localEndDate._value));

    if (isOnline && isGoingNow) {
      dateDisplay = `Ends ${formatDate(lastDate)} at ${formatTime(lastDate)}`;
    } else if (apiSale.dates.length === 1) {
      dateDisplay = `${formatDate(firstDate)}, ${firstTime}-${lastTime}`;
    } else {
      dateDisplay = `${formatDate(firstDate)}-${formatDate(lastDate)}`;
    }
  }

  const highlights = [];
  if (apiSale.saleCategories) {
    apiSale.saleCategories.slice(0, 6).forEach(cat => highlights.push(cat.name));
  }
  if (highlights.length === 0) {
    highlights.push(saleTypeNames[apiSale.type] || 'Estate Sale');
    if (apiSale.pictureCount > 100) highlights.push(`${apiSale.pictureCount} Photos`);
  }

  return {
    id: apiSale.id,
    title: apiSale.name,
    company: apiSale.orgName,
    address: `${apiSale.cityName}, ${apiSale.stateCode} ${apiSale.postalCodeNumber}`,
    fullAddress: apiSale.address ? `${apiSale.address}, ${apiSale.cityName}, ${apiSale.stateCode} ${apiSale.postalCodeNumber}` : `${apiSale.cityName}, ${apiSale.stateCode} ${apiSale.postalCodeNumber}`,
    neighborhood: apiSale.cityName,
    dates: `${formatDate(firstStart)}-${formatDate(lastEnd)}`,
    dateDisplay,
    startDate: firstStart ? firstStart.getTime() : null,
    endDate: lastEnd ? lastEnd.getTime() : null,
    photos: apiSale.pictureCount || 0,
    highlights,
    description: apiSale.description || `${saleTypeNames[apiSale.type] || 'Estate Sale'} in ${apiSale.cityName}`,
    saleType: saleTypeNames[apiSale.type] || apiSale.typeName || 'Estate Sale',
    isOnline,
    isGoingNow,
    startsTomorrow,
    url: `https://www.estatesales.net/${apiSale.stateCode}/${apiSale.cityName}/${apiSale.postalCodeNumber}/${apiSale.id}`,
    imageUrl: apiSale.mainPicture?.thumbnailUrl || apiSale.mainPicture?.url || null,
    fullImageUrl: apiSale.mainPicture?.url || null,
    companyLogo: apiSale.orgLogoUrl,
    phone: apiSale.phoneNumbers?.[0] || '',
    latitude: apiSale.latitude,
    longitude: apiSale.longitude
  };
}

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
