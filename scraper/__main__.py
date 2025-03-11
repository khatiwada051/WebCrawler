"""
Main entry point for the scraper package.
"""

import argparse
import asyncio
import logging
import os
import sys
import json
from typing import List, Optional

from scraper.core.orchestrator import Orchestrator
from scraper.auth.auth_manager import AuthManager
from scraper.utils.exceptions import ScraperException

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('scraper')

async def run_scraper(
    config_path: str,
    site_id: str,
    urls: Optional[List[str]] = None,
    with_login: bool = False,
    output_dir: Optional[str] = None
) -> None:
    """
    Run the scraper with the specified configuration.
    
    Args:
        config_path: Path to the global configuration file
        site_id: ID of the site to scrape
        urls: Optional specific URLs to scrape
        with_login: Whether to use authentication
        output_dir: Optional override for output directory
    """
    try:
        # Create and initialize orchestrator
        orchestrator = Orchestrator(config_path, site_id)
        
        # Override output directory if specified
        if output_dir:
            orchestrator.global_config['storage']['output_dir'] = output_dir
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
        
        # Override login_required based on with_login flag
        if with_login and not orchestrator.site_config.get('login_required', False):
            orchestrator.site_config['login_required'] = True
            logger.info("Enabling login for this session")
        
        # Initialize orchestrator components
        orchestrator.initialize()
        
        # Run the scraper
        await orchestrator.run(urls)
        
        # Clean up
        orchestrator.cleanup()
        
        logger.info(f"Scraping completed successfully for site: {site_id}")
        logger.info(f"Stats: {orchestrator.stats}")
    
    except ScraperException as e:
        logger.error(f"Scraping failed: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        sys.exit(1)

async def setup_auth(
    config_path: str,
    site_id: str,
    secure: bool = True
) -> None:
    """
    Set up authentication credentials for a site.
    
    Args:
        config_path: Path to the global configuration file
        site_id: ID of the site to set up credentials for
        secure: Whether to use secure storage
    """
    try:
        # Load site configuration to get credentials key
        site_config_path = os.path.join(os.path.dirname(config_path), 'sites', f'{site_id}.json')
        
        try:
            with open(site_config_path, 'r') as f:
                site_config = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load site configuration from {site_config_path}: {str(e)}")
            sys.exit(1)
        
        if 'authentication' not in site_config or 'credentials_key' not in site_config['authentication']:
            logger.error(f"Site configuration for {site_id} is missing authentication settings")
            sys.exit(1)
        
        # Create auth manager
        auth_manager = AuthManager(
            credentials_key=site_config['authentication']['credentials_key'],
            secure_storage=secure
        )
        
        # Prompt for credentials and save them
        credentials = await auth_manager._prompt_for_credentials()
        if credentials.get('save', False):
            del credentials['save']  # Remove save flag before storing
            
            if secure:
                success = auth_manager._store_in_keyring(credentials)
                if success:
                    logger.info(f"Credentials for {site_id} saved securely in the keyring")
                else:
                    logger.error("Failed to save credentials in keyring")
                    sys.exit(1)
            else:
                success = auth_manager._store_in_config(credentials)
                if success:
                    logger.info(f"Credentials for {site_id} saved in config file")
                else:
                    logger.error("Failed to save credentials in config file")
                    sys.exit(1)
        else:
            logger.info("Credentials not saved")
    
    except Exception as e:
        logger.exception(f"Failed to set up authentication: {str(e)}")
        sys.exit(1)

def main() -> None:
    """Command line interface for the scraper."""
    parser = argparse.ArgumentParser(description='AI-Powered Web Scraping Agent')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run the scraper')
    run_parser.add_argument('--config', default='config/config.json', help='Path to global config file')
    run_parser.add_argument('--site', required=True, help='Site ID to scrape')
    run_parser.add_argument('--urls', nargs='+', help='Specific URLs to scrape')
    run_parser.add_argument('--with-login', action='store_true', help='Use authentication')
    run_parser.add_argument('--output-dir', help='Override output directory')
    
    # Auth setup command
    auth_parser = subparsers.add_parser('auth', help='Authentication commands')
    auth_subparsers = auth_parser.add_subparsers(dest='auth_command', help='Authentication command')
    
    setup_parser = auth_subparsers.add_parser('setup', help='Set up authentication credentials')
    setup_parser.add_argument('--config', default='config/config.json', help='Path to global config file')
    setup_parser.add_argument('--site', required=True, help='Site ID to set up credentials for')
    setup_parser.add_argument('--no-secure', action='store_true', help='Do not use secure storage')
    
    # Schedule command (placeholder - actual implementation would be more complex)
    schedule_parser = subparsers.add_parser('schedule', help='Schedule recurring scraping jobs')
    schedule_parser.add_argument('--config', default='config/config.json', help='Path to global config file')
    schedule_parser.add_argument('--site', required=True, help='Site ID to schedule')
    schedule_parser.add_argument('--interval', required=True, help='Interval (e.g., 12h, 1d)')
    
    args = parser.parse_args()
    
    if args.command == 'run':
        asyncio.run(run_scraper(
            config_path=args.config,
            site_id=args.site,
            urls=args.urls,
            with_login=args.with_login,
            output_dir=args.output_dir
        ))
    elif args.command == 'auth' and args.auth_command == 'setup':
        asyncio.run(setup_auth(
            config_path=args.config,
            site_id=args.site,
            secure=not args.no_secure
        ))
    elif args.command == 'schedule':
        print(f"Scheduling scraping job for {args.site} with interval {args.interval}")
        print("Scheduling functionality is not yet implemented")
    else:
        parser.print_help()

if __name__ == '__main__':
    main() 