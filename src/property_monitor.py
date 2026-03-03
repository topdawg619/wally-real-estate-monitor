"""
Property monitoring system that coordinates all scrapers and manages the monitoring process.
"""

import json
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Import scrapers
from scrapers.redfin_scraper import RedfinScraper
# from scrapers.zillow_scraper import ZillowScraper  # Will be created
# from scrapers.realtor_scraper import RealtorScraper  # Will be created

# Import database manager
from database_manager import DatabaseManager

class PropertyMonitor:
    """Coordinates property monitoring across multiple sites."""
    
    def __init__(self, config_path: str = "config/config.json"):
        self.config_path = Path(config_path)
        self.load_config()
        
        # Setup logging
        self.setup_logging()
        
        # Initialize database
        self.db = DatabaseManager()
        
        # Initialize scrapers
        self.scrapers = {
            'redfin': RedfinScraper()
            # 'zillow': ZillowScraper(),    # Will be added
            # 'realtor': RealtorScraper()   # Will be added
        }
        
        self.logger.info("Property monitor initialized")
    
    def load_config(self):
        """Load configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Config file not found: {self.config_path}")
            self.config = self.get_default_config()
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in config file: {self.config_path}")
            self.config = self.get_default_config()
        
        # Load ZIP codes
        zip_config_path = self.config_path.parent / "zip_codes.json"
        try:
            with open(zip_config_path, 'r') as f:
                self.zip_config = json.load(f)
        except FileNotFoundError:
            self.logger.warning("ZIP codes config not found, using defaults")
            self.zip_config = {
                "primary": ["91913"],
                "secondary": ["91910", "91911", "91915"]
            }
    
    def get_default_config(self) -> Dict:
        """Return default configuration."""
        return {
            "bedrooms_min": 5,
            "bathrooms_min": 3,
            "price_max": 1200000,
            "price_min": 500000,
            "property_types": ["Single Family", "Townhouse"],
            "monitoring": {
                "scan_frequency": "3x_daily",
                "max_pages": 10,
                "request_delay": 2
            },
            "alerts": {
                "new_listings": True,
                "price_changes": True,
                "price_drop_threshold": 0.05
            }
        }
    
    def setup_logging(self):
        """Setup logging configuration."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "monitor.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def get_target_zip_codes(self) -> List[str]:
        """Get list of ZIP codes to monitor."""
        zip_codes = []
        zip_codes.extend(self.zip_config.get("primary", []))
        zip_codes.extend(self.zip_config.get("secondary", []))
        return list(set(zip_codes))  # Remove duplicates
    
    def run_monitoring_cycle(self, sites: List[str] = None, zip_codes: List[str] = None):
        """Run a complete monitoring cycle."""
        start_time = datetime.now()
        self.logger.info("=" * 50)
        self.logger.info(f"Starting monitoring cycle at {start_time}")
        
        # Use provided sites or all available
        if sites is None:
            sites = list(self.scrapers.keys())
        
        # Use provided ZIP codes or configured ones
        if zip_codes is None:
            zip_codes = self.get_target_zip_codes()
        
        self.logger.info(f"Monitoring sites: {sites}")
        self.logger.info(f"Target ZIP codes: {zip_codes}")
        
        total_new_properties = 0
        total_updated_properties = 0
        total_properties_found = 0
        
        # Monitor each site
        for site_name in sites:
            if site_name not in self.scrapers:
                self.logger.warning(f"Scraper not available for site: {site_name}")
                continue
            
            self.logger.info(f"Monitoring {site_name}...")
            
            try:
                # Get scraper
                scraper = self.scrapers[site_name]
                
                # Search for properties
                properties = scraper.search_properties(
                    zip_codes=zip_codes,
                    **self.config
                )
                
                self.logger.info(f"Found {len(properties)} properties on {site_name}")
                total_properties_found += len(properties)
                
                # Process each property
                for property_data in properties:
                    try:
                        # Validate property meets criteria
                        if not scraper.validate_property(property_data, self.config):
                            continue
                        
                        # Add or update in database
                        property_id, is_new = self.db.add_or_update_property(property_data)
                        
                        if is_new:
                            total_new_properties += 1
                            self.logger.info(f"New property: {property_data.get('address', 'Unknown')}")
                        else:
                            total_updated_properties += 1
                        
                    except Exception as e:
                        self.logger.error(f"Error processing property: {str(e)}")
                        continue
                
            except Exception as e:
                self.logger.error(f"Error monitoring {site_name}: {str(e)}")
                continue
        
        # Generate summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        self.logger.info(f"Monitoring cycle completed in {duration}")
        self.logger.info(f"Summary:")
        self.logger.info(f"  - Total properties found: {total_properties_found}")
        self.logger.info(f"  - New properties added: {total_new_properties}")
        self.logger.info(f"  - Properties updated: {total_updated_properties}")
        
        # Log monitoring run
        self.db.log_activity(
            property_id=None,
            activity_type="monitoring_cycle",
            description=f"Cycle complete: {total_properties_found} found, {total_new_properties} new, {total_updated_properties} updated"
        )
        
        return {
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration,
            'properties_found': total_properties_found,
            'new_properties': total_new_properties,
            'updated_properties': total_updated_properties
        }
    
    def generate_daily_report(self) -> Dict:
        """Generate daily monitoring report."""
        self.logger.info("Generating daily report...")
        
        # Get market stats
        zip_codes = self.get_target_zip_codes()
        market_stats = self.db.get_market_stats(zip_codes)
        
        # Get recent activity
        recent_activity = self.db.get_recent_activity(days=1, limit=20)
        
        # Get new listings from last 24 hours
        new_listings = self.db.get_properties({
            'zip_codes': zip_codes,
            'status': 'active'
        }, limit=50)
        
        # Filter for truly new (first seen in last 24 hours)
        from datetime import datetime, timedelta
        yesterday = datetime.now() - timedelta(days=1)
        
        truly_new = [
            prop for prop in new_listings 
            if datetime.fromisoformat(prop['first_seen'].replace('Z', '+00:00')) > yesterday
        ]
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'market_stats': market_stats,
            'recent_activity': recent_activity,
            'new_listings_24h': truly_new,
            'total_active_properties': market_stats.get('total_properties', 0)
        }
        
        self.logger.info(f"Daily report: {len(truly_new)} new listings, {len(recent_activity)} activities")
        
        return report
    
    def check_alerts(self) -> List[Dict]:
        """Check for properties that meet alert criteria."""
        alerts = []
        
        if not self.config.get('alerts', {}).get('new_listings', True):
            return alerts
        
        # Get recent new listings
        zip_codes = self.get_target_zip_codes()
        recent_properties = self.db.get_recent_activity(days=1, limit=20)
        
        new_listing_activities = [
            activity for activity in recent_properties 
            if activity['activity_type'] == 'new_listing'
        ]
        
        for activity in new_listing_activities:
            # Check if it's a good deal (below market average)
            property_data = self.db.get_property_by_id(activity['property_id'])
            if not property_data:
                continue
            
            alert_reasons = []
            
            # Price-based alerts
            price = property_data.get('price', 0)
            if price < 900000:  # Good deal threshold
                alert_reasons.append(f"Below market price: ${price:,}")
            
            # Days on market (if we had that data)
            # if property_data.get('days_on_market', 0) > 30:
            #     alert_reasons.append("Long time on market")
            
            if alert_reasons:
                alerts.append({
                    'property_id': property_data['id'],
                    'address': property_data['address'],
                    'price': property_data['price'],
                    'reasons': alert_reasons,
                    'listing_url': property_data.get('listing_url', ''),
                    'timestamp': activity['timestamp']
                })
        
        return alerts
    
    def cleanup_database(self):
        """Clean up old database entries."""
        self.logger.info("Running database cleanup...")
        self.db.cleanup_old_data(days_old=90)
        self.logger.info("Database cleanup completed")

def main():
    """Main entry point for command line usage."""
    parser = argparse.ArgumentParser(description='Real Estate Property Monitor')
    parser.add_argument('--sites', type=str, help='Comma-separated list of sites to monitor (redfin,zillow,realtor)')
    parser.add_argument('--zips', type=str, help='Comma-separated list of ZIP codes to monitor')
    parser.add_argument('--config', type=str, default='config/config.json', help='Path to config file')
    parser.add_argument('--report', action='store_true', help='Generate daily report only')
    parser.add_argument('--cleanup', action='store_true', help='Run database cleanup only')
    parser.add_argument('--alerts', action='store_true', help='Check alerts only')
    
    args = parser.parse_args()
    
    # Initialize monitor
    monitor = PropertyMonitor(config_path=args.config)
    
    try:
        if args.cleanup:
            monitor.cleanup_database()
        elif args.report:
            report = monitor.generate_daily_report()
            print(json.dumps(report, indent=2, default=str))
        elif args.alerts:
            alerts = monitor.check_alerts()
            print(json.dumps(alerts, indent=2, default=str))
        else:
            # Parse sites and ZIP codes if provided
            sites = None
            if args.sites:
                sites = [s.strip() for s in args.sites.split(',')]
            
            zip_codes = None
            if args.zips:
                zip_codes = [z.strip() for z in args.zips.split(',')]
            
            # Run monitoring cycle
            result = monitor.run_monitoring_cycle(sites=sites, zip_codes=zip_codes)
            print(f"Monitoring completed: {result['new_properties']} new properties found")
            
    except KeyboardInterrupt:
        print("\\nMonitoring interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()