#!/usr/bin/env python3
"""
Wally Real Estate Monitor - Setup and Management Script
Easy setup, testing, and management for the real estate monitoring system.
"""

import os
import sys
import subprocess
import sqlite3
import json
import webbrowser
import time
from pathlib import Path

def install_dependencies():
    """Install required Python packages"""
    requirements = [
        'requests>=2.28.0',
        'beautifulsoup4>=4.11.0',
        'lxml>=4.9.0',
        'sqlite3',  # Built-in to Python
        'flask>=2.2.0',
        'schedule>=1.2.0',
        'python-dateutil>=2.8.0'
    ]
    
    print("🔧 Installing dependencies...")
    for package in requirements:
        if package == 'sqlite3':
            continue  # Built-in
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install {package}")
            return False
    
    print("✅ Dependencies installed successfully!")
    return True

def create_directory_structure():
    """Create necessary directories"""
    directories = [
        'src/scrapers',
        'dashboard/css',
        'dashboard/js',
        'config',
        'scripts',
        'data',
        'logs',
        'tests'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Directory structure created!")

def create_database():
    """Initialize SQLite database with tables"""
    print("🗄️ Creating database...")
    
    db_path = Path('data/properties.db')
    
    with sqlite3.connect(db_path) as conn:
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
        
        conn.commit()
    
    print("✅ Database created successfully!")

def create_config_files():
    """Create configuration files"""
    print("⚙️ Creating configuration files...")
    
    # Main config
    config = {
        "bedrooms_min": 5,
        "bathrooms_min": 3,
        "price_max": 1200000,
        "price_min": 500000,
        "property_types": ["Single Family", "Townhouse", "Condo"],
        "monitoring": {
            "scan_frequency": "3x_daily",
            "scan_times": ["07:00", "13:00", "19:00"],
            "max_pages": 10,
            "request_delay": 2
        },
        "dashboard": {
            "port": 8080,
            "auto_open": True
        },
        "alerts": {
            "new_listings": True,
            "price_changes": True,
            "price_drop_threshold": 0.05
        }
    }
    
    with open('config/config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    # ZIP codes config
    zip_codes = {
        "primary": ["91913"],
        "secondary": ["91910", "91911", "91915", "91917", "92154"],
        "names": {
            "91913": "Chula Vista East",
            "91910": "Chula Vista Central", 
            "91911": "Chula Vista West",
            "91915": "Bonita",
            "91917": "National City",
            "92154": "San Ysidro"
        }
    }
    
    with open('config/zip_codes.json', 'w') as f:
        json.dump(zip_codes, f, indent=2)
    
    print("✅ Configuration files created!")

def create_demo_data():
    """Create demo data for testing"""
    print("🏠 Creating demo data...")
    
    demo_properties = [
        {
            'address': '1234 Demo Street, Chula Vista, CA 91913',
            'zip_code': '91913',
            'price': 950000,
            'bedrooms': 5,
            'bathrooms': 3.5,
            'square_feet': 2800,
            'property_type': 'Single Family',
            'listing_url': 'https://example.com/property1',
            'source': 'redfin',
            'status': 'active'
        },
        {
            'address': '5678 Sample Ave, Chula Vista, CA 91910',
            'zip_code': '91910',
            'price': 875000,
            'bedrooms': 5,
            'bathrooms': 3.0,
            'square_feet': 2600,
            'property_type': 'Single Family',
            'listing_url': 'https://example.com/property2',
            'source': 'zillow',
            'status': 'active'
        },
        {
            'address': '9101 Test Lane, Bonita, CA 91915',
            'zip_code': '91915',
            'price': 1100000,
            'bedrooms': 6,
            'bathrooms': 4.0,
            'square_feet': 3200,
            'property_type': 'Single Family',
            'listing_url': 'https://example.com/property3',
            'source': 'realtor',
            'status': 'active'
        }
    ]
    
    db_path = Path('data/properties.db')
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        for prop in demo_properties:
            cursor.execute('''
                INSERT OR REPLACE INTO properties 
                (address, zip_code, price, bedrooms, bathrooms, square_feet, 
                 property_type, listing_url, source, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                prop['address'], prop['zip_code'], prop['price'],
                prop['bedrooms'], prop['bathrooms'], prop['square_feet'],
                prop['property_type'], prop['listing_url'], prop['source'], prop['status']
            ))
        
        conn.commit()
    
    print("✅ Demo data created!")

def test_system():
    """Test the monitoring system"""
    print("🧪 Testing system components...")
    
    # Test database connection
    try:
        db_path = Path('data/properties.db')
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM properties')
            count = cursor.fetchone()[0]
            print(f"✅ Database: {count} properties found")
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    
    # Test configuration
    try:
        with open('config/config.json', 'r') as f:
            config = json.load(f)
        print("✅ Configuration: Loaded successfully")
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False
    
    # Test web dashboard files
    dashboard_files = ['dashboard/index.html', 'dashboard/css/styles.css', 'dashboard/js/dashboard.js']
    for file_path in dashboard_files:
        if Path(file_path).exists():
            print(f"✅ Dashboard: {file_path} found")
        else:
            print(f"⚠️  Dashboard: {file_path} missing (will be created)")
    
    print("✅ System test completed!")
    return True

def start_dashboard():
    """Start the web dashboard"""
    print("🖥️ Starting web dashboard...")
    
    try:
        # Import and start the dashboard
        sys.path.append('src')
        from web_dashboard import start_dashboard
        
        # Load configuration
        with open('config/config.json', 'r') as f:
            config = json.load(f)
        
        port = config.get('dashboard', {}).get('port', 8080)
        auto_open = config.get('dashboard', {}).get('auto_open', True)
        
        if auto_open:
            # Open browser after a short delay
            def open_browser():
                time.sleep(2)
                webbrowser.open(f'http://localhost:{port}')
            
            import threading
            browser_thread = threading.Thread(target=open_browser)
            browser_thread.daemon = True
            browser_thread.start()
        
        print(f"📱 Dashboard starting at http://localhost:{port}")
        start_dashboard(port=port)
        
    except ImportError:
        print("❌ Dashboard module not found. Run 'python setup.py setup' first.")
    except Exception as e:
        print(f"❌ Dashboard failed to start: {e}")

def install_monitoring():
    """Install automated monitoring via cron"""
    print("⏰ Setting up automated monitoring...")
    
    try:
        # Get current directory
        current_dir = os.getcwd()
        
        # Create monitoring script
        monitor_script = f"""#!/bin/bash
cd {current_dir}
python src/property_monitor.py >> logs/monitor.log 2>&1
"""
        
        script_path = Path('scripts/run_monitor.sh')
        with open(script_path, 'w') as f:
            f.write(monitor_script)
        
        # Make script executable
        os.chmod(script_path, 0o755)
        
        # Generate cron entries
        cron_entries = f"""# Wally Real Estate Monitor
0 7 * * * {current_dir}/scripts/run_monitor.sh
0 13 * * * {current_dir}/scripts/run_monitor.sh  
0 19 * * * {current_dir}/scripts/run_monitor.sh
"""
        
        print("⏰ Monitoring schedule:")
        print("  - 7:00 AM: Morning scan")
        print("  - 1:00 PM: Afternoon scan") 
        print("  - 7:00 PM: Evening scan")
        print()
        print("To install cron jobs, run:")
        print(f"echo '{cron_entries.strip()}' | crontab -")
        print()
        print("To view current cron jobs: crontab -l")
        print("To remove cron jobs: crontab -r")
        
    except Exception as e:
        print(f"❌ Monitoring setup failed: {e}")

def setup():
    """Complete setup process"""
    print("🚀 Setting up Wally Real Estate Monitor...")
    print()
    
    # Create directories
    create_directory_structure()
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Create database
    create_database()
    
    # Create config files
    create_config_files()
    
    # Create demo data
    create_demo_data()
    
    print()
    print("✅ Setup completed successfully!")
    print()
    print("🎯 Next steps:")
    print("  1. Test the system: python setup.py test")
    print("  2. Start dashboard: python setup.py dashboard")
    print("  3. Set up monitoring: python setup.py monitor")
    print()
    
    return True

def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print("Usage: python setup.py [setup|test|dashboard|monitor]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'setup':
        setup()
    elif command == 'test':
        test_system()
    elif command == 'dashboard':
        start_dashboard()
    elif command == 'monitor':
        install_monitoring()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: setup, test, dashboard, monitor")
        sys.exit(1)

if __name__ == '__main__':
    main()