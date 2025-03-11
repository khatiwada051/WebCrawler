"""
Site Adapter Registry - Component that manages site-specific adapter modules.
"""

import logging
import importlib
import os
import json
from typing import Dict, Any, Optional, Type

from scraper.utils.exceptions import AdapterException

logger = logging.getLogger(__name__)

class BaseSiteAdapter:
    """Base class for site-specific adapters."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the site adapter.
        
        Args:
            config: Optional site-specific configuration
        """
        self.config = config or {}
    
    async def extract(self, soup, url: str, page_type: str) -> Any:
        """
        Extract data from a page using site-specific logic.
        
        Args:
            soup: BeautifulSoup object with parsed HTML
            url: URL of the page
            page_type: Type of page (product_list, product_detail, etc.)
            
        Returns:
            Extracted data
        """
        # Default implementation delegates to specific methods based on page type
        if page_type == 'product_list':
            return await self.extract_product_list(soup, url)
        elif page_type == 'product_detail':
            return await self.extract_product_detail(soup, url)
        else:
            return await self.extract_generic(soup, url)
    
    async def extract_product_list(self, soup, url: str) -> Any:
        """Extract data from a product list page."""
        raise NotImplementedError("Subclasses must implement extract_product_list method")
    
    async def extract_product_detail(self, soup, url: str) -> Any:
        """Extract data from a product detail page."""
        raise NotImplementedError("Subclasses must implement extract_product_detail method")
    
    async def extract_generic(self, soup, url: str) -> Any:
        """Extract data from a generic page."""
        raise NotImplementedError("Subclasses must implement extract_generic method")
    
    def determine_page_type(self, soup, url: str) -> str:
        """
        Determine the type of page based on site-specific rules.
        
        Args:
            soup: BeautifulSoup object with parsed HTML
            url: URL of the page
            
        Returns:
            Page type string
        """
        raise NotImplementedError("Subclasses must implement determine_page_type method")
    
    def verify_login_success(self, response_html: str) -> bool:
        """
        Verify if login was successful based on site-specific rules.
        
        Args:
            response_html: HTML response from login attempt
            
        Returns:
            True if login successful, False otherwise
        """
        raise NotImplementedError("Subclasses must implement verify_login_success method")


# Registry to keep track of all site adapters
_adapter_registry: Dict[str, Type[BaseSiteAdapter]] = {}

def register_adapter(site_id: str, adapter_class: Type[BaseSiteAdapter]) -> None:
    """
    Register a site adapter.
    
    Args:
        site_id: Unique identifier for the site
        adapter_class: Adapter class to register
    """
    global _adapter_registry
    _adapter_registry[site_id] = adapter_class
    logger.debug(f"Registered adapter for site: {site_id}")

def get_site_adapter(site_id: str, config: Optional[Dict[str, Any]] = None) -> Optional[BaseSiteAdapter]:
    """
    Get a site adapter instance.
    
    Args:
        site_id: Site identifier
        config: Optional configuration for the adapter
        
    Returns:
        Site adapter instance or None if not found
    """
    global _adapter_registry
    
    # First check if adapter is already registered
    adapter_class = _adapter_registry.get(site_id)
    
    # If not, try to dynamically load it
    if not adapter_class:
        try:
            # Try to import as a module
            module_name = f"scraper.sites.{site_id.replace('-', '_')}"
            module = importlib.import_module(module_name)
            
            # Look for the adapter class
            adapter_class = getattr(module, f"{site_id.title().replace('-', '')}Adapter")
            
            # Register it for future use
            register_adapter(site_id, adapter_class)
            
        except (ImportError, AttributeError) as e:
            logger.warning(f"No adapter found for site {site_id}: {str(e)}")
            return None
    
    # Load site-specific config if none provided
    if not config:
        config = _load_site_config(site_id)
    
    # Create and return instance
    return adapter_class(config)

def _load_site_config(site_id: str) -> Dict[str, Any]:
    """
    Load site-specific configuration.
    
    Args:
        site_id: Site identifier
        
    Returns:
        Site configuration dictionary
    """
    # Look for config in standard locations
    config_paths = [
        f"config/sites/{site_id}.json",
        f"../config/sites/{site_id}.json",
        os.path.join(os.path.expanduser("~"), ".scraper", "config", "sites", f"{site_id}.json")
    ]
    
    for path in config_paths:
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError):
            continue
    
    # Return empty config if not found
    logger.warning(f"No configuration found for site {site_id}")
    return {}

def list_available_adapters() -> Dict[str, str]:
    """
    List all available site adapters.
    
    Returns:
        Dictionary mapping site IDs to adapter class names
    """
    # Start with registered adapters
    adapters = {site_id: adapter_class.__name__ for site_id, adapter_class in _adapter_registry.items()}
    
    # Add adapters available as modules
    sites_dir = os.path.dirname(__file__)
    for filename in os.listdir(sites_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = filename[:-3]  # Remove .py extension
            site_id = module_name.replace('_', '-')
            
            if site_id not in adapters:
                try:
                    module = importlib.import_module(f"scraper.sites.{module_name}")
                    for attr_name in dir(module):
                        if attr_name.endswith('Adapter') and attr_name != 'BaseSiteAdapter':
                            adapters[site_id] = attr_name
                            break
                except ImportError:
                    continue
    
    return adapters

# Example implementation of a site adapter for demo purposes
class ExampleStoreAdapter(BaseSiteAdapter):
    """Example site adapter for demonstration purposes."""
    
    async def extract_product_list(self, soup, url: str) -> Any:
        """Extract product list data from example store."""
        products = []
        
        # Example implementation
        product_containers = soup.find_all('div', class_='product-item')
        
        for container in product_containers:
            product = {}
            
            # Extract name
            name_elem = container.find('h3', class_='product-name')
            if name_elem:
                product['name'] = name_elem.get_text(strip=True)
            
            # Extract price
            price_elem = container.find('span', class_='price')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                # Extract numeric price
                import re
                price_match = re.search(r'(\d+\.\d+)', price_text)
                if price_match:
                    product['price'] = {
                        'current': float(price_match.group(1)),
                        'currency': 'USD'
                    }
            
            # Extract URL
            link = container.find('a', class_='product-link', href=True)
            if link:
                product['url'] = link['href']
            
            # Add to product list
            if product:
                products.append(product)
        
        return products
    
    async def extract_product_detail(self, soup, url: str) -> Any:
        """Extract product detail data from example store."""
        product = {'url': url}
        
        # Extract name
        name_elem = soup.find('h1', class_='product-title')
        if name_elem:
            product['name'] = name_elem.get_text(strip=True)
        
        # Extract price
        price_elem = soup.find('div', class_='product-price')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            # Extract numeric price
            import re
            price_match = re.search(r'(\d+\.\d+)', price_text)
            if price_match:
                product['price'] = {
                    'current': float(price_match.group(1)),
                    'currency': 'USD'
                }
        
        # Extract description
        desc_elem = soup.find('div', class_='product-description')
        if desc_elem:
            product['description'] = desc_elem.get_text(strip=True)
        
        # Extract specifications
        specs = {}
        specs_table = soup.find('table', class_='specifications')
        if specs_table:
            for row in specs_table.find_all('tr'):
                cells = row.find_all(['th', 'td'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    if key and value:
                        specs[key] = value
        
        if specs:
            product['specifications'] = specs
        
        return product
    
    async def extract_generic(self, soup, url: str) -> Any:
        """Extract generic data from example store."""
        data = {'url': url}
        
        # Extract page title
        if soup.title:
            data['title'] = soup.title.get_text(strip=True)
        
        # Extract meta description
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and 'content' in meta_desc.attrs:
            data['description'] = meta_desc['content']
        
        return data
    
    def determine_page_type(self, soup, url: str) -> str:
        """Determine page type for example store."""
        import re
        
        # Check URL patterns
        if re.search(r'/product/\d+', url):
            return 'product_detail'
        
        if re.search(r'/category/|/search', url):
            return 'product_list'
        
        # Check page structure
        if soup.find('div', class_='product-detail'):
            return 'product_detail'
        
        if soup.find_all('div', class_='product-item'):
            return 'product_list'
        
        # Default
        return 'generic'
    
    def verify_login_success(self, response_html: str) -> bool:
        """Verify login success for example store."""
        return 'logout' in response_html.lower() or 'my account' in response_html.lower()

# Register the example adapter
register_adapter('example-store', ExampleStoreAdapter)

# Example usage
if __name__ == "__main__":
    # Get available adapters
    available_adapters = list_available_adapters()
    print("Available adapters:", available_adapters)
    
    # Get example adapter
    adapter = get_site_adapter('example-store')
    if adapter:
        print(f"Got adapter: {adapter.__class__.__name__}")
    else:
        print("Adapter not found") 