"""
Base Extractor - Component responsible for extracting structured data from web pages.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from bs4 import BeautifulSoup
import re
import json

from scraper.utils.exceptions import ExtractionException

logger = logging.getLogger(__name__)

class BaseExtractor:
    """Base class for data extraction from web pages."""
    
    def __init__(self, site_adapter=None):
        """
        Initialize the extractor.
        
        Args:
            site_adapter: Optional adapter with site-specific extraction rules
        """
        self.site_adapter = site_adapter
    
    async def extract(self, html_content: str, url: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Extract data from HTML content.
        
        Args:
            html_content: HTML content to extract data from
            url: URL of the page (for context)
            
        Returns:
            Extracted data as a dictionary or list of dictionaries
        """
        try:
            # Parse HTML
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Determine page type
            page_type = self._determine_page_type(soup, url)
            logger.debug(f"Detected page type: {page_type}")
            
            # Use site adapter if available
            if self.site_adapter:
                return await self.site_adapter.extract(soup, url, page_type)
            
            # Default extraction based on page type
            if page_type == 'product_list':
                return await self._extract_product_list(soup, url)
            elif page_type == 'product_detail':
                return await self._extract_product_detail(soup, url)
            else:
                logger.warning(f"Unknown page type for URL: {url}")
                # Try generic extraction
                return await self._extract_generic(soup, url)
                
        except Exception as e:
            logger.error(f"Extraction failed for URL {url}: {str(e)}")
            raise ExtractionException(f"Failed to extract data from {url}: {str(e)}")
    
    def _determine_page_type(self, soup: BeautifulSoup, url: str) -> str:
        """
        Determine the type of page (product list, product detail, etc.).
        
        Args:
            soup: Parsed HTML
            url: URL of the page
            
        Returns:
            Page type string
        """
        # Use site adapter if available
        if self.site_adapter:
            return self.site_adapter.determine_page_type(soup, url)
        
        # Default detection logic
        
        # 1. Check URL patterns
        if re.search(r'/(products?|item|detail)/[a-zA-Z0-9_-]+', url):
            return 'product_detail'
            
        if re.search(r'/(category|collection|search|products|catalog)(/|$|\?)', url):
            return 'product_list'
        
        # 2. Check page structure
        # Product detail pages often have specific elements
        product_indicators = [
            soup.find('div', {'class': re.compile(r'product(-detail|-info|-main|_detail|_info)')}),
            soup.find('div', {'id': re.compile(r'product(-detail|-info|-main|_detail|_info)')}),
            soup.find('form', {'class': re.compile(r'(add-to-cart|buy-now)')}),
            soup.find('button', string=re.compile(r'(add to cart|buy now)', re.I))
        ]
        
        if any(product_indicators):
            return 'product_detail'
        
        # Product list pages often have repeating product elements
        product_list_patterns = [
            ('div', {'class': re.compile(r'product(-item|-card|_item|_card|s-item)')}),
            ('li', {'class': re.compile(r'product(-item|-card|_item|_card|s-item)')})
        ]
        
        for tag, attrs in product_list_patterns:
            if len(soup.find_all(tag, attrs)) > 1:
                return 'product_list'
        
        # Default to generic if can't determine
        return 'generic'
    
    async def _extract_product_list(self, soup: BeautifulSoup, url: str) -> List[Dict[str, Any]]:
        """
        Extract data from a product list page.
        
        Args:
            soup: Parsed HTML
            url: URL of the page
            
        Returns:
            List of extracted product data
        """
        products = []
        
        # Look for common product grid/list patterns
        product_containers = []
        
        # Try various common product container patterns
        for pattern in [
            ('div', {'class': re.compile(r'product(-item|-card|_item|_card)')}),
            ('li', {'class': re.compile(r'product(-item|-card|_item|_card)')}),
            ('div', {'class': re.compile(r'item(-product|-box|_product|_box)')}),
            ('div', {'data-product-id': True})
        ]:
            containers = soup.find_all(pattern[0], pattern[1])
            if containers:
                product_containers = containers
                break
        
        for container in product_containers:
            product = {}
            
            # Extract product ID/SKU
            product_id = None
            id_attrs = ['data-product-id', 'data-item-id', 'data-sku', 'id']
            for attr in id_attrs:
                if container.has_attr(attr):
                    product_id = container[attr]
                    break
            
            if product_id:
                product['id'] = product_id
            
            # Extract product URL
            link_elem = container.find('a', href=True)
            if link_elem:
                product['url'] = link_elem['href']
                if not product['url'].startswith(('http://', 'https://')):
                    # Convert relative URL to absolute
                    from urllib.parse import urljoin
                    product['url'] = urljoin(url, product['url'])
            
            # Extract product name
            name_elem = container.find(['h2', 'h3', 'h4', 'a'], {'class': re.compile(r'(product-name|title|name)')}) or \
                        container.find(['h2', 'h3', 'h4', 'a'])
            if name_elem:
                product['name'] = name_elem.get_text(strip=True)
            
            # Extract price
            price_elem = container.find(class_=re.compile(r'(price|product-price)'))
            if price_elem:
                # Clean up price text (remove currency symbols, etc.)
                price_text = price_elem.get_text(strip=True)
                price = self._extract_price(price_text)
                if price:
                    product['price'] = price
            
            # Extract image
            img_elem = container.find('img', src=True)
            if img_elem:
                img_src = img_elem['src']
                if img_src.startswith('data:'):
                    # Try to find data-src attribute for lazy-loaded images
                    for attr in ['data-src', 'data-original', 'data-lazy-src']:
                        if attr in img_elem.attrs:
                            img_src = img_elem[attr]
                            break
                
                if not img_src.startswith('data:'):
                    product['image_url'] = img_src
                    if not product['image_url'].startswith(('http://', 'https://')):
                        from urllib.parse import urljoin
                        product['image_url'] = urljoin(url, product['image_url'])
            
            # Add product to list if we have at least some data
            if product and ('name' in product or 'id' in product):
                products.append(product)
        
        return products
    
    async def _extract_product_detail(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Extract data from a product detail page.
        
        Args:
            soup: Parsed HTML
            url: URL of the page
            
        Returns:
            Extracted product data
        """
        product = {
            'url': url,
            'timestamp': self._get_timestamp(),
        }
        
        # Extract product name
        name_patterns = [
            ('h1', {}),
            ('h1', {'class': re.compile(r'(product-name|product-title|title|name)')}),
            ('div', {'class': re.compile(r'(product-name|product-title|title|name)')}),
        ]
        
        for tag, attrs in name_patterns:
            name_elem = soup.find(tag, attrs)
            if name_elem:
                product['name'] = name_elem.get_text(strip=True)
                break
        
        # Extract product ID/SKU
        sku_patterns = [
            ('span', {'class': re.compile(r'(sku|product-id|item-number)')}),
            ('div', {'class': re.compile(r'(sku|product-id|item-number)')}),
            ('meta', {'property': 'product:sku'}),
            ('*', {'data-product-id': True})
        ]
        
        for tag, attrs in sku_patterns:
            if tag == '*':
                # Search for any tag with the attribute
                for elem in soup.find_all(attrs=attrs):
                    product['id'] = elem['data-product-id']
                    break
            else:
                sku_elem = soup.find(tag, attrs)
                if sku_elem:
                    if 'content' in sku_elem.attrs:
                        product['id'] = sku_elem['content']
                    else:
                        sku_text = sku_elem.get_text(strip=True)
                        # Try to extract just the SKU number
                        sku_match = re.search(r'[A-Za-z0-9-_]+', sku_text)
                        if sku_match:
                            product['id'] = sku_match.group(0)
                        else:
                            product['id'] = sku_text
                    break
        
        # Extract price
        price_patterns = [
            ('span', {'class': re.compile(r'(price|product-price|sales-price|current-price)')}),
            ('div', {'class': re.compile(r'(price|product-price|sales-price|current-price)')}),
            ('meta', {'property': 'product:price:amount'})
        ]
        
        for tag, attrs in price_patterns:
            price_elem = soup.find(tag, attrs)
            if price_elem:
                if 'content' in price_elem.attrs:
                    try:
                        product['price'] = {'current': float(price_elem['content'])}
                    except ValueError:
                        pass
                else:
                    price_text = price_elem.get_text(strip=True)
                    price = self._extract_price(price_text)
                    if price:
                        product['price'] = price
                break
        
        # Extract description
        desc_patterns = [
            ('div', {'class': re.compile(r'(description|product-description|details|product-details)')}),
            ('p', {'class': re.compile(r'(description|product-description)')}),
            ('meta', {'name': 'description'})
        ]
        
        for tag, attrs in desc_patterns:
            desc_elem = soup.find(tag, attrs)
            if desc_elem:
                if 'content' in desc_elem.attrs:
                    product['description'] = desc_elem['content']
                else:
                    product['description'] = desc_elem.get_text(strip=True)
                break
        
        # Extract main image
        img_patterns = [
            ('img', {'class': re.compile(r'(product-image|main-image|gallery-image)')}),
            ('img', {'id': re.compile(r'(product-image|main-image)')}),
            ('meta', {'property': 'og:image'})
        ]
        
        for tag, attrs in img_patterns:
            img_elem = soup.find(tag, attrs)
            if img_elem:
                if 'content' in img_elem.attrs:
                    product['images'] = [{'url': img_elem['content'], 'type': 'primary'}]
                elif 'src' in img_elem.attrs:
                    img_src = img_elem['src']
                    if img_src.startswith('data:'):
                        # Try to find data-src attribute for lazy-loaded images
                        for attr in ['data-src', 'data-original', 'data-lazy-src']:
                            if attr in img_elem.attrs:
                                img_src = img_elem[attr]
                                break
                    
                    if not img_src.startswith('data:'):
                        if not img_src.startswith(('http://', 'https://')):
                            from urllib.parse import urljoin
                            img_src = urljoin(url, img_src)
                        product['images'] = [{'url': img_src, 'type': 'primary'}]
                break
        
        # Extract specifications/attributes
        spec_patterns = [
            ('table', {'class': re.compile(r'(specifications|specs|attributes|product-attributes)')}),
            ('div', {'class': re.compile(r'(specifications|specs|attributes|product-attributes)')})
        ]
        
        for tag, attrs in spec_patterns:
            specs_container = soup.find(tag, attrs)
            if specs_container:
                specs = {}
                
                # Handle table format
                if tag == 'table':
                    for row in specs_container.find_all('tr'):
                        cells = row.find_all(['th', 'td'])
                        if len(cells) >= 2:
                            key = cells[0].get_text(strip=True)
                            value = cells[1].get_text(strip=True)
                            if key and value:
                                specs[key] = value
                
                # Handle div format (common pattern: label + value pairs)
                else:
                    # Look for spec rows
                    spec_rows = specs_container.find_all('div', class_=re.compile(r'(row|item|pair|spec-item)'))
                    
                    # If no specific rows found, try to find label-value pairs
                    if not spec_rows:
                        labels = specs_container.find_all(['dt', 'span', 'div'], class_=re.compile(r'(label|name|key)'))
                        for label in labels:
                            key = label.get_text(strip=True)
                            # Try to find the corresponding value element (sibling or child of parent)
                            value_elem = label.find_next_sibling(['dd', 'span', 'div']) or \
                                        label.parent.find(['dd', 'span', 'div'], class_=re.compile(r'(value|data)'))
                            
                            if value_elem:
                                value = value_elem.get_text(strip=True)
                                if key and value:
                                    specs[key] = value
                    else:
                        # Process each spec row
                        for row in spec_rows:
                            key_elem = row.find(['span', 'div'], class_=re.compile(r'(label|name|key)'))
                            value_elem = row.find(['span', 'div'], class_=re.compile(r'(value|data)'))
                            
                            if key_elem and value_elem:
                                key = key_elem.get_text(strip=True)
                                value = value_elem.get_text(strip=True)
                                if key and value:
                                    specs[key] = value
                
                if specs:
                    product['specifications'] = specs
                break
        
        # Extract availability
        availability_patterns = [
            ('span', {'class': re.compile(r'(availability|stock-status|inventory)')}),
            ('div', {'class': re.compile(r'(availability|stock-status|inventory)')}),
            ('meta', {'property': 'product:availability'})
        ]
        
        for tag, attrs in availability_patterns:
            avail_elem = soup.find(tag, attrs)
            if avail_elem:
                if 'content' in avail_elem.attrs:
                    product['availability'] = avail_elem['content']
                else:
                    avail_text = avail_elem.get_text(strip=True).lower()
                    if any(term in avail_text for term in ['in stock', 'available', 'in-stock']):
                        product['availability'] = 'in_stock'
                    elif any(term in avail_text for term in ['out of stock', 'sold out', 'unavailable']):
                        product['availability'] = 'out_of_stock'
                    else:
                        product['availability'] = avail_text
                break
        
        # Extract brand
        brand_patterns = [
            ('span', {'class': re.compile(r'(brand|manufacturer)')}),
            ('div', {'class': re.compile(r'(brand|manufacturer)')}),
            ('meta', {'property': 'product:brand'})
        ]
        
        for tag, attrs in brand_patterns:
            brand_elem = soup.find(tag, attrs)
            if brand_elem:
                if 'content' in brand_elem.attrs:
                    product['brand'] = brand_elem['content']
                else:
                    product['brand'] = brand_elem.get_text(strip=True)
                break
        
        return product
    
    async def _extract_generic(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Generic data extraction for pages that don't match specific types.
        
        Args:
            soup: Parsed HTML
            url: URL of the page
            
        Returns:
            Extracted data
        """
        data = {
            'url': url,
            'timestamp': self._get_timestamp(),
            'title': soup.title.get_text(strip=True) if soup.title else None
        }
        
        # Extract meta description
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and 'content' in meta_desc.attrs:
            data['description'] = meta_desc['content']
        
        # Extract main content text
        main_content_patterns = [
            ('main', {}),
            ('div', {'id': 'content'}),
            ('div', {'id': 'main'}),
            ('article', {})
        ]
        
        for tag, attrs in main_content_patterns:
            content_elem = soup.find(tag, attrs)
            if content_elem:
                data['content'] = content_elem.get_text(strip=True)[:1000]  # Limit to 1000 chars
                break
        
        return data
    
    def _extract_price(self, price_text: str) -> Optional[Dict[str, Any]]:
        """
        Extract structured price information from text.
        
        Args:
            price_text: Text containing price information
            
        Returns:
            Dictionary with price information or None if extraction failed
        """
        # Remove extra spaces and non-breaking spaces
        price_text = price_text.replace('\xa0', ' ').strip()
        
        # Check for empty string
        if not price_text:
            return None
        
        # Extract prices using regular expressions
        price_data = {}
        
        # Try to extract currency
        currency_match = re.search(r'(\$|€|£|USD|EUR|GBP)', price_text)
        if currency_match:
            currency = currency_match.group(1)
            if currency == '$':
                currency = 'USD'
            elif currency == '€':
                currency = 'EUR'
            elif currency == '£':
                currency = 'GBP'
            price_data['currency'] = currency
        
        # Extract numeric prices
        # 1. Current/sale price (the main price)
        price_match = re.search(r'([\d,]+\.?\d*)', price_text)
        if price_match:
            try:
                current_price = float(price_match.group(1).replace(',', ''))
                price_data['current'] = current_price
            except ValueError:
                pass
        
        # 2. Original price (often for discounted items)
        original_match = re.search(r'(?:was|original|reg)\D*?([\d,]+\.?\d*)', price_text, re.IGNORECASE)
        if original_match:
            try:
                original_price = float(original_match.group(1).replace(',', ''))
                price_data['original'] = original_price
                
                # Calculate discount percentage if both prices are available
                if 'current' in price_data and original_price > price_data['current']:
                    discount_pct = round((original_price - price_data['current']) / original_price * 100)
                    price_data['discount_percentage'] = discount_pct
            except ValueError:
                pass
        
        # If we found any price data, return it
        return price_data if price_data else None
    
    def _get_timestamp(self) -> str:
        """Get the current timestamp in ISO format."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    async def enhance_with_ai(self, data: Dict[str, Any], html_content: str) -> Dict[str, Any]:
        """
        Enhance extracted data using AI techniques.
        
        Args:
            data: Initially extracted data
            html_content: Original HTML content
            
        Returns:
            Enhanced data
        """
        # This is just a placeholder - actual implementation would use NLP/ML
        # to improve data extraction based on context
        return data

class AIExtractor(BaseExtractor):
    """Enhanced extractor that uses AI techniques for improved extraction."""
    
    def __init__(self, site_adapter=None, use_spacy=True, use_transformers=False):
        """
        Initialize the AI extractor.
        
        Args:
            site_adapter: Optional adapter with site-specific extraction rules
            use_spacy: Whether to use spaCy for NLP
            use_transformers: Whether to use transformer models for advanced NLP
        """
        super().__init__(site_adapter)
        self.use_spacy = use_spacy
        self.use_transformers = use_transformers
        self.nlp = None
        
        # Initialize NLP if enabled
        if use_spacy:
            self._initialize_spacy()
    
    def _initialize_spacy(self):
        """Initialize spaCy NLP model."""
        try:
            import spacy
            self.nlp = spacy.load("en_core_web_md")
            logger.info("spaCy model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load spaCy model: {str(e)}")
            self.use_spacy = False
    
    async def extract(self, html_content: str, url: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Extract data with AI enhancement.
        
        Args:
            html_content: HTML content to extract data from
            url: URL of the page
            
        Returns:
            Extracted and enhanced data
        """
        # First, do standard extraction
        data = await super().extract(html_content, url)
        
        # Then enhance with AI
        if isinstance(data, dict):
            return await self.enhance_with_ai(data, html_content)
        elif isinstance(data, list):
            enhanced_items = []
            for item in data:
                enhanced_items.append(await self.enhance_with_ai(item, html_content))
            return enhanced_items
        
        return data
    
    async def enhance_with_ai(self, data: Dict[str, Any], html_content: str) -> Dict[str, Any]:
        """
        Enhance extracted data using AI techniques.
        
        Args:
            data: Initially extracted data
            html_content: Original HTML content
            
        Returns:
            Enhanced data
        """
        enhanced_data = data.copy()
        
        # Use spaCy for entity recognition and enhancement
        if self.use_spacy and self.nlp:
            # Extract and enhance product name
            if 'name' in data:
                doc = self.nlp(data['name'])
                
                # Try to extract brand from name if not already present
                if 'brand' not in data:
                    entities = [(ent.text, ent.label_) for ent in doc.ents]
                    orgs = [ent[0] for ent in entities if ent[1] == 'ORG']
                    if orgs:
                        enhanced_data['brand'] = orgs[0]
            
            # Enhanced description extraction
            if 'description' in data:
                doc = self.nlp(data['description'])
                
                # Extract key phrases
                key_phrases = [chunk.text for chunk in doc.noun_chunks if len(chunk.text.split()) > 1]
                if key_phrases:
                    enhanced_data['key_features'] = key_phrases[:5]  # Limit to top 5
        
        # Add confidence score for extraction quality
        keys_extracted = len(enhanced_data)
        expected_keys = 8  # Expected number of keys for a complete product
        confidence = min(0.3 + (keys_extracted / expected_keys * 0.7), 1.0)  # Scale from 0.3 to 1.0
        
        enhanced_data['metadata'] = {
            'confidence_score': round(confidence, 2),
            'extracted_fields_count': keys_extracted,
            'ai_enhanced': True
        }
        
        return enhanced_data

# Example usage
async def example_usage():
    """Example of how to use the BaseExtractor class."""
    import aiohttp
    
    async with aiohttp.ClientSession() as session:
        # Fetch a sample product page
        async with session.get('https://example.com/product/123') as response:
            html_content = await response.text()
            
            # Create extractor
            extractor = BaseExtractor()
            
            # Extract data
            data = await extractor.extract(html_content, 'https://example.com/product/123')
            
            print(json.dumps(data, indent=2))

if __name__ == "__main__":
    # Run the example
    asyncio.run(example_usage()) 