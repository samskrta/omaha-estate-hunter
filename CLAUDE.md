# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Omaha Estate Sale Hunter is a Next.js 14 web application that aggregates and ranks estate sales in the Omaha/Council Bluffs metro area. The app fetches real-time data from the EstateSales.NET API and provides a custom "Hunt Score" algorithm to help resellers identify the most promising sales.

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: JavaScript (no TypeScript)
- **Styling**: Tailwind CSS
- **UI Components**: Custom components with Lucide React icons
- **Data Fetching**: Server-side rendering + client-side refresh
- **Mapping**: Leaflet + React-Leaflet 4.2.1 (dynamically loaded to avoid SSR issues)
- **Image Gallery**: Custom lightbox component with keyboard navigation

## Development Commands

```bash
# Install dependencies
npm install

# Run development server (http://localhost:3000)
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

## Architecture

### Hybrid SSR + Client Architecture

**Important**: The app uses a hybrid approach with server-side rendering (SSR) for initial data and client-side interactivity.

- `app/page.js` is a **server component** that fetches data at request time and passes it to the client
- `app/SalesClient.js` is a **client component** with all interactive features (filters, sorting, company manager)
- `app/api/sales/route.js` proxies requests to EstateSales.NET with proper headers to avoid CORS
- Initial data is server-rendered into HTML for better performance and SEO
- Users can still click "Refresh" to fetch updated data client-side
- API route URL is simplified (no `select` parameter) to avoid API errors with certain fields

### Hunt Score Algorithm

The core feature is a weighted scoring system to rank estate sales (app/page.js:104-113):

- **Company Rating (55%)**: Grade A-F based on user ratings
- **Photo Count (25%)**: More photos = higher score (capped at 4.0)
- **Highlights (15%)**: Sale categories/features
- **In-Person Bonus (5%)**: 0.5 points for non-online sales

Score ranges:
- 70+: Excellent (green)
- 50-69: Good (blue)
- 30-49: Fair (yellow)
- 0-29: Skip (red)

### State Management

All state is managed with React hooks in the main component:
- `companies`: Company ratings stored in localStorage-like state (initialized from `initialCompanies`)
- `sales`: Raw sale data from API
- `processedSales`: Filtered and sorted sales (computed via useMemo)
- `expandedSale`: Currently expanded sale card
- Filters: `sortBy`, `filterCompany`, `hideOnline`

### API Data Structure

The EstateSales.NET API returns sales with this structure:
- `id`, `name`, `orgName` (company)
- `address`, `cityName`, `stateCode`, `postalCodeNumber`
- `type`, `typeName` (sale type enum)
- `pictureCount`, `mainPicture` (image data)
- `dates[]` array with `localStartDate`/`localEndDate`
- `saleCategories[]` (highlights)
- `firstLocalStartDate`, `lastLocalEndDate` (computed dates)

The `transformSaleData()` function (app/page.js:33-102) converts this to the internal format.

### Sale Type Mapping

Sale types are integer flags (app/page.js:23-30):
- 1: Estate Sale
- 4: Moving Sale
- 64: Online Only Auction
- 256: Moved Offsite To Store
- 512: By Appointment
- 1024: Online Estate Sale

### Component Structure

The app is split into server and client components:

**Server Component** (`app/page.js`):
- `OmahaEstateSales`: Main async component that fetches data server-side
- `getSales()`: Fetches from `/api/sales` during SSR
- `transformSaleData()`: Transforms API data to UI format

**Client Component** (`app/SalesClient.js`):
- `SalesClient`: Main interactive component (receives initial data as props)
- `SaleCard`: Individual sale card with expand/collapse and gallery button
- `CompanyManager`: Modal for managing company ratings
- `GradeBadge`: Letter grade display (A-F)
- `StatusBadge`: Shows LIVE NOW, STARTS TOMORROW, ONLINE badges

**Additional Components**:
- `MapView` (`app/MapView.js`): Leaflet map showing all sales with markers (client-only, dynamically imported)
- `ImageGallery` (`app/ImageGallery.js`): Full-screen image gallery with thumbnails and keyboard navigation

### Styling Approach

- Tailwind utility classes throughout
- Gradient backgrounds on header: `from-blue-600 to-blue-800`
- Responsive grid: `md:grid-cols-2 lg:grid-cols-3`
- Grade colors configured in `gradeConfig` object (app/page.js:13-20)
- Hunt score colors use functions: `getHuntScoreColor()`, `getHuntScoreBg()`

## Key Files

- `app/page.js`: Server component that fetches data and renders client component
- `app/SalesClient.js`: Main interactive UI with list/map views, filtering, sorting
- `app/MapView.js`: Leaflet map component (dynamically loaded)
- `app/ImageGallery.js`: Fullscreen image viewer with API integration
- `app/layout.js`: Root layout with metadata
- `app/globals.css`: Tailwind imports only
- `app/api/sales/route.js`: Proxy API route to EstateSales.NET
- `next.config.js`: Image domain whitelist for EstateSales.NET CDN

## Key Features

### View Modes
- **List View**: Grid of sale cards (default)
- **Map View**: Interactive Leaflet map with markers for each sale
- Toggle between views with List/Map buttons in the toolbar

### Image Gallery
- Click "Gallery" button on any sale card to open full-screen gallery
- Fetches all images from EstateSales.NET API
- Keyboard navigation: Arrow keys (← →) to navigate, Escape to close
- Thumbnail strip at bottom for quick navigation
- Falls back to main image if API fails

## API Configuration

The search is configured for Omaha metro (app/page.js:438-440):
```javascript
const OMAHA_LAT = 41.252363;
const OMAHA_LNG = -95.997988;
const SEARCH_RADIUS_MILES = 100;
```

API includes: `mainpicture,dates,salecategories`
API selects: All needed fields including `firstLocalStartDate`, `lastLocalEndDate`, `phoneNumbers`, `description`, etc.

## Date Handling

- All dates come from API as `{_value: "ISO-8601-string"}` objects
- Convert with `new Date(apiSale.firstLocalStartDate._value)`
- Display formatting uses `toLocaleDateString()` and `toLocaleTimeString()`
- Status badges (LIVE NOW, STARTS TOMORROW) calculated by comparing current time to sale dates
