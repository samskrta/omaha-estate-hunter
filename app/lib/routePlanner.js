/**
 * Route planner for estate sale trips.
 * Optimizes visit order using nearest-neighbor with time-window constraints.
 */

// Haversine distance in miles between two lat/lng points
export function haversineDistance(lat1, lng1, lat2, lng2) {
  const R = 3959; // Earth radius in miles
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// Estimate drive time in minutes (assume 30 mph average for metro driving)
function estimateDriveMinutes(miles) {
  return Math.round((miles / 30) * 60);
}

/**
 * Build an optimized route for visiting sales on a given date.
 *
 * @param {Array} sales - Sales to visit, each with latitude, longitude, schedule[]
 * @param {string} dateKey - ISO date string (YYYY-MM-DD) for the trip day
 * @param {object} startPoint - { latitude, longitude } starting location
 * @returns {object} { route: ordered sales with timing, totalMiles, totalDriveMinutes, googleMapsUrl }
 */
export function planRoute(sales, dateKey, startPoint = null) {
  // Filter to sales that are open on the target date
  const openSales = sales
    .filter((s) => s.latitude && s.longitude && !s.isOnline)
    .map((s) => {
      const daySchedule = s.schedule?.find((d) => d.dateKey === dateKey);
      return daySchedule ? { ...s, daySchedule } : null;
    })
    .filter(Boolean);

  if (openSales.length === 0) {
    return { route: [], totalMiles: 0, totalDriveMinutes: 0, googleMapsUrl: null };
  }

  // Sort by opening time first, then optimize geographically within time windows
  const sorted = [...openSales].sort(
    (a, b) => a.daySchedule.openTime - b.daySchedule.openTime
  );

  // Nearest-neighbor with time awareness
  const start = startPoint || { latitude: sorted[0].latitude, longitude: sorted[0].longitude };
  const visited = [];
  const remaining = new Set(sorted.map((_, i) => i));
  let currentLat = start.latitude;
  let currentLng = start.longitude;
  let currentTime = sorted[0].daySchedule.openTime; // Start at earliest opening

  while (remaining.size > 0) {
    let bestIdx = null;
    let bestScore = Infinity;

    for (const idx of remaining) {
      const sale = sorted[idx];
      const dist = haversineDistance(currentLat, currentLng, sale.latitude, sale.longitude);
      const driveMin = estimateDriveMinutes(dist);
      const arrivalTime = currentTime + driveMin * 60000;

      // Penalty for arriving before it opens (waiting time)
      const waitTime = Math.max(0, sale.daySchedule.openTime - arrivalTime);
      // Penalty for arriving after it closes (missed it)
      const missedPenalty = arrivalTime > sale.daySchedule.closeTime ? 100000 : 0;

      // Score: distance + wait penalty + missed penalty
      const score = dist + (waitTime / 60000) * 0.5 + missedPenalty;

      if (score < bestScore) {
        bestScore = score;
        bestIdx = idx;
      }
    }

    const nextSale = sorted[bestIdx];
    const dist = haversineDistance(currentLat, currentLng, nextSale.latitude, nextSale.longitude);
    const driveMin = estimateDriveMinutes(dist);
    const arrivalTime = currentTime + driveMin * 60000;
    const effectiveArrival = Math.max(arrivalTime, nextSale.daySchedule.openTime);
    const browseMins = 30; // Assume 30 min per sale

    visited.push({
      ...nextSale,
      routeOrder: visited.length + 1,
      distanceFromPrev: Math.round(dist * 10) / 10,
      driveMinutes: driveMin,
      arrivalTime: new Date(effectiveArrival).toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
      }).toLowerCase(),
      waitMinutes: Math.max(0, Math.round((nextSale.daySchedule.openTime - arrivalTime) / 60000)),
      missedIt: arrivalTime > nextSale.daySchedule.closeTime,
    });

    currentLat = nextSale.latitude;
    currentLng = nextSale.longitude;
    currentTime = effectiveArrival + browseMins * 60000;
    remaining.delete(bestIdx);
  }

  // Calculate totals
  const totalMiles = visited.reduce((sum, s) => sum + s.distanceFromPrev, 0);
  const totalDriveMinutes = visited.reduce((sum, s) => sum + s.driveMinutes, 0);

  // Build Google Maps directions URL
  const googleMapsUrl = buildGoogleMapsUrl(visited, startPoint);

  return { route: visited, totalMiles: Math.round(totalMiles * 10) / 10, totalDriveMinutes, googleMapsUrl };
}

function buildGoogleMapsUrl(orderedSales, startPoint) {
  if (orderedSales.length === 0) return null;

  const baseUrl = 'https://www.google.com/maps/dir/';
  const points = [];

  // Start from user's location or first sale
  if (startPoint) {
    points.push(`${startPoint.latitude},${startPoint.longitude}`);
  }

  for (const sale of orderedSales) {
    // Use full address for better Google Maps routing
    points.push(encodeURIComponent(sale.fullAddress));
  }

  return baseUrl + points.join('/');
}

/**
 * Get all unique dates across a set of sales.
 */
export function getAvailableDates(sales) {
  const dateMap = new Map();

  for (const sale of sales) {
    if (!sale.schedule) continue;
    for (const day of sale.schedule) {
      if (!dateMap.has(day.dateKey)) {
        dateMap.set(day.dateKey, { dateKey: day.dateKey, label: day.date, salesCount: 0 });
      }
      dateMap.get(day.dateKey).salesCount++;
    }
  }

  return [...dateMap.values()].sort((a, b) => a.dateKey.localeCompare(b.dateKey));
}
