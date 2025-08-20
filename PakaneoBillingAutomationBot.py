"""
Pakaneo Billing Automation Bot

This module handles browser automation for logging into Pakaneo and extracting
authentication data (cookies and API headers) for use in API requests.
"""

import os
import logging
import asyncio
import traceback
import random
from typing import Optional, List, Dict, Any

from playwright.async_api import async_playwright, Page, BrowserContext
from playwright_stealth import stealth_async
from dotenv import load_dotenv

from logs.custom_logging import setup_logging 
from input.base_input import EMAIL, PASSWORD, MAX_BROWSER_SESSIONS, BASE_URLS, PAGE_LOAD_TIMEOUT, LOGIN_TIMEOUT, API_REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY
from utils.pakaneo_csv_downloader import PakaneCsvDownloader
from utils.helpers import save_auth_data, validate_auth_data, get_auth_data, save_report
from datetime import datetime

logger = setup_logging(logger_name="PakaneoBillingBot", console_level=logging.INFO)

# Load environment variables from .env file
load_dotenv()


class PakaneoBillingAutomationBot:
    def __init__(
        self,
        api_user_ids: List[int],
        start_date: str,
        end_date: str,
        base_urls: List[str] = BASE_URLS,
        export_types: List[str] = None
    ):
        self.api_user_ids = api_user_ids
        self.start_date = start_date
        self.end_date = end_date
        self.base_urls = base_urls
        self.export_types = export_types
        self.semaphore_limit = asyncio.Semaphore(MAX_BROWSER_SESSIONS)
        
        # Initialize user-centric report
        self.user_report = {
            "summary": {
                "total_users": len(api_user_ids),
                "successful_users": 0,
                "failed_users": 0,
                "total_downloads": 0,
                "successful_downloads": 0,
                "failed_downloads": 0,
                "start_time": None,
                "end_time": None,
                "date_range": f"{start_date} to {end_date}"
            },
            "users": {str(user_id): {"status": "pending", "downloads": [], "errors": []} for user_id in api_user_ids},
            "failed_downloads": []
        }
    
    def add_user_error(self, user_id: int, error_msg: str):
        """Add error message to specific user."""
        user_key = str(user_id)
        if user_key in self.user_report["users"]:
            self.user_report["users"][user_key]["errors"].append(error_msg)
            logger.debug(f"Added error for user {user_id}: {error_msg}")
        

    async def is_logged_in(self, page: Page) -> bool:
        """
        Check if user is already logged in by examining page elements.
        
        Args:
            page: Playwright page object
            
        Returns:
            True if logged in, False otherwise
        """
        try:
            # Wait for page to load
            await page.wait_for_load_state("networkidle", timeout=PAGE_LOAD_TIMEOUT)
            
            # Check if login button is NOT visible
            login_button = page.locator("text=Login using email & password")
            login_visible = await login_button.is_visible(timeout=60000)
            
            logger.debug(f"Login button visible: {login_visible} on {page.url}")
            
            if not login_visible:
                # Double check by looking for logout link
                logout_link = page.locator("xpath=.//a[contains(@href, 'logout')]")
                logout_visible = await logout_link.is_visible(timeout=60000)
                logger.debug(f"Logout link visible: {logout_visible} on {page.url}")
                return logout_visible
            
            return False  # Login button visible = not logged in
            
        except Exception as e:
            logger.debug(f"Error checking login status on {page.url}: {e}")
            return False  # Default to not logged in for safety

    async def is_user_data_visible(self, page: Page) -> bool:
        """Check if user data form is visible on the page."""
        try:
            # Wait for page to load
            await page.wait_for_load_state("networkidle", timeout=PAGE_LOAD_TIMEOUT)
            
            # Check if user data form is present
            date_field = page.locator("#apiuserArticleStartDate").first
            date_visible = await date_field.is_visible(timeout=5000)
            
            logger.debug(f"Date field visible: {date_visible} on {page.url}")
            
            if date_visible:
                return True
            
            # Check for specific error messages
            error_500 = page.locator('xpath=//h1[contains(text(), "tabler::error.500-title")]')
            error_500_visible = await error_500.is_visible(timeout=60000)
            
            if error_500_visible:
                logger.warning(f"Error 500: User data not found with '{page.url}'")
                return False
            
            # Check for access denied or other errors
            page_title = await page.title()
            logger.debug(f"Page title: '{page_title}' for {page.url}")
            
            if "error" in page_title.lower() or "denied" in page_title.lower():
                logger.warning(f"Access error detected: '{page_title}' for {page.url}")
                return False
            
            logger.warning(f"User data form not found on {page.url}")
            return False
                
        except Exception as e:
            logger.error(f"Error checking user data visibility on {page.url}: {e}")
            logger.debug(traceback.format_exc())  
            return False 
            
            
    async def capture_api_headers(self, page: Page, url: str) -> Optional[Dict[str, Any]]:
        """
        Capture API request headers by triggering a test API call.
        
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
                await page.goto(url, timeout=PAGE_LOAD_TIMEOUT)
            
            if not await self.is_user_data_visible(page):
                return None
            
            # Fill in test dates for API call
            await page.fill("#apiuserArticleStartDate", self.start_date)
            await page.fill("#apiuserArticleEndDate", self.end_date)

            # Capture the API request headers
            async with page.expect_request("**/get_apiuser_articles") as request_info:
                # Trigger the API call by clicking the send button
                send_button = page.locator("button[id='apiuserArticleSend']").and_(page.locator(":visible"))
                await send_button.click()

            # Extract headers from captured request
            captured_request = await request_info.value
            api_headers = dict(captured_request.headers) if captured_request else None
            api_url = captured_request.url if captured_request else None
            
            if api_headers:
                logger.info("Successfully captured API request headers")
                return {
                    "api_url": api_url,
                    "api_headers": api_headers
                }
            else:
                logger.warning("No request headers found for 'get_apiuser_articles'")
                return None
            
        except Exception as e:
            logger.error(f"Error capturing API headers: {e}")
            logger.debug(traceback.format_exc())
            return None


    async def perform_login(self, page: Page) -> bool:
        """
        Perform login process using email and password.
        
        Args:
            page: Playwright page object
            
        Returns:
            True if login successful, False otherwise
        """
        try:
            logger.info("Starting login process")
            
            # Wait for page to load first
            await page.wait_for_load_state("networkidle", timeout=PAGE_LOAD_TIMEOUT)
            
            # Check if login form is available
            login_button = page.locator("text=Login using email & password")
            if not await login_button.is_visible(timeout=60000):
                logger.warning("Login form not found on page")
                return False
            
            # Click login method selector
            await login_button.click(timeout=LOGIN_TIMEOUT)
            
            # Fill credentials
            await page.fill('input[name="email"]', EMAIL, timeout=LOGIN_TIMEOUT)
            await page.fill('input[name="password"]', PASSWORD, timeout=LOGIN_TIMEOUT)
            
            # Check and click checkbox if present
            checkbox = page.locator('input[type="checkbox"]')
            if await checkbox.is_visible(timeout=60000):
                await checkbox.click(timeout=LOGIN_TIMEOUT)
            
            # Submit login form
            await page.get_by_text("Log in").click(timeout=LOGIN_TIMEOUT)
            
            # Wait for page to load after login
            await page.wait_for_load_state("networkidle", timeout=PAGE_LOAD_TIMEOUT)
            
            logger.info("Login process completed")
            return True
            
        except Exception as e:
            logger.error(f"Login process failed: {e}")
            logger.debug(traceback.format_exc())
            return False


    async def extract_user_data(self, browser_context: BrowserContext, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Extract authentication data for a specific user with retry logic.
        
        Args:
            browser_context: Playwright browser context
            user_id: API user ID to extract data for
            
        Returns:
            Dictionary containing user data if successful, None otherwise
        """
        await asyncio.sleep(random.uniform(0.2, 1))
        
        for attempt in range(MAX_RETRIES):
            try:
                for url in self.base_urls:
                    full_url = f"{url}/settings/apiusers/{user_id}"
                    
                    # Load existing cookies if available
                    cookies = get_auth_data(url, "cookies")
                    if cookies:
                        await browser_context.add_cookies(cookies)
                    
                    page = await browser_context.new_page()
                    await stealth_async(page)
                
                    logger.debug(f"Navigating to '{full_url}' (attempt {attempt + 1}/{MAX_RETRIES})")
                    await page.goto(full_url, timeout=PAGE_LOAD_TIMEOUT)
                    await page.wait_for_load_state("networkidle", timeout=PAGE_LOAD_TIMEOUT)
                
                    # Check if already logged in
                    if await self.is_logged_in(page):
                        user_data = await self.capture_api_headers(page, full_url)
                        if user_data:
                            user_data["user_id"] = user_id
                            cookies = await browser_context.cookies()
                            # Save auth data for this URL
                            save_auth_data(url, "api_headers", user_data["api_headers"])
                            save_auth_data(url, "api_url", user_data["api_url"])
                            save_auth_data(url, "cookies", cookies)
                            await page.close()
                            return user_data
                        
                    # Need to login first
                    logger.info(f"Performing login for user {user_id}")
                    if not await self.perform_login(page):
                        logger.error(f"Login failed for user {user_id}")
                        await page.close()
                        continue
                    
                    # Verify login was successful
                    if not await self.is_logged_in(page):
                        logger.error(f"Login verification failed for user {user_id}")
                        await page.close()
                        continue
                    
                    # Save cookies for future use
                    cookies = await browser_context.cookies()
                    save_auth_data(url, "cookies", cookies)
                    
                    # Extract API data
                    user_data = await self.capture_api_headers(page, full_url)
                    await page.close()
                    
                    if user_data:
                        user_data["user_id"] = user_id
                        # Save auth data for this URL
                        save_auth_data(url, "api_headers", user_data["api_headers"])
                        save_auth_data(url, "api_url", user_data["api_url"])
                        logger.info(f"Successfully extracted auth data for user {user_id}")
                        return user_data
                
                # If we reach here, all URLs failed for this attempt
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"All URLs failed for user {user_id}, retrying in {RETRY_DELAY}s (attempt {attempt + 1}/{MAX_RETRIES})")
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                    
            except Exception as e:
                error_msg = f"Error extracting auth data (attempt {attempt + 1}/{MAX_RETRIES}): {str(e)}"
                logger.error(f"{error_msg} for user {user_id}")
                logger.debug(traceback.format_exc())
                self.add_user_error(user_id, error_msg)
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Retrying user {user_id} in {RETRY_DELAY}s")
                    await asyncio.sleep(RETRY_DELAY)
                    continue
        
        # Final failure message after all retries exhausted
        final_error = f"Failed to extract data after {MAX_RETRIES} attempts"
        logger.error(f"❌ {final_error} for user {user_id}")
        self.add_user_error(user_id, final_error)
        return None

    async def extract_user_data_with_semaphore(self, browser_context: BrowserContext, user_id: int):
        """Extract user data with semaphore control."""
        async with self.semaphore_limit:
            return await self.extract_user_data(browser_context, user_id)
       
    async def extract_all_users_data(self, browser_context: BrowserContext) -> List[Dict[str, Any]]:
        """Extract data for all users concurrently."""
        tasks = [
            self.extract_user_data_with_semaphore(browser_context, user_id) 
            for user_id in self.api_user_ids
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and update user report
        valid_results = []
        for i, result in enumerate(results):
            user_id = self.api_user_ids[i]
            user_key = str(user_id)
            
            if isinstance(result, Exception):
                error_msg = f"Unexpected error during processing: {str(result)}"
                logger.error(f"Error processing user {user_id}: {result}")
                self.add_user_error(user_id, error_msg)
                self.user_report["users"][user_key]["status"] = "failed"
            elif result is not None:
                valid_results.append(result)
                self.user_report["users"][user_key]["status"] = "success"
                logger.info(f"Successfully extracted auth data for user {user_id}")
            else:
                self.user_report["users"][user_key]["status"] = "failed"
                if not self.user_report["users"][user_key]["errors"]:
                    self.add_user_error(user_id, "No data extracted - unknown error")
                
        return valid_results

    async def run(self) -> bool:
        """
        Main bot function to handle Pakaneo authentication and data extraction.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Starting Pakaneo bot for {len(self.api_user_ids)} users")
            self.user_report["summary"]["start_time"] = datetime.now().isoformat()
            
            async with async_playwright() as playwright:
                # Launch persistent browser context to maintain session
                browser_context = await playwright.chromium.launch_persistent_context(
                    user_data_dir="custom_profile",
                    headless=False,
                    ignore_https_errors=True,
                )
                
                # Extract authentication data for all users
                user_data_list = await self.extract_all_users_data(browser_context)
                
                if not user_data_list:
                    logger.error("No user data extracted, cannot proceed")
                    return False
                
                logger.info(f"Successfully extracted data for {len(user_data_list)} users")
                
            # Initialize downloader and start downloads
            downloader = PakaneCsvDownloader(
                api_users_data=user_data_list,
                start_date=self.start_date,
                end_date=self.end_date,
                export_types=self.export_types,
                user_report=self.user_report  # Pass user report to downloader
            )
            
            success = await downloader.download_all_data()
            
            # Finalize report
            self.user_report["summary"]["end_time"] = datetime.now().isoformat()
            self.user_report["summary"]["successful_users"] = sum(1 for u in self.user_report["users"].values() if u["status"] == "success")
            self.user_report["summary"]["failed_users"] = sum(1 for u in self.user_report["users"].values() if u["status"] == "failed")
            
            # Save user-centric report
            await save_report(self.user_report, self.start_date, self.end_date)
            
            if success:
                logger.info("✅ Automation completed successfully")
            else:
                logger.error("❌ Automation failed")
                
            return success

        except Exception as e:
            logger.error(f"Error in Pakaneo bot: {e}")
            logger.debug(traceback.format_exc())
            
            # Save report even on critical failure
            self.user_report["summary"]["end_time"] = datetime.now().isoformat()
            try:
                await save_report(self.user_report, self.start_date, self.end_date)
            except:
                pass
            return False


if __name__ == "__main__":
    from input.base_input import API_USERS_IDS, START_DATE, END_DATE, BASE_URLS
    
    bot = PakaneoBillingAutomationBot(API_USERS_IDS, START_DATE, END_DATE, BASE_URLS)
    asyncio.run(bot.run())