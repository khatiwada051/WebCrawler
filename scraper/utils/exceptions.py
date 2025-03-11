"""
Custom exceptions for the scraper.
"""

class ScraperException(Exception):
    """Base exception for all scraper errors."""
    pass

class CrawlerException(ScraperException):
    """Exception raised for errors in the web crawler."""
    pass

class AuthenticationException(ScraperException):
    """Exception raised for authentication errors."""
    pass

class ExtractionException(ScraperException):
    """Exception raised for errors during data extraction."""
    pass

class FormattingException(ScraperException):
    """Exception raised for errors during data formatting."""
    pass

class StorageException(ScraperException):
    """Exception raised for errors during data storage."""
    pass

class AdapterException(ScraperException):
    """Exception raised for errors in site adapters."""
    pass

class RateLimitException(ScraperException):
    """Exception raised when rate limits are exceeded."""
    pass 