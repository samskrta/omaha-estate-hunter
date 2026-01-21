'use client';

import React, { useState, useMemo, useEffect } from 'react';
import { Star, MapPin, Calendar, Camera, Building2, TrendingUp, Filter, ChevronDown, ChevronUp, Plus, Edit2, Trash2, X, Check, ExternalLink, Clock, RefreshCw, Loader2 } from 'lucide-react';

// Initial company ratings based on user input
const initialCompanies = {
  'Clutter Clearers Consignment': { grade: 'B', notes: 'Good, but pricey' },
  'Blue Moon Estate Sales Of Omaha': { grade: 'C', notes: 'Mid, and pricey' },
};

// Grade configurations
const gradeConfig = {
  'A': { color: 'bg-green-500', textColor: 'text-green-700', bgLight: 'bg-green-100', score: 4 },
  'B': { color: 'bg-blue-500', textColor: 'text-blue-700', bgLight: 'bg-blue-100', score: 3 },
  'C': { color: 'bg-yellow-500', textColor: 'text-yellow-700', bgLight: 'bg-yellow-100', score: 2 },
  'D': { color: 'bg-orange-500', textColor: 'text-orange-700', bgLight: 'bg-orange-100', score: 1 },
  'F': { color: 'bg-red-500', textColor: 'text-red-700', bgLight: 'bg-red-100', score: 0 },
  '?': { color: 'bg-gray-400', textColor: 'text-gray-700', bgLight: 'bg-gray-100', score: 2 },
};

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
    startDate: firstStart,
    endDate: lastEnd,
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
    phone: apiSale.phoneNumbers?.[0] || ''
  };
}

function calculateHuntScore(sale, companies) {
  const company = companies[sale.company];
  const companyGrade = company?.grade || '?';
  const companyScore = gradeConfig[companyGrade].score;
  const photoScore = Math.min(sale.photos / 40, 4);
  const highlightScore = Math.min(sale.highlights.length / 2, 2);
  const inPersonBonus = sale.isOnline ? 0 : 0.5;
  const weightedScore = (companyScore * 0.55) + (photoScore * 0.25) + (highlightScore * 0.15) + (inPersonBonus * 0.05);
  return Math.round((weightedScore / 4) * 100);
}

function getHuntScoreColor(score) {
  if (score >= 70) return 'text-green-600';
  if (score >= 50) return 'text-blue-600';
  if (score >= 30) return 'text-yellow-600';
  return 'text-red-600';
}

function getHuntScoreBg(score) {
  if (score >= 70) return 'bg-green-100 border-green-300';
  if (score >= 50) return 'bg-blue-100 border-blue-300';
  if (score >= 30) return 'bg-yellow-100 border-yellow-300';
  return 'bg-red-100 border-red-300';
}

function GradeBadge({ grade, size = 'md' }) {
  const config = gradeConfig[grade] || gradeConfig['?'];
  const sizeClasses = size === 'sm' ? 'w-6 h-6 text-xs' : 'w-8 h-8 text-sm';
  return (
    <div className={`${config.color} ${sizeClasses} rounded-full flex items-center justify-center text-white font-bold shadow-sm`}>
      {grade}
    </div>
  );
}

function StatusBadge({ sale }) {
  if (sale.isGoingNow) {
    return (
      <span className="px-2 py-1 bg-green-500 text-white text-xs font-semibold rounded-full flex items-center gap-1">
        <Clock className="w-3 h-3" /> LIVE NOW
      </span>
    );
  }
  if (sale.startsTomorrow) {
    return (
      <span className="px-2 py-1 bg-orange-500 text-white text-xs font-semibold rounded-full">
        STARTS TOMORROW
      </span>
    );
  }
  if (sale.isOnline) {
    return (
      <span className="px-2 py-1 bg-purple-500 text-white text-xs font-semibold rounded-full">
        ONLINE
      </span>
    );
  }
  return null;
}

function CompanyManager({ companies, setCompanies, onClose, allSaleCompanies }) {
  const [newCompany, setNewCompany] = useState('');
  const [newGrade, setNewGrade] = useState('C');
  const [newNotes, setNewNotes] = useState('');
  const [editingCompany, setEditingCompany] = useState(null);

  const handleAdd = () => {
    if (newCompany.trim()) {
      setCompanies({
        ...companies,
        [newCompany.trim()]: { grade: newGrade, notes: newNotes }
      });
      setNewCompany('');
      setNewGrade('C');
      setNewNotes('');
    }
  };

  const handleDelete = (companyName) => {
    const updated = { ...companies };
    delete updated[companyName];
    setCompanies(updated);
  };

  const handleUpdate = (companyName, grade, notes) => {
    setCompanies({
      ...companies,
      [companyName]: { grade, notes }
    });
    setEditingCompany(null);
  };

  const unratedCompanies = allSaleCompanies.filter(c => !companies[c]);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[85vh] overflow-hidden">
        <div className="p-6 border-b border-gray-200 flex justify-between items-center bg-gradient-to-r from-blue-600 to-blue-800 text-white">
          <h2 className="text-xl font-bold">Manage Company Ratings</h2>
          <button onClick={onClose} className="p-2 hover:bg-white hover:bg-opacity-20 rounded-full">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {unratedCompanies.length > 0 && (
            <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-sm text-yellow-800">
                <strong>{unratedCompanies.length} unrated companies</strong> in current listings
              </p>
            </div>
          )}

          <div className="mb-6 p-4 bg-gray-50 rounded-lg">
            <h3 className="font-semibold mb-3 text-gray-700">Add Company Rating</h3>
            <div className="flex flex-col gap-3">
              <div className="flex flex-col sm:flex-row gap-3">
                <input
                  type="text"
                  placeholder="Company name"
                  value={newCompany}
                  onChange={(e) => setNewCompany(e.target.value)}
                  list="unrated-companies"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <datalist id="unrated-companies">
                  {unratedCompanies.map(c => <option key={c} value={c} />)}
                </datalist>
                <select
                  value={newGrade}
                  onChange={(e) => setNewGrade(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  {Object.keys(gradeConfig).filter(g => g !== '?').map(g => (
                    <option key={g} value={g}>Grade: {g}</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-3">
                <input
                  type="text"
                  placeholder="Notes (e.g., 'Good prices, well organized')"
                  value={newNotes}
                  onChange={(e) => setNewNotes(e.target.value)}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <button
                  onClick={handleAdd}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 whitespace-nowrap"
                >
                  <Plus className="w-4 h-4" /> Add
                </button>
              </div>
            </div>
          </div>

          <h3 className="font-semibold mb-3 text-gray-700">Your Ratings</h3>
          <div className="space-y-3">
            {Object.entries(companies).length === 0 ? (
              <p className="text-gray-500 text-center py-4">No companies rated yet.</p>
            ) : (
              Object.entries(companies).map(([name, data]) => (
                <div key={name} className="flex items-center gap-3 p-3 bg-white border border-gray-200 rounded-lg">
                  {editingCompany === name ? (
                    <>
                      <select
                        defaultValue={data.grade}
                        onChange={(e) => handleUpdate(name, e.target.value, data.notes)}
                        className="px-2 py-1 border border-gray-300 rounded"
                      >
                        {Object.keys(gradeConfig).filter(g => g !== '?').map(g => (
                          <option key={g} value={g}>{g}</option>
                        ))}
                      </select>
                      <span className="flex-1 font-medium truncate">{name}</span>
                      <input
                        type="text"
                        defaultValue={data.notes}
                        onBlur={(e) => handleUpdate(name, data.grade, e.target.value)}
                        className="flex-1 px-2 py-1 border border-gray-300 rounded"
                      />
                      <button onClick={() => setEditingCompany(null)} className="p-1 hover:bg-gray-100 rounded">
                        <Check className="w-4 h-4 text-green-600" />
                      </button>
                    </>
                  ) : (
                    <>
                      <GradeBadge grade={data.grade} size="sm" />
                      <span className="flex-1 font-medium truncate">{name}</span>
                      <span className="text-gray-500 text-sm flex-1 truncate">{data.notes}</span>
                      <button onClick={() => setEditingCompany(name)} className="p-1 hover:bg-gray-100 rounded">
                        <Edit2 className="w-4 h-4 text-gray-500" />
                      </button>
                      <button onClick={() => handleDelete(name)} className="p-1 hover:bg-gray-100 rounded">
                        <Trash2 className="w-4 h-4 text-red-500" />
                      </button>
                    </>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        <div className="p-4 border-t border-gray-200 bg-gray-50">
          <p className="text-sm text-gray-600">
            <strong>Tip:</strong> Company ratings = 55% of Hunt Score. Rate companies you&apos;ve visited!
          </p>
        </div>
      </div>
    </div>
  );
}

function SaleCard({ sale, companies, onClick, isExpanded }) {
  const huntScore = calculateHuntScore(sale, companies);
  const companyData = companies[sale.company];
  const companyGrade = companyData?.grade || '?';
  const [imgError, setImgError] = useState(false);

  return (
    <div
      className={`bg-white rounded-xl shadow-md hover:shadow-xl transition-all duration-200 overflow-hidden cursor-pointer border-2 ${isExpanded ? 'border-blue-500 ring-2 ring-blue-200' : 'border-transparent'}`}
      onClick={onClick}
    >
      <div className="relative h-48 bg-gray-200">
        {sale.imageUrl && !imgError ? (
          <img
            src={sale.imageUrl}
            alt={sale.title}
            className="w-full h-full object-cover"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gray-300 text-gray-500">
            <Camera className="w-12 h-12" />
          </div>
        )}
        <div className="absolute top-3 left-3 flex gap-2">
          <div className={`px-3 py-1 rounded-full border ${getHuntScoreBg(huntScore)} flex items-center gap-2`}>
            <TrendingUp className={`w-4 h-4 ${getHuntScoreColor(huntScore)}`} />
            <span className={`font-bold ${getHuntScoreColor(huntScore)}`}>{huntScore}</span>
          </div>
          <StatusBadge sale={sale} />
        </div>
        <div className="absolute top-3 right-3">
          <GradeBadge grade={companyGrade} />
        </div>
        <div className="absolute bottom-3 right-3 bg-black bg-opacity-70 text-white px-2 py-1 rounded-lg flex items-center gap-1 text-sm">
          <Camera className="w-4 h-4" />
          {sale.photos}
        </div>
      </div>

      <div className="p-4">
        <h3 className="font-bold text-lg text-gray-800 mb-1 line-clamp-1">{sale.title}</h3>
        <div className="flex items-center gap-2 text-sm text-gray-600 mb-2">
          <Building2 className="w-4 h-4 flex-shrink-0" />
          <span className="truncate">{sale.company}</span>
          {companyData?.notes && (
            <span className="text-gray-400 truncate">• {companyData.notes}</span>
          )}
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-600 mb-2">
          <MapPin className="w-4 h-4 flex-shrink-0" />
          <span className="truncate">{sale.address}</span>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-600 mb-3">
          <Calendar className="w-4 h-4 flex-shrink-0" />
          <span>{sale.dateDisplay}</span>
        </div>
        <div className="flex flex-wrap gap-1">
          {sale.highlights.slice(0, 3).map((highlight, idx) => (
            <span key={idx} className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full">
              {highlight}
            </span>
          ))}
          {sale.highlights.length > 3 && (
            <span className="px-2 py-1 bg-gray-100 text-gray-500 text-xs rounded-full">
              +{sale.highlights.length - 3} more
            </span>
          )}
        </div>
      </div>

      {isExpanded && (
        <div className="px-4 pb-4 border-t border-gray-100 mt-2 pt-4">
          <p className="text-gray-700 mb-4">{sale.description}</p>
          <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
            <div>
              <span className="text-gray-500">Sale Type:</span>
              <span className="ml-2 font-medium">{sale.saleType}</span>
            </div>
            {sale.phone && (
              <div>
                <span className="text-gray-500">Phone:</span>
                <span className="ml-2 font-medium">{sale.phone}</span>
              </div>
            )}
          </div>
          <a
            href={sale.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            onClick={(e) => e.stopPropagation()}
          >
            <ExternalLink className="w-4 h-4" />
            View on EstateSales.NET
          </a>
        </div>
      )}
    </div>
  );
}

export default function OmahaEstateSales() {
  const [sales, setSales] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [companies, setCompanies] = useState(initialCompanies);
  const [showCompanyManager, setShowCompanyManager] = useState(false);
  const [expandedSale, setExpandedSale] = useState(null);
  const [sortBy, setSortBy] = useState('score');
  const [filterCompany, setFilterCompany] = useState('all');
  const [showFilters, setShowFilters] = useState(false);
  const [hideOnline, setHideOnline] = useState(false);

  const fetchSales = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/sales');
      if (!response.ok) throw new Error('Failed to fetch sales');
      const data = await response.json();
      const transformedSales = data.map(transformSaleData);
      setSales(transformedSales);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSales();
  }, []);

  const allCompanies = useMemo(() => {
    return [...new Set(sales.map(s => s.company))].sort();
  }, [sales]);

  const processedSales = useMemo(() => {
    let filtered = [...sales];
    if (filterCompany !== 'all') {
      filtered = filtered.filter(s => s.company === filterCompany);
    }
    if (hideOnline) {
      filtered = filtered.filter(s => !s.isOnline);
    }
    return filtered.sort((a, b) => {
      switch (sortBy) {
        case 'score':
          return calculateHuntScore(b, companies) - calculateHuntScore(a, companies);
        case 'date':
          return (a.startDate || 0) - (b.startDate || 0);
        case 'photos':
          return b.photos - a.photos;
        default:
          return 0;
      }
    });
  }, [sortBy, filterCompany, companies, hideOnline, sales]);

  const ratedCount = Object.keys(companies).length;
  const unratedCount = allCompanies.filter(c => !companies[c]).length;

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-gradient-to-r from-blue-600 to-blue-800 text-white py-6 px-4 shadow-lg">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold mb-2">🏠 Omaha Estate Sale Hunter</h1>
              <p className="text-blue-100">Live data from EstateSales.NET • Find the best sales for resale</p>
              {lastUpdated && (
                <p className="text-blue-200 text-sm mt-1">
                  Last updated: {lastUpdated.toLocaleTimeString()} • {sales.length} active sales
                </p>
              )}
            </div>
            <button
              onClick={fetchSales}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-white bg-opacity-20 hover:bg-opacity-30 rounded-lg transition-colors disabled:opacity-50"
            >
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <RefreshCw className="w-5 h-5" />}
              Refresh
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-4">
        {error && (
          <div className="bg-red-100 border border-red-300 text-red-700 px-4 py-3 rounded-lg mb-4">
            Error loading sales: {error}. <button onClick={fetchSales} className="underline">Try again</button>
          </div>
        )}

        <div className="bg-white rounded-xl shadow-md p-4 mb-6">
          <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
              >
                <Filter className="w-4 h-4" />
                Filters
                {showFilters ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
              <button
                onClick={() => setShowCompanyManager(true)}
                className="flex items-center gap-2 px-4 py-2 bg-blue-100 text-blue-700 hover:bg-blue-200 rounded-lg transition-colors"
              >
                <Star className="w-4 h-4" />
                Companies ({ratedCount} rated{unratedCount > 0 && `, ${unratedCount} unrated`})
              </button>
            </div>
            <div className="text-sm text-gray-600">
              Showing <strong>{processedSales.length}</strong> of {sales.length} sales
            </div>
          </div>

          {showFilters && (
            <div className="mt-4 pt-4 border-t border-gray-200 flex flex-wrap gap-4 items-end">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Sort by</label>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="score">Hunt Score (Best First)</option>
                  <option value="date">Date (Soonest First)</option>
                  <option value="photos">Photos (Most First)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Company</label>
                <select
                  value={filterCompany}
                  onChange={(e) => setFilterCompany(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">All Companies</option>
                  {allCompanies.map(c => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="hideOnline"
                  checked={hideOnline}
                  onChange={(e) => setHideOnline(e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                />
                <label htmlFor="hideOnline" className="text-sm text-gray-700">In-person only</label>
              </div>
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl shadow-md p-4 mb-6">
          <h3 className="font-semibold text-gray-700 mb-3">Hunt Score Guide</h3>
          <div className="flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
              <span>70+ Excellent</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-blue-500"></div>
              <span>50-69 Good</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
              <span>30-49 Fair</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500"></div>
              <span>0-29 Skip</span>
            </div>
          </div>
        </div>

        {loading && sales.length === 0 && (
          <div className="text-center py-12">
            <Loader2 className="w-12 h-12 animate-spin mx-auto text-blue-500 mb-4" />
            <p className="text-gray-500">Loading estate sales...</p>
          </div>
        )}

        {(!loading || sales.length > 0) && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {processedSales.map(sale => (
              <SaleCard
                key={sale.id}
                sale={sale}
                companies={companies}
                isExpanded={expandedSale === sale.id}
                onClick={() => setExpandedSale(expandedSale === sale.id ? null : sale.id)}
              />
            ))}
          </div>
        )}

        {!loading && processedSales.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            <p>No sales match your filters.</p>
          </div>
        )}
      </div>

      {showCompanyManager && (
        <CompanyManager
          companies={companies}
          setCompanies={setCompanies}
          onClose={() => setShowCompanyManager(false)}
          allSaleCompanies={allCompanies}
        />
      )}

      <footer className="bg-gray-800 text-gray-400 py-6 px-4 mt-12">
        <div className="max-w-6xl mx-auto text-center text-sm">
          <p>Estate sale discovery tool for Omaha/Council Bluffs metro area</p>
          <p className="mt-1">Live data from EstateSales.NET • Click any sale to view full details</p>
        </div>
      </footer>
    </div>
  );
}
