"""
Collection of user agent strings for browser emulation.
"""

# List of common user agents for different browsers and devices
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
    
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_5_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
    
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:92.0) Gecko/20100101 Firefox/92.0",
    
    # Firefox on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:91.0) Gecko/20100101 Firefox/91.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:92.0) Gecko/20100101 Firefox/92.0",
    
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
    
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36 Edg/92.0.902.73",
    
    # Opera on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 OPR/77.0.4054.254",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36 OPR/78.0.4093.147",
    
    # Chrome on Android
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.115 Mobile Safari/537.36",
    
    # Safari on iOS
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
]

def get_random_user_agent() -> str:
    """
    Get a random user agent from the list.
    
    Returns:
        Random user agent string
    """
    import random
    return random.choice(USER_AGENTS)

def get_desktop_user_agent() -> str:
    """
    Get a random desktop user agent.
    
    Returns:
        Random desktop user agent string
    """
    import random
    desktop_agents = [ua for ua in USER_AGENTS if "Mobile" not in ua and "Android" not in ua and "iPhone" not in ua and "iPad" not in ua]
    return random.choice(desktop_agents)

def get_mobile_user_agent() -> str:
    """
    Get a random mobile user agent.
    
    Returns:
        Random mobile user agent string
    """
    import random
    mobile_agents = [ua for ua in USER_AGENTS if "Mobile" in ua or "Android" in ua or "iPhone" in ua or "iPad" in ua]
    return random.choice(mobile_agents)

def get_browser_specific_user_agent(browser: str) -> str:
    """
    Get a random user agent for a specific browser.
    
    Args:
        browser: Browser name (chrome, firefox, safari, edge, opera)
        
    Returns:
        Random user agent for the specified browser
    """
    import random
    browser = browser.lower()
    
    if browser == "chrome":
        chrome_agents = [ua for ua in USER_AGENTS if "Chrome" in ua and "Edg" not in ua and "OPR" not in ua]
        return random.choice(chrome_agents)
    elif browser == "firefox":
        firefox_agents = [ua for ua in USER_AGENTS if "Firefox" in ua]
        return random.choice(firefox_agents)
    elif browser == "safari":
        safari_agents = [ua for ua in USER_AGENTS if "Safari" in ua and "Chrome" not in ua]
        return random.choice(safari_agents)
    elif browser == "edge":
        edge_agents = [ua for ua in USER_AGENTS if "Edg" in ua]
        return random.choice(edge_agents)
    elif browser == "opera":
        opera_agents = [ua for ua in USER_AGENTS if "OPR" in ua]
        return random.choice(opera_agents)
    else:
        return get_random_user_agent() 