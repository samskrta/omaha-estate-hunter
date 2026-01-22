'use client';

import { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default marker icons in React-Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

export default function MapView({ sales, onSaleClick }) {
  // Filter sales with valid coordinates
  const mappableSales = sales.filter(sale => sale.latitude && sale.longitude);

  // Calculate center point (Omaha metro center)
  const center = [41.252363, -95.997988];

  if (mappableSales.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-md p-8 text-center text-gray-500">
        <p>No sales with location data available for mapping.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden" style={{ height: '600px' }}>
      <MapContainer
        center={center}
        zoom={10}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {mappableSales.map(sale => (
          <Marker
            key={sale.id}
            position={[sale.latitude, sale.longitude]}
            eventHandlers={{
              click: () => onSaleClick && onSaleClick(sale),
            }}
          >
            <Popup>
              <div className="p-2">
                <h3 className="font-bold text-sm mb-1">{sale.title}</h3>
                <p className="text-xs text-gray-600 mb-1">{sale.company}</p>
                <p className="text-xs text-gray-600 mb-2">{sale.dateDisplay}</p>
                <p className="text-xs">
                  <span className="font-semibold">{sale.photos}</span> photos
                </p>
                <a
                  href={sale.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline text-xs"
                >
                  View Details →
                </a>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
