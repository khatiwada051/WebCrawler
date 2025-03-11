"""
Orchestrator - The central controller that coordinates all components of the scraping system.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
import json
import os

# Import core components
from scraper.core.crawler import WebCrawler
from scraper.extractors.base import BaseExtractor
from scraper.formatters.json_formatter import JSONFormatter
from scraper.storage.storage_engine import StorageEngine
from scraper.auth.auth_manager import AuthManager
from scraper.sites.adapter_registry import get_site_adapter
from scraper.utils.rate_limiter import RateLimiter
from scraper.utils.exceptions import ScraperException

logger = logging.getLogger(__name__)

class Orchestrator:
    """Main controller for the web scraping process that coordinates all components."""
    
    def __init__(self, config_path: str, site_id: str):
        """
        Initialize the orchestrator with configuration.
        
        Args:
            config_path: Path to the global configuration file
            site_id: Identifier for the site to scrape
        """
        self.global_config = self._load_config(config_path)
        self.site_id = site_id
        
        # Load site-specific configuration
        site_config_path = os.path.join(os.path.dirname(config_path), 'sites', f'{site_id}.json')
        self.site_config = self._load_config(site_config_path)
        
        # Initialize components
        self.auth_manager = None
        self.crawler = None
        self.extractor = None
        self.formatter = None
        self.storage = None
        self.rate_limiter = None
        
        # State tracking
        self.stats = {
            "pages_processed": 0,
            "items_extracted": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from a JSON file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            raise ScraperException(f"Failed to load configuration from {config_path}: {str(e)}")
    
    def initialize(self):
        """Initialize all components based on configuration."""
        # Set up logging
        self._setup_logging()
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            delay=self.global_config.get('request_delay', 1.0),
            concurrent_requests=self.global_config.get('concurrency', 1)
        )
        
        # Initialize auth manager if login is required
        if self.site_config.get('login_required', False):
            self.auth_manager = AuthManager(
                credentials_key=self.site_config['authentication']['credentials_key'],
                secure_storage=self.global_config.get('secure_storage', True)
            )
        
        # Initialize web crawler
        self.crawler = WebCrawler(
            base_url=self.site_config['base_url'],
            user_agent_rotation=self.global_config.get('user_agent_rotation', False),
            proxy_settings=self.global_config.get('proxy_settings', {}),
            rate_limiter=self.rate_limiter
        )
        
        # Get site adapter
        site_adapter = get_site_adapter(self.site_id)
        
        # Initialize extractor with site adapter
        self.extractor = BaseExtractor(site_adapter=site_adapter)
        
        # Initialize formatter
        self.formatter = JSONFormatter()
        
        # Initialize storage
        self.storage = StorageEngine(
            output_dir=self.global_config['storage']['output_dir'],
            file_format=self.global_config['storage']['file_format']
        )
        
        logger.info(f"Orchestrator initialized for site: {self.site_id}")
    
    def _setup_logging(self):
        """Configure logging based on configuration."""
        log_level = getattr(logging, self.global_config.get('log_level', 'INFO').upper())
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        if self.global_config.get('log_file'):
            logging.basicConfig(
                level=log_level,
                format=log_format,
                filename=self.global_config['log_file'],
                filemode='a'
            )
        else:
            logging.basicConfig(level=log_level, format=log_format)
    
    async def run(self, urls: Optional[List[str]] = None):
        """
        Execute the scraping process.
        
        Args:
            urls: Optional list of URLs to scrape. If not provided, will use configured start URLs.
        """
        self.stats['start_time'] = time.time()
        logger.info(f"Starting scraping process for site: {self.site_id}")
        
        try:
            # Handle authentication if needed
            if self.auth_manager:
                logger.info("Authenticating...")
                session = await self.auth_manager.authenticate(
                    self.crawler,
                    login_url=self.site_config['authentication']['login_url'],
                    form_selectors=self.site_config['authentication']['form_selectors']
                )
                self.crawler.set_session(session)
            
            # Determine URLs to scrape
            target_urls = urls or self._get_start_urls()
            
            # Process each URL
            for url in target_urls:
                try:
                    # Crawl the page
                    html_content = await self.crawler.fetch_page(url)
                    
                    # Extract data
                    raw_data = await self.extractor.extract(html_content, url)
                    
                    # Format the data
                    formatted_data = self.formatter.format(raw_data, self.site_id, url)
                    
                    # Store the data
                    self.storage.save(formatted_data, f"{self.site_id}_{int(time.time())}")
                    
                    self.stats['pages_processed'] += 1
                    self.stats['items_extracted'] += len(raw_data) if isinstance(raw_data, list) else 1
                
                except Exception as e:
                    logger.error(f"Error processing URL {url}: {str(e)}")
                    self.stats['errors'] += 1
        
        except Exception as e:
            logger.error(f"Scraping process failed: {str(e)}")
            raise
        
        finally:
            self.stats['end_time'] = time.time()
            duration = self.stats['end_time'] - self.stats['start_time']
            logger.info(f"Scraping process completed in {duration:.2f} seconds")
            logger.info(f"Stats: {self.stats}")
    
    def _get_start_urls(self) -> List[str]:
        """Get the list of URLs to start scraping from."""
        # If specific URLs are provided in config
        if 'start_urls' in self.site_config:
            return self.site_config['start_urls']
        
        # If URL patterns need to be generated (e.g., for category pages)
        if 'url_patterns' in self.site_config:
            base_url = self.site_config['base_url']
            patterns = self.site_config['url_patterns']
            return [f"{base_url}{pattern}" for pattern in patterns]
        
        # Default to just the base URL
        return [self.site_config['base_url']]
    
    def cleanup(self):
        """Perform cleanup operations after scraping is complete."""
        if self.crawler:
            self.crawler.close()
        logger.info("Cleanup complete")


# CLI entrypoint function example
def main():
    """Command-line interface for the scraper."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI-Powered Web Scraping Agent')
    parser.add_argument('--config', default='config/config.json', help='Path to config file')
    parser.add_argument('--site', required=True, help='Site ID to scrape')
    parser.add_argument('--urls', nargs='+', help='Specific URLs to scrape')
    
    args = parser.parse_args()
    
    # Create and initialize orchestrator
    orchestrator = Orchestrator(args.config, args.site)
    orchestrator.initialize()
    
    # Run the scraper
    try:
        asyncio.run(orchestrator.run(args.urls))
    finally:
        orchestrator.cleanup()


if __name__ == '__main__':
    main() 