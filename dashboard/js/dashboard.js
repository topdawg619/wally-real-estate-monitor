/**
 * Real Estate Dashboard JavaScript
 * Handles property loading, filtering, favorites, and user interactions
 */

class RealEstateDashboard {
    constructor() {
        this.currentTab = 'properties';
        this.properties = [];
        this.favorites = new Set();
        this.filters = {
            zip_codes: [],
            price_min: null,
            price_max: null,
            source: null,
            sort: 'updated'
        };
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadInitialData();
        this.setupAutoRefresh();
    }
    
    setupEventListeners() {
        // Tab switching
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });
        
        // Filter application
        document.getElementById('apply-filters').addEventListener('click', () => {
            this.applyFilters();
        });
        
        // Modal close
        document.getElementById('modal-close').addEventListener('click', () => {
            this.closeModal();
        });
        
        // Close modal on outside click
        document.getElementById('property-modal').addEventListener('click', (e) => {
            if (e.target.id === 'property-modal') {
                this.closeModal();
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModal();
            }
        });
    }
    
    async loadInitialData() {
        await Promise.all([
            this.loadProperties(),
            this.loadFavorites(),
            this.loadStats(),
            this.loadNewListings(),
            this.loadActivity()
        ]);
    }
    
    setupAutoRefresh() {
        // Refresh data every 5 minutes
        setInterval(() => {
            if (document.visibilityState === 'visible') {
                this.loadInitialData();
            }
        }, 5 * 60 * 1000);
    }
    
    switchTab(tabName) {
        // Update active tab
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        
        // Show tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');
        
        // Show/hide filters
        const filtersEl = document.getElementById('property-filters');
        if (tabName === 'properties') {
            filtersEl.style.display = 'flex';
        } else {
            filtersEl.style.display = 'none';
        }
        
        this.currentTab = tabName;
        
        // Load tab-specific data if needed
        switch (tabName) {
            case 'new-listings':
                this.loadNewListings();
                break;
            case 'favorites':
                this.loadFavorites();
                break;
            case 'activity':
                this.loadActivity();
                break;
            case 'stats':
                this.loadStats();
                break;
        }
    }
    
    async loadProperties() {
        this.showLoading();
        
        try {
            const params = new URLSearchParams();
            
            if (this.filters.zip_codes.length > 0) {
                params.append('zip_codes', this.filters.zip_codes.join(','));
            }
            if (this.filters.price_min) {
                params.append('price_min', this.filters.price_min);
            }
            if (this.filters.price_max) {
                params.append('price_max', this.filters.price_max);
            }
            if (this.filters.source) {
                params.append('source', this.filters.source);
            }
            params.append('sort', this.filters.sort);
            params.append('limit', '100');
            
            const response = await fetch(`/api/properties?${params}`);
            const data = await response.json();
            
            this.properties = data.properties;
            this.renderProperties(this.properties, 'properties-grid');
            this.updateHeaderStats();
            
        } catch (error) {
            console.error('Error loading properties:', error);
            this.showError('Failed to load properties');
        } finally {
            this.hideLoading();
        }
    }
    
    async loadNewListings() {
        try {
            const response = await fetch('/api/new-listings?hours=48&limit=20');
            const data = await response.json();
            
            this.renderProperties(data.new_listings, 'new-listings-grid');
            
        } catch (error) {
            console.error('Error loading new listings:', error);
        }
    }
    
    async loadFavorites() {
        try {
            const response = await fetch('/api/favorites');
            const data = await response.json();
            
            // Update favorites set
            this.favorites = new Set(data.favorites.map(f => f.id));
            
            this.renderProperties(data.favorites, 'favorites-grid');
            this.updateFavoriteButtons();
            
        } catch (error) {
            console.error('Error loading favorites:', error);
        }
    }
    
    async loadActivity() {
        try {
            const response = await fetch('/api/activity?days=7&limit=50');
            const data = await response.json();
            
            this.renderActivity(data.activity);
            
        } catch (error) {
            console.error('Error loading activity:', error);
        }
    }
    
    async loadStats() {
        try {
            const response = await fetch('/api/stats');
            const data = await response.json();
            
            this.renderStats(data.stats);
            
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }
    
    renderProperties(properties, containerId) {
        const container = document.getElementById(containerId);
        const template = document.getElementById('property-card-template');
        
        if (!properties || properties.length === 0) {
            container.innerHTML = '<div class="text-center text-muted">No properties found</div>';
            return;
        }
        
        container.innerHTML = '';
        
        properties.forEach(property => {
            const clone = template.content.cloneNode(true);
            const card = clone.querySelector('.property-card');
            
            // Set property ID
            card.dataset.propertyId = property.id;
            
            // Add click handler
            card.addEventListener('click', () => {
                this.showPropertyModal(property.id);
            });
            
            // Set property data
            clone.querySelector('.property-price').textContent = this.formatPrice(property.price);
            clone.querySelector('.property-address').textContent = property.address;
            clone.querySelector('.bedrooms').textContent = property.bedrooms || '-';
            clone.querySelector('.bathrooms').textContent = property.bathrooms || '-';
            clone.querySelector('.square-feet').textContent = this.formatNumber(property.square_feet) || '-';
            clone.querySelector('.source-badge').textContent = property.source;
            clone.querySelector('.listing-date').textContent = this.formatDate(property.first_seen);
            
            // Set badges
            const badge = clone.querySelector('.property-badge');
            if (this.isNewListing(property.first_seen)) {
                badge.textContent = 'NEW';
                badge.style.display = 'block';
            } else {
                badge.style.display = 'none';
            }
            
            // Set favorite status
            const favoriteBtn = clone.querySelector('.property-favorite');
            const heartIcon = favoriteBtn.querySelector('i');
            
            if (this.favorites.has(property.id)) {
                favoriteBtn.classList.add('favorited');
                heartIcon.className = 'fas fa-heart';
            } else {
                favoriteBtn.classList.remove('favorited');
                heartIcon.className = 'far fa-heart';
            }
            
            // Add favorite click handler
            favoriteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleFavorite(property.id, favoriteBtn);
            });
            
            container.appendChild(clone);
        });
    }
    
    renderActivity(activities) {
        const container = document.getElementById('activity-feed');
        const template = document.getElementById('activity-item-template');
        
        if (!activities || activities.length === 0) {
            container.innerHTML = '<div class="text-center text-muted">No recent activity</div>';
            return;
        }
        
        container.innerHTML = '';
        
        activities.forEach(activity => {
            const clone = template.content.cloneNode(true);
            
            // Set icon based on activity type
            const icon = clone.querySelector('.activity-icon i');
            switch (activity.activity_type) {
                case 'new_listing':
                    icon.className = 'fas fa-plus-circle';
                    break;
                case 'price_decrease':
                    icon.className = 'fas fa-arrow-down';
                    clone.querySelector('.activity-icon').style.background = '#28a745';
                    break;
                case 'price_increase':
                    icon.className = 'fas fa-arrow-up';
                    clone.querySelector('.activity-icon').style.background = '#dc3545';
                    break;
                default:
                    icon.className = 'fas fa-home';
            }
            
            // Set content
            clone.querySelector('.activity-description').textContent = activity.description;
            clone.querySelector('.activity-property').textContent = activity.address;
            clone.querySelector('.activity-time').textContent = this.formatRelativeTime(activity.timestamp);
            
            container.appendChild(clone);
        });
    }
    
    renderStats(stats) {
        const container = document.getElementById('stats-grid');
        container.innerHTML = '';
        
        const statsData = [
            {
                icon: 'fa-building',
                value: stats.total_properties || 0,
                label: 'Active Properties'
            },
            {
                icon: 'fa-dollar-sign',
                value: this.formatPrice(stats.avg_price) || '$0',
                label: 'Average Price'
            },
            {
                icon: 'fa-chart-line',
                value: stats.recent_activity || 0,
                label: 'Recent Activity (7d)'
            },
            {
                icon: 'fa-map-marker-alt',
                value: (stats.by_zip_code || []).length,
                label: 'ZIP Codes Monitored'
            }
        ];
        
        const template = document.getElementById('stat-card-template');
        
        statsData.forEach(stat => {
            const clone = template.content.cloneNode(true);
            
            clone.querySelector('.stat-icon i').className = `fas ${stat.icon}`;
            clone.querySelector('.stat-value').textContent = stat.value;
            clone.querySelector('.stat-label').textContent = stat.label;
            
            container.appendChild(clone);
        });
        
        // Add ZIP code breakdown
        if (stats.by_zip_code && stats.by_zip_code.length > 0) {
            const zipBreakdown = document.createElement('div');
            zipBreakdown.className = 'stat-card';
            zipBreakdown.innerHTML = `
                <div class="stat-icon">
                    <i class="fas fa-list"></i>
                </div>
                <div class="stat-content">
                    <div class="stat-label mb-1">Properties by ZIP Code</div>
                    ${stats.by_zip_code.map(zip => 
                        `<div style="font-size: 0.9rem; margin-bottom: 0.25rem;">
                            <strong>${zip.zip_code}:</strong> ${zip.count} properties (avg: ${this.formatPrice(zip.avg_price)})
                        </div>`
                    ).join('')}
                </div>
            `;
            container.appendChild(zipBreakdown);
        }
    }
    
    async showPropertyModal(propertyId) {
        try {
            const response = await fetch(`/api/property/${propertyId}`);
            const data = await response.json();
            
            const property = data.property;
            const priceHistory = data.price_history;
            
            const modalBody = document.getElementById('modal-body');
            modalBody.innerHTML = `
                <div class="property-details-modal">
                    <h2>${property.address}</h2>
                    <div class="property-price-large">${this.formatPrice(property.price)}</div>
                    
                    <div class="property-specs">
                        <div class="spec-item">
                            <i class="fas fa-bed"></i>
                            <span>${property.bedrooms} Bedrooms</span>
                        </div>
                        <div class="spec-item">
                            <i class="fas fa-bath"></i>
                            <span>${property.bathrooms} Bathrooms</span>
                        </div>
                        <div class="spec-item">
                            <i class="fas fa-ruler-combined"></i>
                            <span>${this.formatNumber(property.square_feet)} sqft</span>
                        </div>
                        <div class="spec-item">
                            <i class="fas fa-home"></i>
                            <span>${property.property_type}</span>
                        </div>
                    </div>
                    
                    <div class="property-meta-modal">
                        <div><strong>Source:</strong> ${property.source}</div>
                        <div><strong>ZIP Code:</strong> ${property.zip_code}</div>
                        <div><strong>First Seen:</strong> ${this.formatDate(property.first_seen)}</div>
                        <div><strong>Last Updated:</strong> ${this.formatDate(property.last_updated)}</div>
                        ${property.mls_id ? `<div><strong>MLS ID:</strong> ${property.mls_id}</div>` : ''}
                    </div>
                    
                    ${priceHistory.length > 0 ? `
                        <div class="price-history">
                            <h3>Price History</h3>
                            <div class="price-history-list">
                                ${priceHistory.map(entry => `
                                    <div class="price-history-item">
                                        <span class="price-change">
                                            ${this.formatPrice(entry.old_price)} → ${this.formatPrice(entry.new_price)}
                                        </span>
                                        <span class="price-date">${this.formatDate(entry.change_date)}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}
                    
                    <div class="property-actions">
                        <button class="btn btn-primary" onclick="window.open('${property.listing_url}', '_blank')">
                            <i class="fas fa-external-link-alt"></i> View Listing
                        </button>
                        <button class="btn ${this.favorites.has(property.id) ? 'btn-danger' : 'btn-success'}" 
                                onclick="dashboard.toggleFavorite(${property.id})">
                            <i class="fas fa-heart"></i> 
                            ${this.favorites.has(property.id) ? 'Remove from Favorites' : 'Add to Favorites'}
                        </button>
                    </div>
                </div>
            `;
            
            // Add modal styles
            const modalStyles = `
                <style>
                .property-details-modal { padding: 1rem; }
                .property-price-large { font-size: 2rem; font-weight: bold; color: var(--primary-color); margin: 1rem 0; }
                .property-specs { display: flex; flex-wrap: wrap; gap: 1rem; margin: 1rem 0; }
                .spec-item { display: flex; align-items: center; gap: 0.5rem; background: #f8f9fa; padding: 0.5rem; border-radius: 4px; }
                .property-meta-modal { margin: 1rem 0; }
                .property-meta-modal div { margin: 0.25rem 0; }
                .price-history { margin: 1rem 0; }
                .price-history-item { display: flex; justify-content: space-between; margin: 0.5rem 0; padding: 0.5rem; background: #f8f9fa; border-radius: 4px; }
                .property-actions { display: flex; gap: 1rem; margin-top: 1.5rem; }
                </style>
            `;
            modalBody.insertAdjacentHTML('beforebegin', modalStyles);
            
            document.getElementById('property-modal').classList.add('active');
            
        } catch (error) {
            console.error('Error loading property details:', error);
        }
    }
    
    closeModal() {
        document.getElementById('property-modal').classList.remove('active');
    }
    
    async toggleFavorite(propertyId, buttonElement = null) {
        try {
            const isFavorited = this.favorites.has(propertyId);
            const method = isFavorited ? 'DELETE' : 'POST';
            
            const response = await fetch(`/api/favorites/${propertyId}`, {
                method: method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: method === 'POST' ? JSON.stringify({ notes: '' }) : undefined
            });
            
            if (response.ok) {
                if (isFavorited) {
                    this.favorites.delete(propertyId);
                } else {
                    this.favorites.add(propertyId);
                }
                
                // Update button if provided
                if (buttonElement) {
                    const heartIcon = buttonElement.querySelector('i');
                    if (this.favorites.has(propertyId)) {
                        buttonElement.classList.add('favorited');
                        heartIcon.className = 'fas fa-heart';
                    } else {
                        buttonElement.classList.remove('favorited');
                        heartIcon.className = 'far fa-heart';
                    }
                }
                
                // Update all favorite buttons
                this.updateFavoriteButtons();
                
                // Refresh favorites tab if currently viewing it
                if (this.currentTab === 'favorites') {
                    this.loadFavorites();
                }
            }
        } catch (error) {
            console.error('Error toggling favorite:', error);
        }
    }
    
    updateFavoriteButtons() {
        document.querySelectorAll('.property-favorite').forEach(btn => {
            const card = btn.closest('.property-card');
            const propertyId = parseInt(card.dataset.propertyId);
            const heartIcon = btn.querySelector('i');
            
            if (this.favorites.has(propertyId)) {
                btn.classList.add('favorited');
                heartIcon.className = 'fas fa-heart';
            } else {
                btn.classList.remove('favorited');
                heartIcon.className = 'far fa-heart';
            }
        });
    }
    
    applyFilters() {
        const zipFilter = document.getElementById('zip-filter');
        const priceFilter = document.getElementById('price-filter');
        const sourceFilter = document.getElementById('source-filter');
        const sortFilter = document.getElementById('sort-filter');
        
        // Get selected ZIP codes
        this.filters.zip_codes = Array.from(zipFilter.selectedOptions).map(option => option.value).filter(v => v);
        
        // Parse price filter
        const priceValue = priceFilter.value;
        if (priceValue) {
            const [min, max] = priceValue.split('-');
            this.filters.price_min = parseInt(min) || null;
            this.filters.price_max = parseInt(max) || null;
        } else {
            this.filters.price_min = null;
            this.filters.price_max = null;
        }
        
        this.filters.source = sourceFilter.value || null;
        this.filters.sort = sortFilter.value;
        
        this.loadProperties();
    }
    
    updateHeaderStats() {
        document.getElementById('property-count').textContent = this.properties.length;
        
        // Count new listings (last 24 hours)
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        
        const newCount = this.properties.filter(p => 
            new Date(p.first_seen) > yesterday
        ).length;
        
        document.getElementById('new-count').textContent = newCount;
    }
    
    showLoading() {
        document.getElementById('loading').style.display = 'block';
    }
    
    hideLoading() {
        document.getElementById('loading').style.display = 'none';
    }
    
    showError(message) {
        // Simple error display - could be enhanced
        console.error(message);
    }
    
    // Utility functions
    formatPrice(price) {
        if (!price) return 'Price not available';
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            maximumFractionDigits: 0
        }).format(price);
    }
    
    formatNumber(number) {
        if (!number) return null;
        return new Intl.NumberFormat('en-US').format(number);
    }
    
    formatDate(dateString) {
        if (!dateString) return 'Unknown';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    }
    
    formatRelativeTime(dateString) {
        if (!dateString) return 'Unknown';
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffMinutes = Math.floor(diffMs / (1000 * 60));
        
        if (diffDays > 0) {
            return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`;
        } else if (diffHours > 0) {
            return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
        } else if (diffMinutes > 0) {
            return `${diffMinutes} minute${diffMinutes === 1 ? '' : 's'} ago`;
        } else {
            return 'Just now';
        }
    }
    
    isNewListing(dateString) {
        if (!dateString) return false;
        const date = new Date(dateString);
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        return date > yesterday;
    }
}

// Initialize dashboard when page loads
let dashboard;

document.addEventListener('DOMContentLoaded', () => {
    dashboard = new RealEstateDashboard();
});

// Make dashboard globally accessible for modal buttons
window.dashboard = dashboard;