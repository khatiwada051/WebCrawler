"""
Web Crawler - Component responsible for navigating websites and retrieving content.
"""

import logging
import random
import asyncio
from typing import Dict, List, Optional, Union, Any
import aiohttp
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import time
from urllib.parse import urljoin

from scraper.utils.rate_limiter import RateLimiter
from scraper.utils.exceptions import CrawlerException
from scraper.utils.user_agents import USER_AGENTS

logger = logging.getLogger(__name__)

class WebCrawler:
    """
    Handles HTTP requests, browser automation, and content retrieval.
    Supports both simple HTTP requests and full browser automation.
    """
    
    def __init__(
        self,
        base_url: str,
        user_agent_rotation: bool = False,
        proxy_settings: Dict[str, Any] = None,
        rate_limiter: Optional[RateLimiter] = None,
        headers: Dict[str, str] = None,
        use_browser: bool = False
    ):
        """
        Initialize the web crawler.
        
        Args:
            base_url: Base URL for the website
            user_agent_rotation: Whether to rotate user agents
            proxy_settings: Dictionary with proxy configuration
            rate_limiter: Rate limiter for controlling request frequency
            headers: Custom headers for HTTP requests
            use_browser: Whether to use full browser automation
        """
        self.base_url = base_url
        self.user_agent_rotation = user_agent_rotation
        self.proxy_settings = proxy_settings or {}
        self.rate_limiter = rate_limiter or RateLimiter()
        self.headers = headers or {}
        self.use_browser = use_browser
        
        # HTTP session
        self._session = None
        
        # Browser automation
        self._playwright = None
        self._browser = None
        self._context = None
        
        # State
        self._cookies = []
        self._is_initialized = False
    
    async def initialize(self):
        """Initialize the crawler (either HTTP session or browser)."""
        if self._is_initialized:
            return
        
        if self.use_browser:
            await self._initialize_browser()
        else:
            await self._initialize_session()
        
        self._is_initialized = True
    
    async def _initialize_session(self):
        """Initialize HTTP session with aiohttp."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers=self._get_headers(),
                cookies={cookie['name']: cookie['value'] for cookie in self._cookies if 'name' in cookie and 'value' in cookie}
            )
    
    async def _initialize_browser(self):
        """Initialize browser automation with Playwright."""
        self._playwright = await async_playwright().start()
        
        # Set up browser launch options
        browser_type = self._playwright.chromium
        launch_options = {}
        
        # Configure proxy if enabled
        if self.proxy_settings.get('enabled', False):
            launch_options['proxy'] = {
                'server': self.proxy_settings.get('server', ''),
                'username': self.proxy_settings.get('username', ''),
                'password': self.proxy_settings.get('password', '')
            }
        
        # Launch browser
        self._browser = await browser_type.launch(
            headless=True,  # Set to False for debugging
            **launch_options
        )
        
        # Create context with custom user agent if rotation is enabled
        context_options = {}
        if self.user_agent_rotation:
            context_options['user_agent'] = self._get_random_user_agent()
        
        self._context = await self._browser.new_context(**context_options)
        
        # Restore cookies if any
        if self._cookies:
            await self._context.add_cookies(self._cookies)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for HTTP requests, with optional user agent rotation."""
        headers = self.headers.copy()
        
        if self.user_agent_rotation and 'User-Agent' not in headers:
            headers['User-Agent'] = self._get_random_user_agent()
        
        return headers
    
    def _get_random_user_agent(self) -> str:
        """Get a random user agent from the predefined list."""
        return random.choice(USER_AGENTS)
    
    def set_session(self, session: aiohttp.ClientSession):
        """Set a custom session (useful after authentication)."""
        if self._session and not self._session.closed:
            asyncio.create_task(self._session.close())
        self._session = session
    
    async def fetch_page(self, url: str, params: Dict[str, str] = None) -> str:
        """
        Fetch a web page using either HTTP requests or browser automation.
        
        Args:
            url: The URL to fetch
            params: Optional query parameters
            
        Returns:
            The HTML content of the page
        """
        # Make sure the crawler is initialized
        if not self._is_initialized:
            await self.initialize()
        
        # Apply rate limiting
        await self.rate_limiter.wait_for_request()
        
        # Normalize URL
        if not url.startswith(('http://', 'https://')):
            url = urljoin(self.base_url, url)
        
        try:
            if self.use_browser:
                return await self._fetch_with_browser(url, params)
            else:
                return await self._fetch_with_http(url, params)
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            raise CrawlerException(f"Failed to fetch page {url}: {str(e)}")
    
    async def _fetch_with_http(self, url: str, params: Dict[str, str] = None) -> str:
        """Fetch page using HTTP requests."""
        async with self._session.get(
            url,
            params=params,
            proxy=self.proxy_settings.get('server') if self.proxy_settings.get('enabled', False) else None,
            timeout=aiohttp.ClientTimeout(total=30)  # 30-second timeout
        ) as response:
            # Check for successful response
            if response.status != 200:
                raise CrawlerException(f"HTTP error {response.status} when fetching {url}")
            
            # Extract and store any cookies
            if response.cookies:
                for name, cookie in response.cookies.items():
                    self._cookies.append({
                        'name': name,
                        'value': cookie.value,
                        'domain': cookie.get('domain', ''),
                        'path': cookie.get('path', '/')
                    })
            
            # Return page content
            return await response.text()
    
    async def _fetch_with_browser(self, url: str, params: Dict[str, str] = None) -> str:
        """Fetch page using browser automation."""
        # Create page
        page = await self._context.new_page()
        
        try:
            # Build URL with params if provided
            if params:
                query_string = '&'.join(f"{k}={v}" for k, v in params.items())
                url = f"{url}?{query_string}" if '?' not in url else f"{url}&{query_string}"
            
            # Navigate to the page
            await page.goto(url, wait_until='networkidle')
            
            # Extract and store cookies
            cookies = await self._context.cookies()
            if cookies:
                self._cookies = cookies
            
            # Return page content
            return await page.content()
        finally:
            await page.close()
    
    async def click_and_wait(self, page: Page, selector: str, timeout: int = 5000) -> None:
        """
        Click an element and wait for navigation or network idle.
        
        Args:
            page: Playwright Page object
            selector: CSS selector for the element to click
            timeout: Timeout in milliseconds
        """
        try:
            await page.click(selector)
            await page.wait_for_load_state('networkidle', timeout=timeout)
        except Exception as e:
            logger.error(f"Error clicking element {selector}: {str(e)}")
            raise CrawlerException(f"Failed to click element {selector}: {str(e)}")
    
    async def fill_form(self, page: Page, form_selectors: Dict[str, str], form_data: Dict[str, str]) -> None:
        """
        Fill a form on a page.
        
        Args:
            page: Playwright Page object
            form_selectors: Dictionary of field names to CSS selectors
            form_data: Dictionary of field names to values
        """
        try:
            for field, value in form_data.items():
                if field in form_selectors:
                    await page.fill(form_selectors[field], value)
        except Exception as e:
            logger.error(f"Error filling form: {str(e)}")
            raise CrawlerException(f"Failed to fill form: {str(e)}")
    
    async def extract_links(self, html_content: str, base_url: str = None) -> List[str]:
        """
        Extract links from HTML content.
        
        Args:
            html_content: HTML content to parse
            base_url: Base URL for resolving relative links
            
        Returns:
            List of extracted URLs
        """
        from bs4 import BeautifulSoup
        
        base = base_url or self.base_url
        soup = BeautifulSoup(html_content, 'lxml')
        
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith(('http://', 'https://')):
                links.append(href)
            else:
                links.append(urljoin(base, href))
        
        return links
    
    async def close(self):
        """Clean up resources."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        
        if self._browser:
            await self._browser.close()
            self._browser = None
        
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        
        self._is_initialized = False

# Example usage function
async def example_usage():
    """Example of how to use the WebCrawler class."""
    # Create a crawler
    crawler = WebCrawler(
        base_url="https://example.com",
        user_agent_rotation=True,
        use_browser=True
    )
    
    try:
        # Initialize
        await crawler.initialize()
        
        # Fetch a page
        html_content = await crawler.fetch_page("/products")
        
        # Extract links
        links = await crawler.extract_links(html_content)
        print(f"Found {len(links)} links on the page")
        
    finally:
        # Clean up
        await crawler.close()

if __name__ == "__main__":
    # Run the example
    asyncio.run(example_usage()) 