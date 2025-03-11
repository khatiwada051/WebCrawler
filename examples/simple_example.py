"""
Simple example demonstrating how to use the scraper.
"""

import asyncio
import os
import json
import logging

from scraper.core.orchestrator import Orchestrator
from scraper.core.crawler import WebCrawler
from scraper.extractors.base import BaseExtractor
from scraper.formatters.json_formatter import JSONFormatter
from scraper.storage.storage_engine import StorageEngine

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('example')

# Example URL to scrape (a public product page)
EXAMPLE_URL = "https://books.toscrape.com/catalogue/category/books/science_22/index.html"

async def simple_example():
    """Run a simple example scraping a public website."""
    logger.info("Starting simple example")
    
    # Create components manually
    crawler = WebCrawler(
        base_url="https://books.toscrape.com",
        user_agent_rotation=True
    )
    
    extractor = BaseExtractor()
    formatter = JSONFormatter()
    
    # Create output directory
    os.makedirs("./data", exist_ok=True)
    storage = StorageEngine(output_dir="./data")
    
    try:
        # Initialize crawler
        await crawler.initialize()
        
        # Fetch the page
        logger.info(f"Fetching page: {EXAMPLE_URL}")
        html_content = await crawler.fetch_page(EXAMPLE_URL)
        
        # Extract data
        logger.info("Extracting data")
        raw_data = await extractor.extract(html_content, EXAMPLE_URL)
        
        # Format data
        logger.info("Formatting data")
        formatted_data = formatter.format(raw_data, "books-toscrape", EXAMPLE_URL)
        
        # Save data
        logger.info("Saving data")
        filepath = storage.save(formatted_data, "books_science")
        
        logger.info(f"Data saved to {filepath}")
        
        # Print summary
        if isinstance(raw_data, list):
            logger.info(f"Extracted {len(raw_data)} products")
        else:
            logger.info("Extracted page data")
    
    finally:
        # Clean up
        await crawler.close()
        logger.info("Example completed")

async def orchestrator_example():
    """Run an example using the Orchestrator."""
    logger.info("Starting orchestrator example")
    
    # Create a simple config
    config = {
        "concurrency": 1,
        "request_delay": 1.0,
        "user_agent_rotation": True,
        "storage": {
            "output_dir": "./data",
            "file_format": "json"
        }
    }
    
    # Create a simple site config
    site_config = {
        "site_id": "books-toscrape",
        "base_url": "https://books.toscrape.com",
        "login_required": False,
        "url_patterns": [
            "/catalogue/category/books/science_22/index.html"
        ]
    }
    
    # Save configs to temporary files
    os.makedirs("./temp", exist_ok=True)
    
    with open("./temp/config.json", "w") as f:
        json.dump(config, f)
    
    os.makedirs("./temp/sites", exist_ok=True)
    with open("./temp/sites/books-toscrape.json", "w") as f:
        json.dump(site_config, f)
    
    try:
        # Create and initialize orchestrator
        orchestrator = Orchestrator("./temp/config.json", "books-toscrape")
        orchestrator.initialize()
        
        # Run the scraper
        await orchestrator.run()
        
        # Print stats
        logger.info(f"Scraping completed with stats: {orchestrator.stats}")
    
    finally:
        # Clean up
        if orchestrator:
            orchestrator.cleanup()
        logger.info("Example completed")

if __name__ == "__main__":
    # Run the examples
    asyncio.run(simple_example())
    print("\n" + "-" * 50 + "\n")
    asyncio.run(orchestrator_example()) 