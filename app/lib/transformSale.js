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
export function transformSaleData(apiSale) {
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

  // Build per-day schedule with open/close times
  const schedule = [];
  if (apiSale.dates && apiSale.dates.length > 0) {
    for (const d of apiSale.dates) {
      const dayStart = d.localStartDate?._value ? new Date(d.localStartDate._value) : null;
      const dayEnd = d.localEndDate?._value ? new Date(d.localEndDate._value) : null;
      if (dayStart && dayEnd) {
        schedule.push({
          date: dayStart.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }),
          dateKey: dayStart.toISOString().split('T')[0],
          open: dayStart.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }).toLowerCase(),
          close: dayEnd.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }).toLowerCase(),
          openTime: dayStart.getTime(),
          closeTime: dayEnd.getTime(),
        });
      }
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
    longitude: apiSale.longitude,
    schedule,
  };
}
