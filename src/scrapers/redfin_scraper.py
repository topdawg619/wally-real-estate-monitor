"""
Redfin.com scraper with JSON data extraction.
"""

import json
import re
from typing import List, Dict, Optional
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

class RedfinScraper(BaseScraper):
    """Scraper for Redfin.com real estate listings."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = "https://www.redfin.com"
    
    def get_site_name(self) -> str:
        return "redfin"
    
    def build_search_url(self, zip_codes: List[str], **criteria) -> str:
        """Build Redfin search URL."""
        # Join ZIP codes for search
        location = ", ".join(zip_codes)
        
        # Build URL parameters
        params = []
        
        # Bedrooms
        min_beds = criteria.get('bedrooms_min', 5)
        params.append(f"min-beds={min_beds}")
        
        # Bathrooms  
        min_baths = criteria.get('bathrooms_min', 3)
        params.append(f"min-baths={min_baths}")
        
        # Price range
        if 'price_min' in criteria:
            params.append(f"min-price={criteria['price_min']}")
        if 'price_max' in criteria:
            params.append(f"max-price={criteria['price_max']}")
        
        # Property types (default to single family)
        prop_types = criteria.get('property_types', ['Single Family'])
        if 'Single Family' in prop_types:
            params.append("property-type=house")
        
        # Build the URL
        location_encoded = quote_plus(location)
        params_str = "&".join(params)
        
        return f"{self.base_url}/city/{location_encoded}/filter/{params_str}"
    
    def extract_listings(self, response) -> List[Dict]:
        """Extract listings from Redfin search results."""
        properties = []
        
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Method 1: Try to find JSON data in script tags
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string and 'window.__reactTransferState' in script.string:
                    properties.extend(self._extract_from_react_data(script.string))
                    break
            
            # Method 2: Parse HTML elements if JSON not found
            if not properties:
                properties.extend(self._extract_from_html(soup))
                
        except Exception as e:
            self.logger.error(f"Error extracting Redfin listings: {str(e)}")
        
        return [self.standardize_property(prop) for prop in properties if self._is_valid_listing(prop)]
    
    def _extract_from_react_data(self, script_content: str) -> List[Dict]:
        """Extract properties from React JSON data."""
        properties = []
        
        try:
            # Find the JSON data
            start_marker = 'window.__reactTransferState'
            start_index = script_content.find(start_marker)
            if start_index == -1:
                return properties
            
            # Extract JSON portion
            json_start = script_content.find('{', start_index)
            json_end = script_content.rfind('}') + 1
            
            if json_start == -1 or json_end == -1:
                return properties
            
            json_str = script_content[json_start:json_end]
            data = json.loads(json_str)
            
            # Navigate to property listings (structure may vary)
            homes = self._find_homes_in_data(data)
            
            for home in homes:
                prop = self._parse_redfin_home(home)
                if prop:
                    properties.append(prop)
                    
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.warning(f"Could not parse Redfin JSON data: {str(e)}")
        
        return properties
    
    def _find_homes_in_data(self, data: Dict) -> List[Dict]:
        """Find homes data within the React state object."""
        homes = []
        
        # Common paths where Redfin stores listing data
        search_paths = [
            ['searchResults', 'homes'],
            ['homes'],
            ['listings'],
            ['properties']
        ]
        
        for path in search_paths:
            current = data
            try:
                for key in path:
                    current = current[key]
                if isinstance(current, list):
                    homes = current
                    break
            except (KeyError, TypeError):
                continue
        
        # If direct paths don't work, search recursively
        if not homes:
            homes = self._recursive_find_homes(data)
        
        return homes
    
    def _recursive_find_homes(self, obj, depth=0, max_depth=5) -> List[Dict]:
        """Recursively search for home listings in the data structure."""
        if depth > max_depth:
            return []
        
        homes = []
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in ['homes', 'listings', 'properties'] and isinstance(value, list):
                    # Check if this looks like property data
                    if value and isinstance(value[0], dict) and 'address' in value[0]:
                        homes.extend(value)
                else:
                    homes.extend(self._recursive_find_homes(value, depth + 1, max_depth))
        elif isinstance(obj, list):
            for item in obj:
                homes.extend(self._recursive_find_homes(item, depth + 1, max_depth))
        
        return homes
    
    def _parse_redfin_home(self, home: Dict) -> Optional[Dict]:
        """Parse a single home from Redfin JSON data."""
        try:
            return {
                'address': self._get_address(home),
                'zip_code': home.get('address', {}).get('zip', ''),
                'price': home.get('price', {}).get('value'),
                'bedrooms': home.get('beds'),
                'bathrooms': home.get('baths'),
                'square_feet': home.get('sqFt', {}).get('value'),
                'property_type': home.get('propertyType', ''),
                'listing_url': self._build_listing_url(home),
                'mls_id': home.get('mlsId', ''),
                'listing_date': home.get('listingDate'),
                'status': home.get('mlsStatus', 'active')
            }
        except Exception as e:
            self.logger.warning(f"Error parsing Redfin home data: {str(e)}")
            return None
    
    def _get_address(self, home: Dict) -> str:
        """Extract full address from home data."""
        address_parts = []
        
        address_obj = home.get('address', {})
        
        if 'streetNumber' in address_obj:
            address_parts.append(str(address_obj['streetNumber']))
        if 'streetName' in address_obj:
            address_parts.append(address_obj['streetName'])
        if 'city' in address_obj:
            address_parts.append(address_obj['city'])
        if 'state' in address_obj:
            address_parts.append(address_obj['state'])
        if 'zip' in address_obj:
            address_parts.append(address_obj['zip'])
        
        return ", ".join(address_parts)
    
    def _build_listing_url(self, home: Dict) -> str:
        """Build the full listing URL."""
        url_path = home.get('url', '')
        if url_path:
            return f"{self.base_url}{url_path}"
        return ""
    
    def _extract_from_html(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract properties from HTML elements as fallback."""
        properties = []
        
        # Look for property containers (this may need updates as Redfin changes)
        listing_containers = soup.find_all('div', {'class': re.compile(r'.*HomeCard.*|.*listing.*', re.I)})
        
        for container in listing_containers:
            try:
                prop = self._parse_html_listing(container)
                if prop:
                    properties.append(prop)
            except Exception as e:
                self.logger.warning(f"Error parsing HTML listing: {str(e)}")
        
        return properties
    
    def _parse_html_listing(self, container) -> Optional[Dict]:
        """Parse a single listing from HTML elements."""
        try:
            # This is a simplified HTML parser - may need updates
            address_elem = container.find('a', {'data-rf-test-id': 'titleText'})
            address = address_elem.get_text(strip=True) if address_elem else ""
            
            price_elem = container.find('span', {'data-rf-test-id': 'homecard-price'})
            price = price_elem.get_text(strip=True) if price_elem else ""
            
            beds_elem = container.find('span', {'data-rf-test-id': 'homecard-beds'})
            beds = beds_elem.get_text(strip=True) if beds_elem else ""
            
            baths_elem = container.find('span', {'data-rf-test-id': 'homecard-baths'})
            baths = baths_elem.get_text(strip=True) if baths_elem else ""
            
            sqft_elem = container.find('span', {'data-rf-test-id': 'homecard-sqft'})
            sqft = sqft_elem.get_text(strip=True) if sqft_elem else ""
            
            url_elem = container.find('a', href=True)
            listing_url = f"{self.base_url}{url_elem['href']}" if url_elem else ""
            
            # Extract ZIP code from address
            zip_match = re.search(r'\\b(\\d{5})\\b', address)
            zip_code = zip_match.group(1) if zip_match else ""
            
            return {
                'address': address,
                'zip_code': zip_code,
                'price': price,
                'bedrooms': beds,
                'bathrooms': baths,
                'square_feet': sqft,
                'property_type': 'Single Family',  # Default
                'listing_url': listing_url,
                'mls_id': '',
                'listing_date': None,
                'status': 'active'
            }
            
        except Exception as e:
            self.logger.warning(f"Error parsing HTML listing: {str(e)}")
            return None
    
    def _is_valid_listing(self, prop: Dict) -> bool:
        """Check if the listing has minimum required data."""
        return (
            prop.get('address') and 
            prop.get('price') and
            prop.get('bedrooms') is not None
        )
    
    def parse_listing(self, listing_element) -> Optional[Dict]:
        """Parse a single listing element (for compatibility with base class)."""
        return self._parse_html_listing(listing_element)