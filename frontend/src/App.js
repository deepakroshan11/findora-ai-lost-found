import React, { useState, useEffect, useCallback } from 'react';
import { Camera, MapPin, Search, Bell, Upload, X, Check, AlertCircle, TrendingUp, Filter, Clock, Sparkles } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const FindoraApp = () => {
  const [activeTab, setActiveTab] = useState('home');
  const [items, setItems] = useState([]);
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(false);
  const [userId, setUserId] = useState(localStorage.getItem('findora_user_id') || null);
  const [stats, setStats] = useState(null);
  const [filterType, setFilterType] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    category: 'wallet',
    location: '',
    latitude: null,
    longitude: null,
    itemType: 'lost',
    rewardAmount: 0,
    contactInfo: '',
    image: null
  });
  
  const [previewUrl, setPreviewUrl] = useState(null);
  const [notification, setNotification] = useState(null);
  const [formErrors, setFormErrors] = useState({});

  // Auto-register user on mount
  useEffect(() => {
    if (!userId) {
      autoRegisterUser();
    }
  }, [userId]);

  // Fetch data based on active tab
  useEffect(() => {
    if (activeTab === 'browse') {
      fetchItems();
    }
    if (activeTab === 'home') {
      fetchStats();
    }
    if (activeTab === 'matches') {
      fetchMatches();
    }
  }, [activeTab]);

  const autoRegisterUser = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/users/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: `user${Date.now()}@findora.app`,
          name: 'User',
          phone: ''
        })
      });
      
      if (!response.ok) throw new Error('Registration failed');
      
      const data = await response.json();
      setUserId(data.user_id);
      localStorage.setItem('findora_user_id', data.user_id);
    } catch (error) {
      console.error('Registration failed:', error);
      showNotification('Failed to register user', 'error');
    }
  };

  const showNotification = useCallback((message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/stats`);
      if (!response.ok) throw new Error('Failed to fetch stats');
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Stats fetch error:', error);
    }
  };

  const fetchItems = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/api/items`);
      if (!response.ok) throw new Error('Failed to fetch items');
      const data = await response.json();
      setItems(data);
    } catch (error) {
      showNotification('Failed to load items', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchMatches = async () => {
    try {
      setLoading(true);
      const allMatches = [];

      // Fetch items first if not already loaded
      let itemsToCheck = items;
      if (items.length === 0) {
        const response = await fetch(`${API_BASE}/api/items`);
        if (response.ok) {
          itemsToCheck = await response.json();
          setItems(itemsToCheck);
        }
      }

      for (const item of itemsToCheck) {
        const res = await fetch(`${API_BASE}/api/matches/${item.item_id}`);
        if (!res.ok) continue;
        
        const data = await res.json();
        const highConfidence = data.filter(
          m => m.confidence_score >= 0.8
        );

        // Add item details to each match for display
        const matchesWithDetails = highConfidence.map(match => ({
          ...match,
          sourceItem: item
        }));

        allMatches.push(...matchesWithDetails);
      }

      setMatches(allMatches);
    } catch (err) {
      console.error('Match fetch error:', err);
      showNotification('Failed to load matches', 'error');
    } finally {
      setLoading(false);
    }
  };

  const validateForm = () => {
    const errors = {};
    
    if (!formData.title.trim()) {
      errors.title = 'Title is required';
    }
    
    if (!formData.description.trim()) {
      errors.description = 'Description is required';
    } else if (formData.description.length < 10) {
      errors.description = 'Description must be at least 10 characters';
    }
    
    if (!formData.location.trim()) {
      errors.location = 'Location is required';
    }
    
    if (!formData.contactInfo.trim()) {
      errors.contactInfo = 'Contact information is required';
    } else if (!formData.contactInfo.includes('@') && !/^\+?[\d\s-()]+$/.test(formData.contactInfo)) {
      errors.contactInfo = 'Please provide a valid email or phone number';
    }
    
    if (!formData.image) {
      errors.image = 'Image is required';
    }
    
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 10 * 1024 * 1024) {
        showNotification('Image too large! Max 10MB', 'error');
        return;
      }
      
      const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
      if (!validTypes.includes(file.type)) {
        showNotification('Invalid file type. Please upload JPG, PNG, or WEBP', 'error');
        return;
      }
      
      setFormData({ ...formData, image: file });
      setFormErrors({ ...formErrors, image: null });
      
      const reader = new FileReader();
      reader.onloadend = () => setPreviewUrl(reader.result);
      reader.readAsDataURL(file);
    }
  };

  const resetForm = () => {
    setFormData({
      title: '',
      description: '',
      category: 'wallet',
      location: '',
      latitude: null,
      longitude: null,
      itemType: 'lost',
      rewardAmount: 0,
      contactInfo: '',
      image: null
    });
    setPreviewUrl(null);
    setFormErrors({});
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      showNotification('Please fix all errors before submitting', 'error');
      return;
    }

    try {
      setLoading(true);
      
      const data = new FormData();
      data.append('title', formData.title.trim());
      data.append('description', formData.description.trim());
      data.append('category', formData.category);
      data.append('location', formData.location.trim());
      data.append('item_type', formData.itemType);
      data.append('reward_amount', formData.rewardAmount);
      data.append('contact_info', formData.contactInfo.trim());
      data.append('user_id', userId);
      data.append('image', formData.image);
      
      if (formData.latitude) data.append('latitude', formData.latitude);
      if (formData.longitude) data.append('longitude', formData.longitude);

      const response = await fetch(`${API_BASE}/api/items/report`, {
        method: 'POST',
        body: data
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Submission failed');
      }

      showNotification('Item reported successfully! AI is searching for matches...', 'success');
      resetForm();
      setTimeout(() => setActiveTab('browse'), 2000);
    } catch (error) {
      console.error('Submission error:', error);
      showNotification(error.message || 'Failed to report item', 'error');
    } finally {
      setLoading(false);
    }
  };

  const getLocation = () => {
    if (!navigator.geolocation) {
      showNotification('Geolocation not supported by your browser', 'error');
      return;
    }

    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setFormData({
          ...formData,
          latitude: position.coords.latitude,
          longitude: position.coords.longitude
        });
        showNotification('Location captured successfully!', 'success');
        setLoading(false);
      },
      (error) => {
        let message = 'Could not get location';
        if (error.code === error.PERMISSION_DENIED) {
          message = 'Location permission denied. Please enable location access.';
        } else if (error.code === error.POSITION_UNAVAILABLE) {
          message = 'Location information unavailable';
        } else if (error.code === error.TIMEOUT) {
          message = 'Location request timed out';
        }
        showNotification(message, 'error');
        setLoading(false);
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  // Filter items based on type and search query
  const filteredItems = items.filter(item => {
    const matchesType = filterType === 'all' || item.item_type === filterType;
    const matchesSearch = !searchQuery || 
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.location.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesType && matchesSearch;
  });

  const Notification = () => {
    if (!notification) return null;
    const bgColor = notification.type === 'success' ? 'bg-emerald-500' : 'bg-rose-500';
    
    return (
      <div className={`fixed top-4 right-4 ${bgColor} text-white px-6 py-3 rounded-xl shadow-2xl z-50 flex items-center gap-2 animate-slide-in`}>
        {notification.type === 'success' ? <Check size={20} /> : <AlertCircle size={20} />}
        <span className="font-medium">{notification.message}</span>
      </div>
    );
  };

  const HomeTab = () => (
    <div className="max-w-6xl mx-auto py-12 px-4">
      <div className="text-center mb-16">
        <h1 className="text-7xl font-black mb-4 bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
          Findora
        </h1>
        <p className="text-2xl text-gray-700 font-semibold mb-2">AI-Powered Lost & Found Platform</p>
        <p className="text-lg text-gray-500">Reuniting people with their belongings using smart technology</p>
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-16">
          <div className="bg-white p-8 rounded-2xl shadow-lg hover:shadow-xl transition-shadow border border-gray-100">
            <div className="flex items-center justify-between mb-3">
              <TrendingUp className="text-indigo-600" size={32} />
              <div className="text-4xl font-bold text-indigo-900">{stats.total_items}</div>
            </div>
            <div className="text-sm font-medium text-gray-600">Total Items</div>
          </div>
          <div className="bg-white p-8 rounded-2xl shadow-lg hover:shadow-xl transition-shadow border border-gray-100">
            <div className="flex items-center justify-between mb-3">
              <Search className="text-rose-600" size={32} />
              <div className="text-4xl font-bold text-rose-900">{stats.lost_items}</div>
            </div>
            <div className="text-sm font-medium text-gray-600">Lost Items</div>
          </div>
          <div className="bg-white p-8 rounded-2xl shadow-lg hover:shadow-xl transition-shadow border border-gray-100">
            <div className="flex items-center justify-between mb-3">
              <Camera className="text-emerald-600" size={32} />
              <div className="text-4xl font-bold text-emerald-900">{stats.found_items}</div>
            </div>
            <div className="text-sm font-medium text-gray-600">Found Items</div>
          </div>
          <div className="bg-white p-8 rounded-2xl shadow-lg hover:shadow-xl transition-shadow border border-gray-100">
            <div className="flex items-center justify-between mb-3">
              <Check className="text-purple-600" size={32} />
              <div className="text-4xl font-bold text-purple-900">{stats.matched_items}</div>
            </div>
            <div className="text-sm font-medium text-gray-600">Matched</div>
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-8 mb-16">
        <button
          onClick={() => {
            setFormData({ ...formData, itemType: 'lost' });
            setActiveTab('report');
          }}
          className="group bg-gradient-to-br from-rose-500 to-rose-600 hover:from-rose-600 hover:to-rose-700 text-white p-12 rounded-3xl shadow-xl transition-all hover:scale-105 hover:shadow-2xl"
        >
          <Search size={64} className="mx-auto mb-6 group-hover:scale-110 transition-transform" />
          <h3 className="text-4xl font-bold mb-4">Lost Something?</h3>
          <p className="text-xl opacity-90">Report your lost item and our AI will help you find it</p>
        </button>

        <button
          onClick={() => {
            setFormData({ ...formData, itemType: 'found' });
            setActiveTab('report');
          }}
          className="group bg-gradient-to-br from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-white p-12 rounded-3xl shadow-xl transition-all hover:scale-105 hover:shadow-2xl"
        >
          <Camera size={64} className="mx-auto mb-6 group-hover:scale-110 transition-transform" />
          <h3 className="text-4xl font-bold mb-4">Found Something?</h3>
          <p className="text-xl opacity-90">Help return it to the rightful owner</p>
        </button>
      </div>

      <div className="bg-white p-10 rounded-3xl shadow-xl border border-gray-100">
        <h2 className="text-4xl font-bold mb-10 text-center text-gray-900">How It Works</h2>
        <div className="grid md:grid-cols-3 gap-8">
          {[
            { 
              num: 1, 
              title: 'Upload & Describe', 
              desc: 'Take a photo and describe your item with as much detail as possible', 
              color: 'indigo',
              icon: Upload
            },
            { 
              num: 2, 
              title: 'AI Analyzes', 
              desc: 'Our advanced AI analyzes images, text, and location to find matches', 
              color: 'purple',
              icon: Search
            },
            { 
              num: 3, 
              title: 'Get Matched', 
              desc: 'Receive instant notifications when a potential match is discovered', 
              color: 'emerald',
              icon: Bell
            }
          ].map((step) => {
            const Icon = step.icon;
            return (
              <div key={step.num} className="text-center">
                <div className={`bg-gradient-to-br from-${step.color}-500 to-${step.color}-600 text-white w-20 h-20 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg`}>
                  <Icon size={36} />
                </div>
                <h3 className="font-bold text-xl mb-3 text-gray-900">{step.title}</h3>
                <p className="text-gray-600">{step.desc}</p>
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-12 text-center">
        <div className="inline-flex items-center gap-6 bg-white px-8 py-4 rounded-full shadow-lg border border-gray-100">
          <span className="flex items-center gap-2 text-sm text-gray-600">
            <span>🤖</span>
            <span className="font-medium">AI-Powered</span>
          </span>
          <span className="w-px h-4 bg-gray-300"></span>
          <span className="flex items-center gap-2 text-sm text-gray-600">
            <span>🔒</span>
            <span className="font-medium">Secure & Private</span>
          </span>
          <span className="w-px h-4 bg-gray-300"></span>
          <span className="flex items-center gap-2 text-sm text-gray-600">
            <span>⚡</span>
            <span className="font-medium">Fast Matching</span>
          </span>
        </div>
      </div>
    </div>
  );

  const ReportTab = () => (
    <div className="max-w-3xl mx-auto py-8 px-4">
      <div className="mb-8">
        <h2 className="text-5xl font-bold mb-3 text-gray-900">
          Report {formData.itemType === 'lost' ? 'Lost' : 'Found'} Item
        </h2>
        <p className="text-lg text-gray-600">Our AI will automatically search for potential matches in our database</p>
      </div>

      <div className="space-y-6">
        <div className="flex gap-4 p-2 bg-gray-100 rounded-2xl">
          <button
            onClick={() => setFormData({ ...formData, itemType: 'lost' })}
            className={`flex-1 py-4 rounded-xl font-bold text-lg transition-all ${
              formData.itemType === 'lost' 
                ? 'bg-rose-500 text-white shadow-lg scale-105' 
                : 'text-gray-600 hover:bg-gray-200'
            }`}
          >
            Lost Item
          </button>
          <button
            onClick={() => setFormData({ ...formData, itemType: 'found' })}
            className={`flex-1 py-4 rounded-xl font-bold text-lg transition-all ${
              formData.itemType === 'found' 
                ? 'bg-emerald-500 text-white shadow-lg scale-105' 
                : 'text-gray-600 hover:bg-gray-200'
            }`}
          >
            Found Item
          </button>
        </div>

        <div>
          <label className="block font-bold mb-3 text-lg text-gray-900">
            Item Photo <span className="text-rose-500">*</span>
          </label>
          <div className={`border-3 border-dashed rounded-2xl p-10 text-center transition-all ${
            formErrors.image ? 'border-rose-300 bg-rose-50' : 'border-gray-300 hover:border-indigo-400 hover:bg-gray-50'
          }`}>
            {previewUrl ? (
              <div className="relative">
                <img 
                  src={previewUrl} 
                  alt="Preview" 
                  className="max-h-96 mx-auto rounded-xl shadow-xl object-contain" 
                />
                <button
                  onClick={() => {
                    setPreviewUrl(null);
                    setFormData({ ...formData, image: null });
                  }}
                  className="absolute top-4 right-4 bg-rose-500 text-white p-3 rounded-full hover:bg-rose-600 shadow-lg transition-all hover:scale-110"
                  aria-label="Remove image"
                >
                  <X size={20} />
                </button>
              </div>
            ) : (
              <label className="cursor-pointer block">
                <Upload size={64} className="mx-auto text-gray-400 mb-4" />
                <p className="text-gray-700 text-xl font-medium mb-1">Click to upload image</p>
                <p className="text-gray-500 text-sm">Max 10MB • JPG, PNG, WEBP</p>
                <input
                  type="file"
                  accept="image/jpeg,image/jpg,image/png,image/webp"
                  onChange={handleImageChange}
                  className="hidden"
                  aria-label="Upload image"
                />
              </label>
            )}
          </div>
          {formErrors.image && (
            <p className="mt-2 text-sm text-rose-600 flex items-center gap-1">
              <AlertCircle size={16} />
              {formErrors.image}
            </p>
          )}
        </div>

        <div>
          <label className="block font-bold mb-3 text-lg text-gray-900">
            Title <span className="text-rose-500">*</span>
          </label>
          <input
            type="text"
            value={formData.title}
            onChange={(e) => {
              setFormData({ ...formData, title: e.target.value });
              if (formErrors.title) setFormErrors({ ...formErrors, title: null });
            }}
            placeholder="e.g., Black Leather Wallet"
            className={`w-full px-5 py-4 border-2 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-lg transition-all ${
              formErrors.title ? 'border-rose-300 bg-rose-50' : 'border-gray-300'
            }`}
          />
          {formErrors.title && (
            <p className="mt-2 text-sm text-rose-600 flex items-center gap-1">
              <AlertCircle size={16} />
              {formErrors.title}
            </p>
          )}
        </div>

        <div>
          <label className="block font-bold mb-3 text-lg text-gray-900">
            Category <span className="text-rose-500">*</span>
          </label>
          <select
            value={formData.category}
            onChange={(e) => setFormData({ ...formData, category: e.target.value })}
            className="w-full px-5 py-4 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 text-lg"
          >
            <option value="wallet">Wallet</option>
            <option value="phone">Phone</option>
            <option value="keys">Keys</option>
            <option value="bag">Bag/Backpack</option>
            <option value="jewelry">Jewelry</option>
            <option value="documents">Documents</option>
            <option value="electronics">Electronics</option>
            <option value="clothing">Clothing</option>
            <option value="accessories">Accessories</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div>
          <label className="block font-bold mb-3 text-lg text-gray-900">
            Description <span className="text-rose-500">*</span>
          </label>
          <textarea
            value={formData.description}
            onChange={(e) => {
              setFormData({ ...formData, description: e.target.value });
              if (formErrors.description) setFormErrors({ ...formErrors, description: null });
            }}
            placeholder="Describe the item in detail: color, size, brand, distinctive features, where and when it was lost/found..."
            rows={5}
            className={`w-full px-5 py-4 border-2 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-lg transition-all ${
              formErrors.description ? 'border-rose-300 bg-rose-50' : 'border-gray-300'
            }`}
          />
          <div className="flex justify-between items-center mt-2">
            {formErrors.description && (
              <p className="text-sm text-rose-600 flex items-center gap-1">
                <AlertCircle size={16} />
                {formErrors.description}
              </p>
            )}
            <p className="text-sm text-gray-500 ml-auto">
              {formData.description.length} characters
            </p>
          </div>
        </div>

        <div>
          <label className="block font-bold mb-3 text-lg text-gray-900">
            Location <span className="text-rose-500">*</span>
          </label>
          <div className="flex gap-3">
            <input
              type="text"
              value={formData.location}
              onChange={(e) => {
                setFormData({ ...formData, location: e.target.value });
                if (formErrors.location) setFormErrors({ ...formErrors, location: null });
              }}
              placeholder="e.g., Central Bus Station, Main Street, Downtown Mall"
              className={`flex-1 px-5 py-4 border-2 rounded-xl focus:ring-2 focus:ring-indigo-500 text-lg transition-all ${
                formErrors.location ? 'border-rose-300 bg-rose-50' : 'border-gray-300'
              }`}
            />
            <button
              onClick={getLocation}
              disabled={loading}
              className="px-6 py-4 bg-indigo-500 text-white rounded-xl hover:bg-indigo-600 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-lg hover:shadow-xl transition-all"
              aria-label="Get current location"
            >
              <MapPin size={20} />
              <span className="hidden sm:inline">GPS</span>
            </button>
          </div>
          {formErrors.location && (
            <p className="mt-2 text-sm text-rose-600 flex items-center gap-1">
              <AlertCircle size={16} />
              {formErrors.location}
            </p>
          )}
          {formData.latitude && (
            <p className="text-sm text-emerald-600 mt-2 font-medium flex items-center gap-1">
              <Check size={16} />
              GPS coordinates captured ({formData.latitude.toFixed(4)}, {formData.longitude.toFixed(4)})
            </p>
          )}
        </div>

        <div>
          <label className="block font-bold mb-3 text-lg text-gray-900">
            Contact Info <span className="text-rose-500">*</span>
          </label>
          <input
            type="text"
            value={formData.contactInfo}
            onChange={(e) => {
              setFormData({ ...formData, contactInfo: e.target.value });
              if (formErrors.contactInfo) setFormErrors({ ...formErrors, contactInfo: null });
            }}
            placeholder="Email address or phone number"
            className={`w-full px-5 py-4 border-2 rounded-xl focus:ring-2 focus:ring-indigo-500 text-lg transition-all ${
              formErrors.contactInfo ? 'border-rose-300 bg-rose-50' : 'border-gray-300'
            }`}
          />
          {formErrors.contactInfo && (
            <p className="mt-2 text-sm text-rose-600 flex items-center gap-1">
              <AlertCircle size={16} />
              {formErrors.contactInfo}
            </p>
          )}
        </div>

        {formData.itemType === 'lost' && (
          <div>
            <label className="block font-bold mb-3 text-lg text-gray-900">
              Reward Amount (Optional)
            </label>
            <div className="relative">
              <span className="absolute left-5 top-1/2 -translate-y-1/2 text-gray-500 text-lg font-medium">$</span>
              <input
                type="number"
                value={formData.rewardAmount || ''}
                onChange={(e) => setFormData({ ...formData, rewardAmount: parseFloat(e.target.value) || 0 })}
                placeholder="0"
                min="0"
                step="0.01"
                className="w-full pl-10 pr-5 py-4 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 text-lg"
              />
            </div>
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={loading}
          className={`w-full py-6 rounded-2xl font-bold text-white text-xl shadow-xl ${
            formData.itemType === 'lost' 
              ? 'bg-gradient-to-r from-rose-500 to-rose-600 hover:from-rose-600 hover:to-rose-700' 
              : 'bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700'
          } ${loading ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105 transition-all hover:shadow-2xl'}`}
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              Processing...
            </span>
          ) : (
            `Report ${formData.itemType === 'lost' ? 'Lost' : 'Found'} Item`
          )}
        </button>
      </div>
    </div>
  );

  const BrowseTab = () => (
    <div className="max-w-7xl mx-auto py-8 px-4">
      <div className="mb-8">
        <h2 className="text-5xl font-bold mb-6 text-gray-900">Browse Items</h2>
        
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              placeholder="Search by title, description, or location..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-4 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 text-lg"
            />
          </div>
          
          <div className="flex gap-2">
            <button
              onClick={() => setFilterType('all')}
              className={`px-6 py-4 rounded-xl font-semibold transition-all ${
                filterType === 'all'
                  ? 'bg-indigo-500 text-white shadow-lg'
                  : 'bg-white text-gray-700 border-2 border-gray-300 hover:border-indigo-300'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilterType('lost')}
              className={`px-6 py-4 rounded-xl font-semibold transition-all ${
                filterType === 'lost'
                  ? 'bg-rose-500 text-white shadow-lg'
                  : 'bg-white text-gray-700 border-2 border-gray-300 hover:border-rose-300'
              }`}
            >
              Lost
            </button>
            <button
              onClick={() => setFilterType('found')}
              className={`px-6 py-4 rounded-xl font-semibold transition-all ${
                filterType === 'found'
                  ? 'bg-emerald-500 text-white shadow-lg'
                  : 'bg-white text-gray-700 border-2 border-gray-300 hover:border-emerald-300'
              }`}
            >
              Found
            </button>
          </div>
        </div>
      </div>
      
      {loading ? (
        <div className="text-center py-24">
          <div className="w-20 h-20 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-6"></div>
          <p className="text-2xl text-gray-600 font-medium">Loading items...</p>
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="text-center py-24 bg-white rounded-3xl border-2 border-dashed border-gray-300">
          <Search size={80} className="mx-auto text-gray-300 mb-6" />
          <p className="text-2xl text-gray-700 font-bold mb-2">
            {searchQuery || filterType !== 'all' ? 'No matching items found' : 'No items reported yet'}
          </p>
          <p className="text-gray-500 mb-8 text-lg">
            {searchQuery || filterType !== 'all' 
              ? 'Try adjusting your search or filters' 
              : 'Be the first to report a lost or found item'}
          </p>
          {!searchQuery && filterType === 'all' && (
            <button
              onClick={() => setActiveTab('report')}
              className="px-10 py-4 bg-indigo-500 text-white rounded-xl hover:bg-indigo-600 font-bold text-lg shadow-lg hover:shadow-xl transition-all hover:scale-105"
            >
              Report First Item
            </button>
          )}
        </div>
      ) : (
        <>
          <p className="text-gray-600 mb-6 text-lg">
            Showing {filteredItems.length} {filteredItems.length === 1 ? 'item' : 'items'}
          </p>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredItems.map((item) => (
              <div 
                key={item.item_id} 
                className="bg-white rounded-2xl shadow-lg overflow-hidden hover:shadow-2xl transition-all hover:scale-105 border border-gray-100"
              >
                <div className="relative h-64 bg-gradient-to-br from-gray-100 to-gray-200">
                  {item.image_path && (
                    <img 
                      src={`${API_BASE}${item.image_path}`} 
                      alt={item.title} 
                      className="w-full h-full object-cover" 
                    />
                  )}
                  <div className={`absolute top-4 right-4 px-4 py-2 rounded-xl text-white text-sm font-bold shadow-xl ${
                    item.item_type === 'lost' ? 'bg-rose-500' : 'bg-emerald-500'
                  }`}>
                    {item.item_type === 'lost' ? 'LOST' : 'FOUND'}
                  </div>
                </div>
                <div className="p-6">
                  <h3 className="font-bold text-2xl mb-3 text-gray-900">{item.title}</h3>
                  <p className="text-gray-600 text-sm mb-4 line-clamp-2">{item.description}</p>
                  <div className="flex items-center text-sm text-gray-500 mb-3">
                    <MapPin size={18} className="mr-2 flex-shrink-0" />
                    <span className="line-clamp-1">{item.location}</span>
                  </div>
                  <div className="flex items-center text-xs text-gray-400 mb-4">
                    <Clock size={16} className="mr-1" />
                    {new Date(item.created_at).toLocaleDateString('en-US', { 
                      year: 'numeric', 
                      month: 'short', 
                      day: 'numeric' 
                    })}
                  </div>
                  {item.reward_amount > 0 && (
                    <div className="bg-emerald-50 border-2 border-emerald-200 rounded-xl px-4 py-3 text-emerald-700 font-bold text-sm flex items-center justify-between">
                      <span>Reward Offered</span>
                      <span className="text-lg">${item.reward_amount}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );

  const MatchesTab = () => (
    <div className="max-w-6xl mx-auto py-10 px-4">
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-4">
          <Sparkles className="text-purple-600" size={48} />
          <h2 className="text-5xl font-bold text-gray-900">AI Matches</h2>
        </div>
        <p className="text-lg text-gray-600">
          High-confidence matches found by our AI (80%+ confidence score)
        </p>
      </div>

      {loading ? (
        <div className="text-center py-24">
          <div className="w-20 h-20 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-6"></div>
          <p className="text-2xl text-gray-600 font-medium">Analyzing matches...</p>
        </div>
      ) : matches.length === 0 ? (
        <div className="text-center py-24 bg-white rounded-3xl border-2 border-dashed border-gray-300">
          <Sparkles size={80} className="mx-auto text-gray-300 mb-6" />
          <p className="text-2xl text-gray-700 font-bold mb-2">No high-confidence matches yet</p>
          <p className="text-gray-500 text-lg mb-8">
            Our AI will notify you when potential matches are found
          </p>
          <button
            onClick={() => setActiveTab('report')}
            className="px-10 py-4 bg-purple-500 text-white rounded-xl hover:bg-purple-600 font-bold text-lg shadow-lg hover:shadow-xl transition-all hover:scale-105"
          >
            Report an Item
          </button>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-6">
          {matches.map((match, index) => (
            <div 
              key={index} 
              className="bg-white p-8 rounded-2xl shadow-lg hover:shadow-xl transition-all border border-gray-100"
            >
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                  <Sparkles className="text-purple-600" size={24} />
                  <h3 className="text-xl font-bold text-gray-900">Match Found</h3>
                </div>
                <div className={`px-4 py-2 rounded-xl text-white text-sm font-bold ${
                  match.confidence_score >= 0.9 
                    ? 'bg-emerald-500' 
                    : 'bg-purple-500'
                }`}>
                  {match.confidence_score >= 0.9 ? 'High Match' : 'Good Match'}
                </div>
              </div>

              {match.sourceItem && (
                <div className="mb-6 p-4 bg-gray-50 rounded-xl">
                  <p className="text-sm text-gray-500 mb-2">Source Item</p>
                  <h4 className="font-bold text-lg text-gray-900 mb-1">
                    {match.sourceItem.title}
                  </h4>
                  <p className="text-sm text-gray-600 line-clamp-2">
                    {match.sourceItem.description}
                  </p>
                </div>
              )}

              <div className="space-y-4">
                <div>
                  <p className="text-sm font-semibold text-gray-700 mb-2">
                    Match Confidence
                  </p>
                  <div className="w-full bg-gray-200 h-6 rounded-full overflow-hidden">
                    <div
                      className={`h-6 rounded-full transition-all duration-500 ${
                        match.confidence_score >= 0.9 
                          ? 'bg-gradient-to-r from-emerald-500 to-emerald-600' 
                          : 'bg-gradient-to-r from-purple-500 to-purple-600'
                      }`}
                      style={{
                        width: `${Math.round(match.confidence_score * 100)}%`
                      }}
                    />
                  </div>
                  <p className={`mt-2 text-2xl font-bold ${
                    match.confidence_score >= 0.9 ? 'text-emerald-700' : 'text-purple-700'
                  }`}>
                    {Math.round(match.confidence_score * 100)}%
                  </p>
                </div>

                {match.matched_item_id && (
                  <div className="pt-4 border-t border-gray-200">
                    <p className="text-sm text-gray-500">
                      Matched Item ID: <span className="font-mono text-gray-700">{match.matched_item_id}</span>
                    </p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50">
      <Notification />

      <header className="bg-white shadow-md sticky top-0 z-40 border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-5 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <div className="bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 p-3 rounded-2xl shadow-lg">
              <Search size={32} className="text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-black bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                Findora
              </h1>
              <p className="text-xs text-gray-500 font-medium">AI-Powered Platform</p>
            </div>
          </div>
          <button 
            className="relative p-3 hover:bg-gray-100 rounded-xl transition-colors"
            aria-label="Notifications"
          >
            <Bell size={26} />
            <span className="absolute top-2 right-2 w-2.5 h-2.5 bg-rose-500 rounded-full animate-pulse"></span>
          </button>
        </div>
      </header>

      <nav className="bg-white border-b shadow-sm sticky top-[88px] z-30">
        <div className="max-w-7xl mx-auto px-4 flex gap-1">
          {[
            { id: 'home', label: 'Home', icon: '🏠' },
            { id: 'report', label: 'Report Item', icon: '📝' },
            { id: 'browse', label: 'Browse', icon: '🔍' },
            { id: 'matches', label: 'Matches', icon: '🧠' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-6 py-4 font-bold border-b-3 transition-all ${
                activeTab === tab.id
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      <main className="pb-16">
        {activeTab === 'home' && <HomeTab />}
        {activeTab === 'report' && <ReportTab />}
        {activeTab === 'browse' && <BrowseTab />}
        {activeTab === 'matches' && <MatchesTab />}
      </main>

      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-8">
            <p className="text-3xl font-bold mb-3">Findora</p>
            <p className="text-gray-400 text-lg mb-6">AI-Powered Lost & Found Platform</p>
            <p className="text-gray-500 mb-4">
              Advanced Computer Vision • Natural Language Processing • Smart Matching
            </p>
          </div>
          <div className="flex flex-wrap justify-center gap-8 text-sm text-gray-400 border-t border-gray-800 pt-8">
            <span className="flex items-center gap-2">✨ AI-Powered</span>
            <span className="flex items-center gap-2">🔒 Secure</span>
            <span className="flex items-center gap-2">⚡ Fast</span>
            <span className="flex items-center gap-2">🎯 Accurate</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default FindoraApp;