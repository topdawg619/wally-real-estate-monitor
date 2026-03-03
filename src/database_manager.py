"""
Database manager for storing and managing property listings.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

class DatabaseManager:
    """Manages SQLite database operations for property listings."""
    
    def __init__(self, db_path: str = "data/properties.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Properties table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS properties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    address TEXT NOT NULL,
                    zip_code TEXT NOT NULL,
                    price INTEGER NOT NULL,
                    bedrooms INTEGER NOT NULL,
                    bathrooms REAL NOT NULL,
                    square_feet INTEGER,
                    property_type TEXT,
                    listing_url TEXT,
                    source TEXT NOT NULL,
                    mls_id TEXT,
                    listing_date DATE,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    raw_data TEXT,
                    UNIQUE(address, source)
                )
            ''')
            
            # Price history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    property_id INTEGER,
                    old_price INTEGER,
                    new_price INTEGER,
                    change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (property_id) REFERENCES properties (id)
                )
            ''')
            
            # Favorites table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS favorites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    property_id INTEGER,
                    notes TEXT,
                    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (property_id) REFERENCES properties (id)
                )
            ''')
            
            # Activity log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    activity_type TEXT NOT NULL,
                    property_id INTEGER,
                    description TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (property_id) REFERENCES properties (id)
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_zip_code ON properties(zip_code)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_price ON properties(price)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON properties(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_last_updated ON properties(last_updated)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_source ON properties(source)')
            
            conn.commit()
    
    def add_or_update_property(self, property_data: Dict) -> Tuple[int, bool]:
        """
        Add a new property or update existing one.
        Returns: (property_id, is_new)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if property already exists
            cursor.execute('''
                SELECT id, price FROM properties 
                WHERE address = ? AND source = ?
            ''', (property_data['address'], property_data['source']))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing property
                property_id, old_price = existing
                new_price = property_data.get('price')
                
                # Update the property
                cursor.execute('''
                    UPDATE properties SET
                        price = ?, bedrooms = ?, bathrooms = ?, square_feet = ?,
                        property_type = ?, listing_url = ?, mls_id = ?, 
                        listing_date = ?, last_updated = CURRENT_TIMESTAMP,
                        status = ?, raw_data = ?
                    WHERE id = ?
                ''', (
                    new_price, property_data.get('bedrooms'), property_data.get('bathrooms'),
                    property_data.get('square_feet'), property_data.get('property_type'),
                    property_data.get('listing_url'), property_data.get('mls_id'),
                    property_data.get('listing_date'), property_data.get('status', 'active'),
                    json.dumps(property_data.get('raw_data', {})), property_id
                ))
                
                # Log price change if significant
                if old_price and new_price and abs(new_price - old_price) > 1000:
                    cursor.execute('''
                        INSERT INTO price_history (property_id, old_price, new_price)
                        VALUES (?, ?, ?)
                    ''', (property_id, old_price, new_price))
                    
                    # Log activity
                    change_type = "price_increase" if new_price > old_price else "price_decrease"
                    self.log_activity(property_id, change_type, 
                                    f"Price changed from ${old_price:,} to ${new_price:,}")
                
                return property_id, False
            else:
                # Insert new property
                cursor.execute('''
                    INSERT INTO properties (
                        address, zip_code, price, bedrooms, bathrooms, square_feet,
                        property_type, listing_url, source, mls_id, listing_date,
                        status, raw_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    property_data['address'], property_data.get('zip_code'),
                    property_data.get('price'), property_data.get('bedrooms'),
                    property_data.get('bathrooms'), property_data.get('square_feet'),
                    property_data.get('property_type'), property_data.get('listing_url'),
                    property_data['source'], property_data.get('mls_id'),
                    property_data.get('listing_date'), property_data.get('status', 'active'),
                    json.dumps(property_data.get('raw_data', {}))
                ))
                
                property_id = cursor.lastrowid
                
                # Log new listing activity
                self.log_activity(property_id, "new_listing", 
                                f"New listing added: {property_data['address']}")
                
                return property_id, True
    
    def get_properties(self, filters: Dict = None, limit: int = None) -> List[Dict]:
        """Get properties with optional filters."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()
            
            query = "SELECT * FROM properties"
            conditions = []
            params = []
            
            if filters:
                if 'zip_codes' in filters and filters['zip_codes']:
                    placeholders = ','.join('?' * len(filters['zip_codes']))
                    conditions.append(f"zip_code IN ({placeholders})")
                    params.extend(filters['zip_codes'])
                
                if 'price_min' in filters:
                    conditions.append("price >= ?")
                    params.append(filters['price_min'])
                
                if 'price_max' in filters:
                    conditions.append("price <= ?")
                    params.append(filters['price_max'])
                
                if 'bedrooms_min' in filters:
                    conditions.append("bedrooms >= ?")
                    params.append(filters['bedrooms_min'])
                
                if 'bathrooms_min' in filters:
                    conditions.append("bathrooms >= ?")
                    params.append(filters['bathrooms_min'])
                
                if 'status' in filters:
                    conditions.append("status = ?")
                    params.append(filters['status'])
                
                if 'source' in filters:
                    conditions.append("source = ?")
                    params.append(filters['source'])
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY last_updated DESC"
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Convert to dictionaries
            properties = []
            for row in rows:
                prop = dict(row)
                # Parse raw_data if it exists
                if prop['raw_data']:
                    try:
                        prop['raw_data'] = json.loads(prop['raw_data'])
                    except json.JSONDecodeError:
                        prop['raw_data'] = {}
                properties.append(prop)
            
            return properties
    
    def get_property_by_id(self, property_id: int) -> Optional[Dict]:
        """Get a single property by ID."""
        properties = self.get_properties({'id': property_id})
        return properties[0] if properties else None
    
    def get_recent_activity(self, days: int = 7, limit: int = 50) -> List[Dict]:
        """Get recent activity (new listings, price changes, etc.)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    al.*,
                    p.address,
                    p.price,
                    p.zip_code,
                    p.source,
                    p.listing_url
                FROM activity_log al
                JOIN properties p ON al.property_id = p.id
                WHERE al.timestamp >= datetime('now', '-{} days')
                ORDER BY al.timestamp DESC
                LIMIT ?
            '''.format(days), (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_price_history(self, property_id: int) -> List[Dict]:
        """Get price history for a property."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM price_history 
                WHERE property_id = ? 
                ORDER BY change_date ASC
            ''', (property_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def add_to_favorites(self, property_id: int, notes: str = "") -> bool:
        """Add property to favorites."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO favorites (property_id, notes)
                    VALUES (?, ?)
                ''', (property_id, notes))
                conn.commit()
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Error adding to favorites: {str(e)}")
            return False
    
    def remove_from_favorites(self, property_id: int) -> bool:
        """Remove property from favorites."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM favorites WHERE property_id = ?', (property_id,))
                conn.commit()
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Error removing from favorites: {str(e)}")
            return False
    
    def get_favorites(self) -> List[Dict]:
        """Get all favorited properties."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    p.*,
                    f.notes,
                    f.added_date as favorited_date
                FROM properties p
                JOIN favorites f ON p.id = f.property_id
                ORDER BY f.added_date DESC
            ''')
            
            return [dict(row) for row in cursor.fetchall()]
    
    def log_activity(self, property_id: int, activity_type: str, description: str):
        """Log an activity for a property."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO activity_log (property_id, activity_type, description)
                    VALUES (?, ?, ?)
                ''', (property_id, activity_type, description))
                conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Error logging activity: {str(e)}")
    
    def get_market_stats(self, zip_codes: List[str] = None) -> Dict:
        """Get market statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            filters = []
            params = []
            
            if zip_codes:
                placeholders = ','.join('?' * len(zip_codes))
                filters.append(f"zip_code IN ({placeholders})")
                params.extend(zip_codes)
            
            where_clause = " WHERE " + " AND ".join(filters) if filters else ""
            
            # Get basic stats
            cursor.execute(f'''
                SELECT 
                    COUNT(*) as total_properties,
                    AVG(price) as avg_price,
                    MIN(price) as min_price,
                    MAX(price) as max_price,
                    AVG(bedrooms) as avg_bedrooms,
                    AVG(bathrooms) as avg_bathrooms,
                    AVG(square_feet) as avg_sqft
                FROM properties 
                WHERE status = 'active' {where_clause}
            ''', params)
            
            stats = dict(cursor.fetchone()) if cursor.fetchone() else {}
            
            # Get listings by ZIP code
            cursor.execute(f'''
                SELECT zip_code, COUNT(*) as count, AVG(price) as avg_price
                FROM properties 
                WHERE status = 'active' {where_clause}
                GROUP BY zip_code
                ORDER BY count DESC
            ''', params)
            
            stats['by_zip_code'] = [
                {'zip_code': row[0], 'count': row[1], 'avg_price': row[2]}
                for row in cursor.fetchall()
            ]
            
            # Get recent activity count
            cursor.execute(f'''
                SELECT COUNT(*) FROM activity_log al
                JOIN properties p ON al.property_id = p.id
                WHERE al.timestamp >= datetime('now', '-7 days') {where_clause}
            ''', params)
            
            stats['recent_activity'] = cursor.fetchone()[0]
            
            return stats
    
    def cleanup_old_data(self, days_old: int = 90):
        """Clean up old inactive properties and logs."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Remove old sold/inactive properties
                cursor.execute('''
                    DELETE FROM properties 
                    WHERE status IN ('sold', 'off_market', 'expired') 
                    AND last_updated < datetime('now', '-{} days')
                '''.format(days_old))
                
                removed_properties = cursor.rowcount
                
                # Clean up orphaned activity logs
                cursor.execute('''
                    DELETE FROM activity_log 
                    WHERE timestamp < datetime('now', '-{} days')
                '''.format(days_old * 2))
                
                removed_logs = cursor.rowcount
                
                conn.commit()
                
                self.logger.info(f"Cleanup: Removed {removed_properties} old properties and {removed_logs} old logs")
                
        except sqlite3.Error as e:
            self.logger.error(f"Error during cleanup: {str(e)}")

if __name__ == "__main__":
    # Test the database manager
    db = DatabaseManager()
    
    # Test adding a property
    test_property = {
        'address': '123 Test Street, Chula Vista, CA 91913',
        'zip_code': '91913',
        'price': 950000,
        'bedrooms': 5,
        'bathrooms': 3.5,
        'square_feet': 2800,
        'property_type': 'Single Family',
        'listing_url': 'https://example.com/test',
        'source': 'test',
        'status': 'active'
    }
    
    property_id, is_new = db.add_or_update_property(test_property)
    print(f"Added property {property_id}, new: {is_new}")
    
    # Get properties
    properties = db.get_properties(limit=5)
    print(f"Found {len(properties)} properties")
    
    # Get market stats
    stats = db.get_market_stats()
    print(f"Market stats: {stats}")