"""
Rate Limiter - Utility for controlling request frequency to avoid overwhelming target servers.
"""

import logging
import asyncio
import time
from typing import Dict, Set, Optional
import random

from scraper.utils.exceptions import RateLimitException

logger = logging.getLogger(__name__)

class RateLimiter:
    """Controls request rates to avoid overwhelming target servers and prevent being blocked."""
    
    def __init__(
        self,
        delay: float = 1.0,
        jitter: float = 0.5,
        concurrent_requests: int = 1,
        domain_specific_delays: Optional[Dict[str, float]] = None
    ):
        """
        Initialize the rate limiter.
        
        Args:
            delay: Base delay between requests in seconds
            jitter: Random jitter to add to delay (+/- seconds)
            concurrent_requests: Maximum number of concurrent requests
            domain_specific_delays: Domain-specific delay overrides
        """
        self.delay = delay
        self.jitter = jitter
        self.concurrent_requests = concurrent_requests
        self.domain_specific_delays = domain_specific_delays or {}
        
        # Semaphore to control concurrency
        self._semaphore = asyncio.Semaphore(concurrent_requests)
        
        # Track last request time per domain
        self._last_request_time: Dict[str, float] = {}
        
        # Track domains currently being processed
        self._active_domains: Set[str] = set()
    
    async def wait_for_request(self, domain: Optional[str] = None) -> None:
        """
        Wait for rate limit to allow a request.
        
        Args:
            domain: Optional domain for domain-specific rate limiting
        """
        # If domain-specific, handle that logic
        if domain:
            await self._wait_for_domain(domain)
        else:
            # Simple rate limiting with jitter
            await self._apply_jittered_delay()
    
    async def _wait_for_domain(self, domain: str) -> None:
        """
        Apply domain-specific rate limiting.
        
        Args:
            domain: Domain to rate limit
        """
        # Get domain-specific delay or use default
        domain_delay = self.domain_specific_delays.get(domain, self.delay)
        
        # Check if we need to wait for this domain
        current_time = time.time()
        last_request = self._last_request_time.get(domain, 0)
        time_since_last = current_time - last_request
        
        if time_since_last < domain_delay and domain in self._active_domains:
            # Need to wait
            wait_time = domain_delay - time_since_last
            # Add some jitter
            wait_time += random.uniform(-self.jitter, self.jitter)
            wait_time = max(0, wait_time)  # Ensure non-negative
            
            logger.debug(f"Rate limiting for {domain}: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        
        # Mark domain as active and update last request time
        self._active_domains.add(domain)
        self._last_request_time[domain] = time.time()
    
    async def _apply_jittered_delay(self) -> None:
        """Apply simple rate limiting with jitter."""
        # Calculate delay with jitter
        jittered_delay = self.delay + random.uniform(-self.jitter, self.jitter)
        jittered_delay = max(0, jittered_delay)  # Ensure non-negative
        
        logger.debug(f"Rate limiting: waiting {jittered_delay:.2f}s")
        await asyncio.sleep(jittered_delay)
    
    async def acquire(self, domain: Optional[str] = None) -> bool:
        """
        Acquire permission to make a request (with concurrency control).
        Use this with an async context manager.
        
        Args:
            domain: Optional domain for domain-specific rate limiting
            
        Returns:
            True if acquired successfully
        """
        # First acquire semaphore for concurrency control
        await self._semaphore.acquire()
        
        try:
            # Then wait for rate limit
            await self.wait_for_request(domain)
            return True
        except Exception as e:
            # If waiting fails, release semaphore and propagate exception
            self._semaphore.release()
            raise
    
    def release(self, domain: Optional[str] = None) -> None:
        """
        Release the rate limiter after request is complete.
        
        Args:
            domain: Optional domain that was being accessed
        """
        # Update last request time for domain
        if domain:
            self._last_request_time[domain] = time.time()
        
        # Release semaphore
        self._semaphore.release()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.release()

# Example rate limiter with domain-specific settings
class DomainAwareRateLimiter(RateLimiter):
    """Extended rate limiter with more sophisticated domain handling."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Track request counts per domain
        self._request_counts: Dict[str, int] = {}
        
        # Track consecutive errors per domain
        self._error_counts: Dict[str, int] = {}
        
        # Backoff delays after errors
        self._backoff_delays: Dict[str, float] = {}
    
    async def wait_for_request(self, domain: Optional[str] = None) -> None:
        """
        Wait for rate limit to allow a request, with domain awareness.
        
        Args:
            domain: Optional domain for domain-specific rate limiting
        """
        if not domain:
            await super().wait_for_request(None)
            return
        
        # Check if domain is in backoff
        if domain in self._backoff_delays:
            backoff_delay = self._backoff_delays[domain]
            logger.warning(f"Domain {domain} in backoff mode: waiting {backoff_delay:.2f}s")
            await asyncio.sleep(backoff_delay)
        
        # Increment request count for domain
        self._request_counts[domain] = self._request_counts.get(domain, 0) + 1
        
        # Apply regular domain waiting logic
        await super().wait_for_request(domain)
    
    def report_success(self, domain: str) -> None:
        """
        Report a successful request to a domain.
        
        Args:
            domain: Domain that was successfully accessed
        """
        # Reset error count on success
        if domain in self._error_counts:
            del self._error_counts[domain]
        
        # Remove any backoff delay
        if domain in self._backoff_delays:
            del self._backoff_delays[domain]
    
    def report_error(self, domain: str, error_type: str = "general") -> None:
        """
        Report an error accessing a domain, which may trigger backoff.
        
        Args:
            domain: Domain that had an error
            error_type: Type of error that occurred
        """
        # Increment error count
        self._error_counts[domain] = self._error_counts.get(domain, 0) + 1
        error_count = self._error_counts[domain]
        
        # Calculate exponential backoff if needed
        if error_count >= 3:
            # Exponential backoff with capping
            backoff_delay = min(2 ** (error_count - 2), 300)  # Cap at 5 minutes
            
            # Add some randomness
            backoff_delay *= random.uniform(0.8, 1.2)
            
            self._backoff_delays[domain] = backoff_delay
            logger.warning(f"Domain {domain} has {error_count} consecutive errors. "
                          f"Setting backoff delay to {backoff_delay:.2f}s")
            
            # If many errors, temporarily block the domain
            if error_count >= 10:
                logger.error(f"Domain {domain} has too many errors. Blocking for 1 hour.")
                self._backoff_delays[domain] = 3600  # 1 hour

# Example usage
async def example_usage():
    """Example of how to use the rate limiter."""
    # Create rate limiter
    rate_limiter = RateLimiter(
        delay=1.0,
        jitter=0.5,
        concurrent_requests=3,
        domain_specific_delays={
            "example.com": 2.0,
            "slow-api.com": 5.0
        }
    )
    
    # Example of manual usage
    for i in range(5):
        # Wait for rate limit
        await rate_limiter.wait_for_request(domain="example.com")
        
        # Make the request (simulated here)
        print(f"Making request {i+1} to example.com")
        await asyncio.sleep(0.1)  # Simulate request
    
    # Example of context manager usage
    tasks = []
    for i in range(5):
        async def make_request(i):
            async with rate_limiter:
                print(f"Making concurrent request {i+1}")
                await asyncio.sleep(0.1)  # Simulate request
        
        tasks.append(asyncio.create_task(make_request(i)))
    
    # Wait for all tasks
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    # Run the example
    asyncio.run(example_usage()) 