"""
Example demonstrating how to use the scraper with authentication.
"""

import asyncio
import os
import json
import logging
import getpass

from scraper.core.crawler import WebCrawler
from scraper.auth.auth_manager import AuthManager
from scraper.extractors.base import BaseExtractor
from scraper.formatters.json_formatter import JSONFormatter
from scraper.storage.storage_engine import StorageEngine

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('login_example')

# This is a demonstration - in a real scenario, you would use a real login-protected site
# For this example, we'll use a mock login page
MOCK_LOGIN_URL = "https://httpbin.org/forms/post"
MOCK_PROTECTED_URL = "https://httpbin.org/get"

async def login_example():
    """Run an example demonstrating login functionality."""
    logger.info("Starting login example")
    
    # Create components manually
    crawler = WebCrawler(
        base_url="https://httpbin.org",
        user_agent_rotation=True,
        use_browser=True  # Use browser automation for login
    )
    
    # Create auth manager
    auth_manager = AuthManager(
        credentials_key="httpbin-example",
        secure_storage=False  # Don't use secure storage for this example
    )
    
    extractor = BaseExtractor()
    formatter = JSONFormatter()
    
    # Create output directory
    os.makedirs("./data", exist_ok=True)
    storage = StorageEngine(output_dir="./data")
    
    try:
        # Initialize crawler
        await crawler.initialize()
        
        # Get credentials (in a real scenario, these would be stored securely)
        # For this example, we'll just use dummy credentials
        credentials = {
            'username': 'example_user',
            'password': 'example_password'
        }
        
        # Set up form selectors for the login page
        # These would be specific to the site you're scraping
        form_selectors = {
            'username': 'input[name="custname"]',  # Using httpbin's form fields
            'password': 'input[name="custtel"]',   # Using httpbin's form fields
            'submit': 'button[type="submit"]'
        }
        
        # Perform login
        logger.info("Performing login")
        
        # In a real scenario, you would use:
        # session = await auth_manager.authenticate(crawler, MOCK_LOGIN_URL, form_selectors)
        
        # For this example, we'll simulate a login by directly navigating to the page
        # and filling the form
        page = await crawler._context.new_page()
        await page.goto(MOCK_LOGIN_URL)
        
        # Fill the form
        await page.fill(form_selectors['username'], credentials['username'])
        await page.fill(form_selectors['password'], credentials['password'])
        
        # Submit the form
        await page.click(form_selectors['submit'])
        await page.wait_for_load_state('networkidle')
        
        # Close the page
        await page.close()
        
        # Now fetch a "protected" page
        logger.info(f"Fetching protected page: {MOCK_PROTECTED_URL}")
        html_content = await crawler.fetch_page(MOCK_PROTECTED_URL)
        
        # Extract data
        logger.info("Extracting data")
        raw_data = await extractor.extract(html_content, MOCK_PROTECTED_URL)
        
        # Format data
        logger.info("Formatting data")
        formatted_data = formatter.format(raw_data, "httpbin-example", MOCK_PROTECTED_URL)
        
        # Save data
        logger.info("Saving data")
        filepath = storage.save(formatted_data, "httpbin_protected")
        
        logger.info(f"Data saved to {filepath}")
    
    finally:
        # Clean up
        await crawler.close()
        logger.info("Example completed")

async def interactive_login_example():
    """Run an example with interactive login."""
    logger.info("Starting interactive login example")
    
    print("\nThis example demonstrates interactive login.")
    print("You will be prompted for credentials that will be used to log in to a mock site.")
    print("In a real scenario, these credentials would be stored securely.")
    
    # Prompt for credentials
    username = input("Username: ")
    password = getpass.getpass("Password: ")
    save_creds = input("Save credentials? (y/n): ").lower() == 'y'
    
    credentials = {
        'username': username,
        'password': password,
        'save': save_creds
    }
    
    # Create auth manager
    auth_manager = AuthManager(
        credentials_key="interactive-example",
        secure_storage=True
    )
    
    # Store credentials if requested
    if save_creds:
        if auth_manager._store_in_config(credentials):
            logger.info("Credentials saved to config file")
        else:
            logger.warning("Failed to save credentials")
    
    # Create crawler
    crawler = WebCrawler(
        base_url="https://httpbin.org",
        user_agent_rotation=True
    )
    
    try:
        # Initialize crawler
        await crawler.initialize()
        
        # Fetch a page (in a real scenario, this would be a protected page)
        logger.info("Fetching page (simulating authenticated request)")
        html_content = await crawler.fetch_page(MOCK_PROTECTED_URL)
        
        logger.info("Request successful")
        logger.info(f"In a real scenario, the credentials ({username}, {password[:1]}...) would be used for authentication")
    
    finally:
        # Clean up
        await crawler.close()
        logger.info("Example completed")

if __name__ == "__main__":
    # Run the examples
    asyncio.run(login_example())
    print("\n" + "-" * 50 + "\n")
    asyncio.run(interactive_login_example()) 