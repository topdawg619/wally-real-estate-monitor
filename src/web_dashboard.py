"""
Web dashboard for viewing and managing real estate properties.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

try:
    from flask import Flask, render_template, jsonify, request, send_from_directory
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("Flask not available. Install with: pip install flask")

from database_manager import DatabaseManager

class WebDashboard:
    """Web dashboard for property monitoring."""
    
    def __init__(self, db_path: str = "data/properties.db"):
        if not FLASK_AVAILABLE:
            raise ImportError("Flask is required for web dashboard")
        
        self.app = Flask(__name__, 
                        template_folder='../dashboard',
                        static_folder='../dashboard')
        self.db = DatabaseManager(db_path)
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route('/')
        def index():
            """Main dashboard page."""
            return send_from_directory('../dashboard', 'index.html')
        
        @self.app.route('/api/properties')
        def get_properties():
            """API endpoint to get properties with filters."""
            # Get query parameters
            zip_codes = request.args.get('zip_codes', '').split(',') if request.args.get('zip_codes') else None
            source = request.args.get('source')
            price_min = request.args.get('price_min', type=int)
            price_max = request.args.get('price_max', type=int)
            bedrooms_min = request.args.get('bedrooms_min', type=int)
            bathrooms_min = request.args.get('bathrooms_min', type=float)
            sort_by = request.args.get('sort', 'last_updated')
            limit = request.args.get('limit', 100, type=int)
            
            # Build filters
            filters = {}
            if zip_codes and zip_codes[0]:
                filters['zip_codes'] = [z.strip() for z in zip_codes if z.strip()]
            if source:
                filters['source'] = source
            if price_min:
                filters['price_min'] = price_min
            if price_max:
                filters['price_max'] = price_max
            if bedrooms_min:
                filters['bedrooms_min'] = bedrooms_min
            if bathrooms_min:
                filters['bathrooms_min'] = bathrooms_min
            
            # Get properties
            properties = self.db.get_properties(filters=filters, limit=limit)
            
            # Sort properties
            if sort_by == 'price_asc':
                properties.sort(key=lambda x: x.get('price', 0))
            elif sort_by == 'price_desc':
                properties.sort(key=lambda x: x.get('price', 0), reverse=True)
            elif sort_by == 'newest':
                properties.sort(key=lambda x: x.get('first_seen', ''), reverse=True)
            elif sort_by == 'updated':
                properties.sort(key=lambda x: x.get('last_updated', ''), reverse=True)
            
            return jsonify({
                'properties': properties,
                'count': len(properties),
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/api/property/<int:property_id>')
        def get_property(property_id):
            """Get single property details."""
            property_data = self.db.get_property_by_id(property_id)
            if not property_data:
                return jsonify({'error': 'Property not found'}), 404
            
            # Get price history
            price_history = self.db.get_price_history(property_id)
            
            return jsonify({
                'property': property_data,
                'price_history': price_history
            })
        
        @self.app.route('/api/activity')
        def get_recent_activity():
            """Get recent activity feed."""
            days = request.args.get('days', 7, type=int)
            limit = request.args.get('limit', 50, type=int)
            
            activity = self.db.get_recent_activity(days=days, limit=limit)
            
            return jsonify({
                'activity': activity,
                'count': len(activity)
            })
        
        @self.app.route('/api/favorites', methods=['GET'])
        def get_favorites():
            """Get favorite properties."""
            favorites = self.db.get_favorites()
            return jsonify({
                'favorites': favorites,
                'count': len(favorites)
            })
        
        @self.app.route('/api/favorites/<int:property_id>', methods=['POST'])
        def add_favorite(property_id):
            """Add property to favorites."""
            data = request.get_json() or {}
            notes = data.get('notes', '')
            
            success = self.db.add_to_favorites(property_id, notes)
            
            return jsonify({
                'success': success,
                'property_id': property_id
            })
        
        @self.app.route('/api/favorites/<int:property_id>', methods=['DELETE'])
        def remove_favorite(property_id):
            """Remove property from favorites."""
            success = self.db.remove_from_favorites(property_id)
            
            return jsonify({
                'success': success,
                'property_id': property_id
            })
        
        @self.app.route('/api/stats')
        def get_market_stats():
            """Get market statistics."""
            zip_codes = request.args.get('zip_codes', '').split(',') if request.args.get('zip_codes') else None
            if zip_codes and zip_codes[0]:
                zip_codes = [z.strip() for z in zip_codes if z.strip()]
            
            stats = self.db.get_market_stats(zip_codes)
            
            return jsonify({
                'stats': stats,
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/api/new-listings')
        def get_new_listings():
            """Get new listings from the last 24-48 hours."""
            hours = request.args.get('hours', 48, type=int)
            limit = request.args.get('limit', 20, type=int)
            
            # Calculate cutoff time
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # Get recent properties
            all_properties = self.db.get_properties(limit=limit*2)  # Get more to filter
            
            # Filter for new listings
            new_listings = [
                prop for prop in all_properties
                if datetime.fromisoformat(prop['first_seen'].replace('Z', '+00:00')) > cutoff_time
            ][:limit]
            
            return jsonify({
                'new_listings': new_listings,
                'count': len(new_listings),
                'hours': hours
            })
        
        @self.app.route('/api/config')
        def get_config():
            """Get dashboard configuration."""
            config = {
                'zip_codes': ['91913', '91910', '91911', '91915', '91917'],
                'sources': ['redfin', 'zillow', 'realtor'],
                'price_ranges': [
                    {'label': 'Under $800K', 'min': 0, 'max': 800000},
                    {'label': '$800K - $1M', 'min': 800000, 'max': 1000000},
                    {'label': '$1M - $1.2M', 'min': 1000000, 'max': 1200000},
                    {'label': 'Over $1.2M', 'min': 1200000, 'max': 9999999}
                ]
            }
            
            return jsonify(config)
        
        # Static file serving
        @self.app.route('/css/<path:filename>')
        def serve_css(filename):
            return send_from_directory('../dashboard/css', filename)
        
        @self.app.route('/js/<path:filename>')
        def serve_js(filename):
            return send_from_directory('../dashboard/js', filename)
    
    def run(self, host='localhost', port=8080, debug=False):
        """Run the web dashboard."""
        print(f"🖥️  Starting Real Estate Dashboard at http://{host}:{port}")
        print("📱 Mobile-optimized for daily property checking")
        print("🏠 Press Ctrl+C to stop")
        
        self.app.run(host=host, port=port, debug=debug)

def start_dashboard(host='localhost', port=8080, debug=False):
    """Start the web dashboard (convenience function)."""
    dashboard = WebDashboard()
    dashboard.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Real Estate Web Dashboard')
    parser.add_argument('--host', default='localhost', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    try:
        start_dashboard(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        print("\\nDashboard stopped by user")
    except Exception as e:
        print(f"Error starting dashboard: {str(e)}")
        print("Make sure Flask is installed: pip install flask")