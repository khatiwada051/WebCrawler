"""
Auth Manager - Component responsible for handling website authentication.
"""

import logging
import json
import os
import asyncio
import getpass
from typing import Dict, Optional, Tuple, Any
import keyring
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from scraper.utils.exceptions import AuthenticationException

logger = logging.getLogger(__name__)

class AuthManager:
    """Manages website authentication and session maintenance."""
    
    def __init__(self, credentials_key: str, secure_storage: bool = True):
        """
        Initialize the authentication manager.
        
        Args:
            credentials_key: Unique identifier for the credentials
            secure_storage: Whether to use secure system keyring
        """
        self.credentials_key = credentials_key
        self.secure_storage = secure_storage
        self.credentials = None
        self.session = None
    
    async def authenticate(self, crawler, login_url: str, form_selectors: Dict[str, str]) -> Any:
        """
        Authenticate with the website.
        
        Args:
            crawler: Web crawler instance to use for authentication
            login_url: URL of the login page
            form_selectors: Dictionary mapping form field names to CSS selectors
            
        Returns:
            Session object that can be used for subsequent requests
        """
        # Get credentials
        credentials = await self._get_credentials()
        if not credentials:
            raise AuthenticationException("No credentials available for authentication")
        
        # Log in using either browser automation or HTTP requests
        if crawler.use_browser:
            return await self._authenticate_with_browser(crawler, login_url, form_selectors, credentials)
        else:
            return await self._authenticate_with_http(crawler, login_url, form_selectors, credentials)
    
    async def _authenticate_with_browser(self, crawler, login_url: str, form_selectors: Dict[str, str], credentials: Dict[str, str]) -> Any:
        """Authenticate using browser automation."""
        from playwright.async_api import Page
        
        # Initialize the crawler if needed
        if not crawler._is_initialized:
            await crawler.initialize()
        
        # Create a new page
        page = await crawler._context.new_page()
        
        try:
            # Navigate to login page
            await page.goto(login_url, wait_until='networkidle')
            
            # Fill login form
            for field, value in credentials.items():
                if field in form_selectors and form_selectors[field]:
                    await page.fill(form_selectors[field], value)
            
            # Submit form
            if form_selectors.get('submit'):
                await page.click(form_selectors['submit'])
                await page.wait_for_load_state('networkidle')
            else:
                # Try to find a submit button or press Enter on the last field
                submit_button = await page.query_selector('button[type="submit"], input[type="submit"]')
                if submit_button:
                    await submit_button.click()
                    await page.wait_for_load_state('networkidle')
                else:
                    # Press Enter on the last field (usually password)
                    if form_selectors.get('password'):
                        await page.press(form_selectors['password'], 'Enter')
                        await page.wait_for_load_state('networkidle')
            
            # Check for successful login
            if not await self._verify_login_success(page):
                raise AuthenticationException("Login failed - verification check did not pass")
            
            # Get cookies for session maintenance
            cookies = await crawler._context.cookies()
            
            # Store cookies in crawler
            crawler._cookies = cookies
            
            logger.info("Authentication successful via browser automation")
            return crawler._context
        
        finally:
            await page.close()
    
    async def _authenticate_with_http(self, crawler, login_url: str, form_selectors: Dict[str, str], credentials: Dict[str, str]) -> Any:
        """Authenticate using HTTP requests."""
        import aiohttp
        
        # Initialize the crawler if needed
        if not crawler._is_initialized:
            await crawler.initialize()
        
        # Prepare form data for submission
        form_data = {}
        for field, value in credentials.items():
            # Form selectors may contain IDs or names - extract just the field name
            selector = form_selectors.get(field, '')
            if selector.startswith('#'):
                form_field_name = selector[1:]  # Remove # from ID
            elif selector.startswith('.'):
                # For class selectors, we need to get the actual field name
                # This is a simplification - in real scenarios, we might need to parse the form
                form_field_name = field
            else:
                form_field_name = selector.split('[')[-1].split('=')[0] if '[' in selector else field
            
            form_data[form_field_name] = value
        
        # Create a new session
        session = aiohttp.ClientSession(headers=crawler._get_headers())
        
        try:
            # Fetch login page first to get any CSRF tokens
            async with session.get(login_url) as response:
                html = await response.text()
                
                # Extract CSRF token if present (simplified example)
                csrf_token = self._extract_csrf_token(html)
                if csrf_token:
                    form_data['csrf_token'] = csrf_token
            
            # Submit login form
            login_endpoint = form_selectors.get('action', login_url)
            
            async with session.post(login_endpoint, data=form_data) as response:
                # Check for successful login based on redirect or response status
                if response.status not in (200, 301, 302, 303):
                    raise AuthenticationException(f"Login failed with status code {response.status}")
                
                html = await response.text()
                
                # Verify login success
                if not self._verify_login_success_html(html):
                    raise AuthenticationException("Login failed - verification check did not pass")
                
                # Store cookies for session maintenance
                cookies = []
                for name, cookie in response.cookies.items():
                    cookies.append({
                        'name': name,
                        'value': cookie.value,
                        'domain': cookie.get('domain', ''),
                        'path': cookie.get('path', '/')
                    })
                
                crawler._cookies = cookies
            
            logger.info("Authentication successful via HTTP request")
            return session
            
        except Exception as e:
            await session.close()
            raise AuthenticationException(f"Authentication failed: {str(e)}")
    
    async def _verify_login_success(self, page) -> bool:
        """
        Verify if login was successful using browser page.
        Override this method in site-specific adapters for custom verification logic.
        
        Args:
            page: Playwright Page object
            
        Returns:
            True if login successful, False otherwise
        """
        # Basic checks that might indicate successful login
        # 1. Check for common login failure messages
        failure_texts = [
            "incorrect password", "login failed", "invalid credentials",
            "username or password is incorrect", "authentication failed"
        ]
        
        page_content = await page.content()
        page_content = page_content.lower()
        
        for text in failure_texts:
            if text in page_content:
                return False
        
        # 2. Check for elements that typically appear after successful login
        success_indicators = [
            "logout", "sign out", "account", "profile", "dashboard"
        ]
        
        for indicator in success_indicators:
            if indicator in page_content:
                return True
        
        # Default to True if no failure indicators found
        # This is a simplification - real implementation would be more robust
        return True
    
    def _verify_login_success_html(self, html: str) -> bool:
        """
        Verify if login was successful using HTML response.
        Override this method in site-specific adapters for custom verification logic.
        
        Args:
            html: HTML content from response
            
        Returns:
            True if login successful, False otherwise
        """
        # Convert to lowercase for case-insensitive matching
        html_lower = html.lower()
        
        # Check for common failure indicators
        failure_texts = [
            "incorrect password", "login failed", "invalid credentials",
            "username or password is incorrect", "authentication failed"
        ]
        
        for text in failure_texts:
            if text in html_lower:
                return False
        
        # Check for success indicators
        success_indicators = [
            "logout", "sign out", "account", "profile", "dashboard"
        ]
        
        for indicator in success_indicators:
            if indicator in html_lower:
                return True
        
        # Default to True if no failure indicators found
        # This is a simplification - real implementation would be more robust
        return True
    
    def _extract_csrf_token(self, html: str) -> Optional[str]:
        """
        Extract CSRF token from HTML.
        
        Args:
            html: HTML content to parse
            
        Returns:
            CSRF token if found, None otherwise
        """
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Look for common CSRF token patterns
        # 1. Check meta tags
        meta = soup.find('meta', {'name': ['csrf-token', 'csrf-param', '_csrf_token']})
        if meta and 'content' in meta.attrs:
            return meta['content']
        
        # 2. Check hidden form fields
        csrf_input = soup.find('input', {'name': ['csrf_token', 'csrf', '_csrf_token', '_token']})
        if csrf_input and 'value' in csrf_input.attrs:
            return csrf_input['value']
        
        # 3. Check for data attributes with CSRF token
        csrf_element = soup.find(attrs={'data-csrf': True})
        if csrf_element and 'data-csrf' in csrf_element.attrs:
            return csrf_element['data-csrf']
        
        return None
    
    async def _get_credentials(self) -> Dict[str, str]:
        """
        Get credentials, either from secure storage or by prompting the user.
        
        Returns:
            Dictionary with credentials
        """
        if self.credentials:
            return self.credentials
        
        # Try to load from secure storage
        if self.secure_storage:
            stored_creds = self._get_from_keyring()
            if stored_creds:
                self.credentials = stored_creds
                return stored_creds
        
        # If not in secure storage, try config file
        config_creds = self._get_from_config()
        if config_creds:
            self.credentials = config_creds
            return config_creds
        
        # If not found anywhere, prompt the user
        logger.info("No stored credentials found, prompting user...")
        creds = await self._prompt_for_credentials()
        
        # Store for future use if requested
        if creds.get('save', False):
            del creds['save']  # Remove save flag before storing
            if self.secure_storage:
                self._store_in_keyring(creds)
            else:
                self._store_in_config(creds)
        
        self.credentials = creds
        return creds
    
    def _get_from_keyring(self) -> Optional[Dict[str, str]]:
        """Retrieve credentials from system keyring."""
        try:
            # Get encrypted credentials from keyring
            encrypted = keyring.get_password("scraper", self.credentials_key)
            if not encrypted:
                return None
            
            # Decrypt the credentials
            key = self._get_encryption_key()
            f = Fernet(key)
            decrypted = f.decrypt(encrypted.encode())
            
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.warning(f"Failed to get credentials from keyring: {str(e)}")
            return None
    
    def _store_in_keyring(self, credentials: Dict[str, str]) -> bool:
        """Store credentials in system keyring."""
        try:
            # Encrypt the credentials
            key = self._get_encryption_key()
            f = Fernet(key)
            encrypted = f.encrypt(json.dumps(credentials).encode())
            
            # Store in keyring
            keyring.set_password("scraper", self.credentials_key, encrypted.decode())
            return True
        except Exception as e:
            logger.error(f"Failed to store credentials in keyring: {str(e)}")
            return False
    
    def _get_encryption_key(self) -> bytes:
        """Generate encryption key from system info and site key."""
        import platform
        
        # Use system info as salt
        salt = platform.node().encode()[:16].ljust(16, b'0')
        
        # Use site key for password
        password = self.credentials_key.encode()
        
        # Generate key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def _get_from_config(self) -> Optional[Dict[str, str]]:
        """Retrieve credentials from config file."""
        try:
            config_dir = os.path.join(os.path.expanduser('~'), '.scraper')
            if not os.path.exists(config_dir):
                return None
            
            config_file = os.path.join(config_dir, 'credentials.json')
            if not os.path.exists(config_file):
                return None
            
            with open(config_file, 'r') as f:
                all_creds = json.load(f)
                return all_creds.get(self.credentials_key)
        except Exception as e:
            logger.warning(f"Failed to get credentials from config: {str(e)}")
            return None
    
    def _store_in_config(self, credentials: Dict[str, str]) -> bool:
        """Store credentials in config file."""
        try:
            config_dir = os.path.join(os.path.expanduser('~'), '.scraper')
            os.makedirs(config_dir, exist_ok=True)
            
            config_file = os.path.join(config_dir, 'credentials.json')
            
            # Load existing credentials if file exists
            all_creds = {}
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    all_creds = json.load(f)
            
            # Add or update credentials for this site
            all_creds[self.credentials_key] = credentials
            
            # Write back to file
            with open(config_file, 'w') as f:
                json.dump(all_creds, f)
                
            return True
        except Exception as e:
            logger.error(f"Failed to store credentials in config: {str(e)}")
            return False
    
    async def _prompt_for_credentials(self) -> Dict[str, str]:
        """Prompt user for credentials."""
        print(f"\nPlease enter credentials for {self.credentials_key}:")
        username = input("Username: ")
        password = getpass.getpass("Password: ")
        save = input("Save credentials for future use? (y/n): ").lower() == 'y'
        
        return {
            'username': username,
            'password': password,
            'save': save
        }

# Example setup function
def setup_credentials():
    """Set up credentials for a website interactively."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Set up authentication credentials')
    parser.add_argument('--site', required=True, help='Site ID')
    parser.add_argument('--secure', action='store_true', help='Use secure storage')
    
    args = parser.parse_args()
    
    auth_manager = AuthManager(args.site, args.secure)
    asyncio.run(auth_manager._prompt_for_credentials())
    print(f"Credentials set up for {args.site}")

if __name__ == "__main__":
    # Example usage
    setup_credentials() 