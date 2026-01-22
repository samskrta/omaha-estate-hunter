'use client';

import { useState, useEffect } from 'react';
import { X, ChevronLeft, ChevronRight, ExternalLink, Loader2 } from 'lucide-react';

export default function ImageGallery({ sale, onClose }) {
  const [images, setImages] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Fetch sale details to get all images
    const fetchImages = async () => {
      setLoading(true);
      setError(null);
      try {
        // Parse the sale URL to get the state, city, zip, and id
        const urlParts = sale.url.split('/');
        const saleId = urlParts[urlParts.length - 1];

        // Fetch from EstateSales.NET API
        const response = await fetch(
          `https://www.estatesales.net/api/sale-details/${saleId}?include=pictures`
        );

        if (!response.ok) throw new Error('Failed to fetch images');

        const data = await response.json();

        // Extract image URLs
        const imageList = data.pictures?.map(pic => ({
          url: pic.url,
          thumbnailUrl: pic.thumbnailUrl,
          description: pic.description || ''
        })) || [];

        setImages(imageList);
      } catch (err) {
        console.error('Error fetching images:', err);
        setError('Unable to load images. Click "View on EstateSales.NET" to see all photos.');
        // Fallback to main image if available
        if (sale.fullImageUrl) {
          setImages([{ url: sale.fullImageUrl, thumbnailUrl: sale.imageUrl, description: '' }]);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchImages();
  }, [sale]);

  const nextImage = () => {
    setCurrentIndex((prev) => (prev + 1) % images.length);
  };

  const prevImage = () => {
    setCurrentIndex((prev) => (prev - 1 + images.length) % images.length);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowRight') nextImage();
    if (e.key === 'ArrowLeft') prevImage();
    if (e.key === 'Escape') onClose();
  };

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [images]);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center z-50 p-4">
      <div className="max-w-6xl w-full h-full flex flex-col">
        {/* Header */}
        <div className="flex justify-between items-start mb-4 text-white">
          <div className="flex-1">
            <h2 className="text-2xl font-bold mb-1">{sale.title}</h2>
            <p className="text-gray-300">{sale.company}</p>
            <p className="text-sm text-gray-400 mt-1">
              {loading ? 'Loading images...' : `${currentIndex + 1} of ${images.length} photos`}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white hover:bg-opacity-20 rounded-full transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Main Image */}
        <div className="flex-1 flex items-center justify-center relative">
          {loading ? (
            <div className="text-center text-white">
              <Loader2 className="w-12 h-12 animate-spin mx-auto mb-4" />
              <p>Loading gallery...</p>
            </div>
          ) : error ? (
            <div className="text-center text-white max-w-md">
              <p className="mb-4">{error}</p>
              <a
                href={sale.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <ExternalLink className="w-4 h-4" />
                View on EstateSales.NET
              </a>
            </div>
          ) : images.length > 0 ? (
            <>
              <img
                src={images[currentIndex].url}
                alt={images[currentIndex].description || sale.title}
                className="max-h-full max-w-full object-contain"
              />

              {/* Navigation Arrows */}
              {images.length > 1 && (
                <>
                  <button
                    onClick={prevImage}
                    className="absolute left-4 top-1/2 -translate-y-1/2 p-3 bg-black bg-opacity-50 hover:bg-opacity-70 rounded-full text-white transition-colors"
                  >
                    <ChevronLeft className="w-6 h-6" />
                  </button>
                  <button
                    onClick={nextImage}
                    className="absolute right-4 top-1/2 -translate-y-1/2 p-3 bg-black bg-opacity-50 hover:bg-opacity-70 rounded-full text-white transition-colors"
                  >
                    <ChevronRight className="w-6 h-6" />
                  </button>
                </>
              )}
            </>
          ) : (
            <div className="text-center text-white">
              <p>No images available</p>
            </div>
          )}
        </div>

        {/* Image Description */}
        {!loading && !error && images[currentIndex]?.description && (
          <div className="mt-4 text-white text-center">
            <p>{images[currentIndex].description}</p>
          </div>
        )}

        {/* Thumbnail Strip */}
        {!loading && !error && images.length > 1 && (
          <div className="mt-4 flex gap-2 overflow-x-auto pb-2">
            {images.map((img, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentIndex(idx)}
                className={`flex-shrink-0 w-20 h-20 rounded-lg overflow-hidden border-2 transition-all ${
                  idx === currentIndex
                    ? 'border-blue-500 ring-2 ring-blue-300'
                    : 'border-gray-600 hover:border-gray-400'
                }`}
              >
                <img
                  src={img.thumbnailUrl || img.url}
                  alt={`Thumbnail ${idx + 1}`}
                  className="w-full h-full object-cover"
                />
              </button>
            ))}
          </div>
        )}

        {/* Footer */}
        <div className="mt-4 text-center">
          <a
            href={sale.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
            View Full Listing on EstateSales.NET
          </a>
        </div>
      </div>
    </div>
  );
}
