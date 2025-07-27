"""
Pakaneo Billing Automation Bot

This module handles browser automation for logging into Pakaneo and extracting
authentication data (cookies and API headers) for use in API requests.
"""

import logging
import asyncio
import traceback
from typing import Optional, Dict, Any

from playwright.async_api import async_playwright, Page, BrowserContext
from playwright_stealth import stealth_async

from logs.custom_logging import setup_logging 
from input.base_input import EMAIL, PASSWORD
from utils.helpers import save_auth_data, validate_auth_data

logger = setup_logging(logger_name="PakaneoBillingBot", log_file="bot.log", console_level=logging.INFO)


async def is_logged_in(page: Page) -> bool:
    """
    Check if user is already logged in by examining page elements.
    
    Uses dual verification:
    1. Login button should NOT be visible
    2. Logout link SHOULD be visible
    
    Args:
        page: Playwright page object
        
    Returns:
        True if logged in, False otherwise
    """
    try:
        # Check if login button is NOT visible
        login_button = page.locator("text=Login using email & password")
        login_visible = await login_button.is_visible(timeout=3000)
        
        if not login_visible:
            # Double check by looking for logout link
            logout_link = page.locator("xpath=.//a[contains(@href, 'logout')]")
            logout_visible = await logout_link.is_visible(timeout=3000)
            return logout_visible
        
        return False  # Login button visible = not logged in
        
    except Exception as e:
        logger.warning(f"Error checking login status: {e}")
        logger.debug(traceback.format_exc())
        return False  # Default to not logged in for safety


async def capture_api_headers(page: Page, url: str) -> Optional[Dict[str, str]]:
    """
    Capture API request headers by triggering a test API call.
    
    Navigates to the billing page, fills in test dates, and captures
    the headers from the API request to get_apiuser_articles endpoint.
    
    Args:
        page: Playwright page object
        url: Base URL to navigate to
        
    Returns:
        Dictionary of request headers if successful, None otherwise
    """
    try:
        # Navigate to billing page if not already there
        if page.url != url:
            logger.debug(f"Navigating to {url}")
            await page.goto(url, timeout=120000)
        
        # Fill in test dates for API call
        await page.fill("#apiuserArticleStartDate", "2025-07-01")
        await page.fill("#apiuserArticleEndDate", "2025-07-15")

        # Capture the API request headers
        async with page.expect_request("**/get_apiuser_articles") as request_info:
            # Trigger the API call by clicking the send button
            send_button = page.locator("button[id='apiuserArticleSend']").and_(page.locator(":visible"))
            await send_button.click()

        # Extract headers from captured request
        captured_request = await request_info.value
        request_headers = dict(captured_request.headers) if captured_request else None
        
        if request_headers:
            logger.info("Successfully captured API request headers")
            return request_headers
        else:
            logger.warning("No request headers found for 'get_apiuser_articles'")
            return None
        
    except Exception as e:
        logger.error(f"Error capturing API headers: {e}")
        logger.debug(traceback.format_exc())
        return None


async def perform_login(page: Page) -> bool:
    """
    Perform login process using email and password.
    
    Args:
        page: Playwright page object
        
    Returns:
        True if login successful, False otherwise
    """
    try:
        logger.info("Starting login process")
        
        # Click login method selector
        await page.get_by_text("Login using email & password").click()
        
        # Fill credentials
        await page.fill('input[name="email"]', EMAIL)
        await page.fill('input[name="password"]', PASSWORD)
        
        # Submit login form
        await page.get_by_text("Log in").click()
        
        # Wait for page to load after login
        await page.wait_for_load_state("networkidle")
        
        logger.info("Login process completed")
        return True
        
    except Exception as e:
        logger.error(f"Login process failed: {e}")
        logger.debug(traceback.format_exc())
        return False


async def extract_auth_data(browser_context: BrowserContext, page: Page, url: str) -> bool:
    """
    Extract and save authentication data (cookies and API headers).
    
    Args:
        browser_context: Playwright browser context
        page: Playwright page object
        url: Base URL for the site
        
    Returns:
        True if all auth data extracted successfully, False otherwise
    """
    try:
        # Extract cookies
        cookies = await browser_context.cookies()
        if not cookies:
            logger.warning("No cookies found")
            return False
        
        logger.info(f"Retrieved {len(cookies)} cookies")
        
        # Save cookies
        if not save_auth_data(url, "cookies", cookies):
            logger.error("Failed to save cookies")
            return False
        
        # Extract API headers
        api_headers = await capture_api_headers(page, url)
        if not api_headers:
            logger.warning("Failed to capture API headers")
            return False
        
        # Save API headers
        if not save_auth_data(url, "api_headers", api_headers):
            logger.error("Failed to save API headers")
            return False
        
        logger.info("Successfully extracted and saved all authentication data")
        return True
        
    except Exception as e:
        logger.error(f"Error extracting auth data: {e}")
        logger.debug(traceback.format_exc())
        return False


async def pakaneo_billing_automation_bot(url: str) -> bool:
    """
    Main bot function to handle Pakaneo authentication and data extraction.
    
    This function:
    1. Launches a persistent browser context
    2. Checks if already logged in
    3. Performs login if necessary
    4. Extracts cookies and API headers
    5. Saves authentication data for later use
    
    Args:
        url: The Pakaneo base URL to authenticate with
        
    Returns:
        True if successful, False otherwise
    """
    browser_context = None
    
    try:
        logger.info(f"Starting Pakaneo bot for {url}")
        
        async with async_playwright() as playwright:
            # Launch persistent browser context to maintain session
            browser_context = await playwright.chromium.launch_persistent_context(
                user_data_dir=r"custom_profile",
                headless=False,
                ignore_https_errors=True,  # Handle SSL certificate issues
            )
            
            # Create new page and apply stealth mode
            page = await browser_context.new_page()
            await stealth_async(page)
            
            logger.info(f"Navigating to {url}")
            await page.goto(url, timeout=120000)
            
            # Check if already logged in
            logged_in = await is_logged_in(page)
            
            if logged_in:
                logger.info("Already logged in, extracting auth data")
                return await extract_auth_data(browser_context, page, url)
            
            # Need to login first
            logger.info("Not logged in, performing login")
            login_success = await perform_login(page)
            
            if not login_success:
                logger.error("Login failed")
                return False
            
            # Verify login was successful
            if not await is_logged_in(page):
                logger.error("Login verification failed")
                return False
            
            # Extract authentication data
            return await extract_auth_data(browser_context, page, url)
            
    except Exception as e:
        logger.error(f"Error in Pakaneo bot: {e}")
        logger.debug(traceback.format_exc())
        return False
    
    finally:
        # Clean up browser context
        if browser_context:
            try:
                await browser_context.close()
                logger.debug("Browser context closed successfully")
            except Exception as e:
                logger.warning(f"Error closing browser context: {e}")


async def refresh_auth_data(url: str) -> bool:
    """
    Refresh authentication data by running the bot.
    
    This is a convenience function that can be called when
    authentication data needs to be refreshed (e.g., CSRF token expired).
    
    Args:
        url: The Pakaneo base URL
        
    Returns:
        True if refresh successful, False otherwise
    """
    logger.info("Refreshing authentication data")
    success = await pakaneo_billing_automation_bot(url)
    
    if success:
        logger.info("Authentication data refreshed successfully")
        # Validate the refreshed data
        return validate_auth_data(url, ['cookies', 'api_headers'])
    else:
        logger.error("Failed to refresh authentication data")
        return False


# Main execution for testing
if __name__ == "__main__":
    from input.base_input import BASE_URL
    
    async def main():
        success = await pakaneo_billing_automation_bot(BASE_URL)
        if success:
            print("✅ Bot completed successfully")
        else:
            print("❌ Bot failed")
    
    asyncio.run(main())