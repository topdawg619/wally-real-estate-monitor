"""
Base scraper framework with rate limiting, error handling, and respectful practices.
"""

import time
import requests
from datetime import datetime
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import random
from urllib.parse import urljoin, urlparse

class BaseScraper(ABC):
    """Base class for all real estate site scrapers."""
    
    def __init__(self, delay_range=(2, 4), max_retries=3, timeout=30):
        self.delay_range = delay_range
        self.max_retries = max_retries
        self.timeout = timeout
        self.session = requests.Session()
        self.last_request_time = 0
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Common headers to appear more browser-like
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def respect_rate_limit(self):
        """Ensure we don't make requests too quickly."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        min_delay = self.delay_range[0]
        if time_since_last < min_delay:
            sleep_time = min_delay - time_since_last
            time.sleep(sleep_time)
        
        # Add random jitter
        jitter = random.uniform(0, self.delay_range[1] - self.delay_range[0])
        time.sleep(jitter)
        
        self.last_request_time = time.time()
    
    def make_request(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Make a rate-limited request with retry logic."""
        self.respect_rate_limit()
        
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"Making request to: {url} (attempt {attempt + 1})")
                response = self.session.get(url, timeout=self.timeout, **kwargs)
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:  # Rate limited
                    wait_time = 2 ** attempt * 30  # Exponential backoff
                    self.logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    self.logger.warning(f"Request failed with status {response.status_code}")
                    
            except requests.RequestException as e:
                self.logger.error(f"Request error (attempt {attempt + 1}): {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        return None
    
    @abstractmethod
    def get_site_name(self) -> str:
        """Return the name of the site being scraped."""
        pass
    
    @abstractmethod
    def build_search_url(self, zip_codes: List[str], **criteria) -> str:
        """Build the search URL for the given criteria."""
        pass
    
    @abstractmethod
    def parse_listing(self, listing_element) -> Optional[Dict]:
        """Parse a single listing element into a standardized format."""
        pass
    
    @abstractmethod
    def extract_listings(self, response: requests.Response) -> List[Dict]:
        """Extract all listings from a search results page."""
        pass
    
    def search_properties(self, zip_codes: List[str], **criteria) -> List[Dict]:
        """Search for properties matching the given criteria."""
        all_properties = []
        
        try:
            search_url = self.build_search_url(zip_codes, **criteria)
            self.logger.info(f"Searching {self.get_site_name()}: {search_url}")
            
            response = self.make_request(search_url)
            if response:
                properties = self.extract_listings(response)
                self.logger.info(f"Found {len(properties)} properties on {self.get_site_name()}")
                all_properties.extend(properties)
            else:
                self.logger.error(f"Failed to get search results from {self.get_site_name()}")
                
        except Exception as e:
            self.logger.error(f"Error searching {self.get_site_name()}: {str(e)}")
        
        return all_properties
    
    def normalize_price(self, price_str: str) -> Optional[int]:
        """Convert price string to integer."""
        if not price_str:
            return None
        
        # Remove common price formatting
        price_clean = price_str.replace('$', '').replace(',', '').replace('+', '')
        
        try:
            return int(float(price_clean))
        except (ValueError, TypeError):
            self.logger.warning(f"Could not parse price: {price_str}")
            return None
    
    def normalize_bedrooms(self, beds_str: str) -> Optional[int]:
        """Convert bedrooms string to integer."""
        if not beds_str:
            return None
        
        try:
            # Handle formats like "5 bed", "5br", "5+"
            beds_clean = beds_str.lower().replace('bed', '').replace('br', '').replace('+', '').strip()
            return int(float(beds_clean))
        except (ValueError, TypeError):
            self.logger.warning(f"Could not parse bedrooms: {beds_str}")
            return None
    
    def normalize_bathrooms(self, baths_str: str) -> Optional[float]:
        """Convert bathrooms string to float."""
        if not baths_str:
            return None
        
        try:
            # Handle formats like "3.5 bath", "3ba", "3+"
            baths_clean = baths_str.lower().replace('bath', '').replace('ba', '').replace('+', '').strip()
            return float(baths_clean)
        except (ValueError, TypeError):
            self.logger.warning(f"Could not parse bathrooms: {baths_str}")
            return None
    
    def normalize_square_feet(self, sqft_str: str) -> Optional[int]:
        """Convert square feet string to integer."""
        if not sqft_str:
            return None
        
        try:
            # Handle formats like "2,800 sq ft", "2800sqft"
            sqft_clean = sqft_str.replace(',', '').replace('sq', '').replace('ft', '').strip()
            return int(float(sqft_clean))
        except (ValueError, TypeError):
            self.logger.warning(f"Could not parse square feet: {sqft_str}")
            return None
    
    def standardize_property(self, raw_property: Dict) -> Dict:
        """Standardize a property dictionary to common format."""
        return {
            'address': raw_property.get('address', '').strip(),
            'zip_code': raw_property.get('zip_code', '').strip(),
            'price': self.normalize_price(raw_property.get('price', '')),
            'bedrooms': self.normalize_bedrooms(raw_property.get('bedrooms', '')),
            'bathrooms': self.normalize_bathrooms(raw_property.get('bathrooms', '')),
            'square_feet': self.normalize_square_feet(raw_property.get('square_feet', '')),
            'property_type': raw_property.get('property_type', '').strip(),
            'listing_url': raw_property.get('listing_url', '').strip(),
            'source': self.get_site_name(),
            'mls_id': raw_property.get('mls_id', '').strip(),
            'listing_date': raw_property.get('listing_date'),
            'status': raw_property.get('status', 'active').lower().strip(),
            'raw_data': raw_property  # Keep original for debugging
        }
    
    def validate_property(self, property_data: Dict, criteria: Dict) -> bool:
        """Check if property meets the search criteria."""
        if not property_data.get('address'):
            return False
        
        if not property_data.get('price'):
            return False
        
        # Check bedrooms
        min_beds = criteria.get('bedrooms_min', 0)
        if property_data.get('bedrooms', 0) < min_beds:
            return False
        
        # Check bathrooms
        min_baths = criteria.get('bathrooms_min', 0)
        if property_data.get('bathrooms', 0) < min_baths:
            return False
        
        # Check price range
        max_price = criteria.get('price_max', float('inf'))
        min_price = criteria.get('price_min', 0)
        prop_price = property_data.get('price', 0)
        
        if not (min_price <= prop_price <= max_price):
            return False
        
        return True