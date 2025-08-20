"""
Pakaneo Billing Automation

This module handles the main automation workflow for downloading billing data
from the Pakaneo API. It includes CSRF token handling, concurrent downloads,
and comprehensive error handling.
"""
import sys
import aiohttp
import asyncio
import json
import os
import random
import logging
import time
import traceback
from datetime import datetime
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional


# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from logs.custom_logging import setup_logging 
from utils.helpers import get_auth_data, HEADERS_GET, generate_csv_filename, format_duration, save_report, create_date_folder
from input.base_input import MAX_CONCURRENT_REQUESTS, MAX_RETRIES, RETRY_DELAY

logger = setup_logging(logger_name="PakaneoBillingAutomation", console_level=logging.INFO)

# Random delay between requests for politeness
DELAY_RANGE = (0.2, 1.0)

class PakaneCsvDownloader:
    """Handles CSV file downloads from Pakaneo API."""
    
    def __init__(
        self,
        api_users_data: List[Dict[str, Any]],
        start_date: str,
        end_date: str,
        export_types: List[str] = None,
        user_report: Dict[str, Any] = None
    ):
        self.api_users_data = api_users_data
        self.start_date = start_date
        self.end_date = end_date
        self.export_types = export_types or ["storeproducts", "storedproducts", "packedproducts", "packedorders"]
        self.download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        self.user_report = user_report  # Reference to shared user report
        
        # Create URL to user mapping for tracking downloads
        self.url_to_user = {}
    
    def add_user_error(self, user_id: int, error_msg: str):
        """Add error message to specific user in report."""
        if self.user_report:
            user_key = str(user_id)
            if user_key in self.user_report["users"]:
                self.user_report["users"][user_key]["errors"].append(error_msg)
    
    def add_user_download(self, user_id: int, url: str, success: bool = True):
        """Track download for specific user."""
        if self.user_report:
            user_key = str(user_id)
            if user_key in self.user_report["users"]:
                if success:
                    self.user_report["users"][user_key]["downloads"].append(url)
                    self.user_report["summary"]["successful_downloads"] += 1
                else:
                    self.user_report["failed_downloads"].append({"user_id": user_id, "url": url})
                    self.user_report["summary"]["failed_downloads"] += 1

    
    
    def convert_cookies_format(self, cookies_data):
        """Convert Playwright cookies format to aiohttp format."""
        if not cookies_data:
            return {}
        
        cookies = {}
        if isinstance(cookies_data, list):
            for cookie in cookies_data:
                if isinstance(cookie, dict) and 'name' in cookie and 'value' in cookie:
                    cookies[cookie['name']] = cookie['value']
        else:
            cookies = cookies_data
        
        return cookies



    async def get_apiuser_articles_with_retry(
        self,
        user_data: Dict[str, Any],
        session: aiohttp.ClientSession,
    ) -> Dict[str, Any]:
        """
        Fetch articles for an API user with automatic retry.
        
        Args:
            user_data: Dictionary containing user API data
            session: aiohttp session for making requests
            
        Returns:
            Dictionary containing article data options
        """
        user_id = user_data.get("user_id")
        api_url = user_data.get("api_url")
        api_headers = user_data.get("api_headers")
        
        if not all([user_id, api_url, api_headers]):
            logger.error(f"Missing required user data for user {user_id}")
            return {}
            
        data = {
            "apiuser": user_id,
            'start': self.start_date,
            'end': self.end_date,
        }
        
        for attempt in range(MAX_RETRIES):
            logger.debug(f"Fetching articles for API user '{user_id}' ({self.start_date} to {self.end_date}) - Attempt {attempt + 1}/{MAX_RETRIES}")
            
            try:
                # Extract base URL from api_url for auth data lookup
                from urllib.parse import urlparse
                parsed = urlparse(api_url)
                base_url = f"{parsed.scheme}://{parsed.netloc}"
                
                # Get fresh auth data for each attempt
                cookies_data = get_auth_data(base_url, "cookies")
                
                if not cookies_data:
                    error_msg = f"Missing cookies for API user '{user_id}'"
                    logger.error(error_msg)
                    self.add_user_error(user_id, error_msg)
                    return {}
                    
                if not api_headers:
                    error_msg = f"Missing API headers for API user '{user_id}'"
                    logger.error(error_msg)
                    self.add_user_error(user_id, error_msg)
                    return {}
                
                # Convert cookies to aiohttp format
                cookies = self.convert_cookies_format(cookies_data)
                
                async with session.post(api_url, cookies=cookies, headers=api_headers, data=data) as response:
                    content_type = response.headers.get("Content-Type", "")
                    status = response.status
                    
                    logger.debug(f"API response for user '{user_id}': status={status}, content-type={content_type}")
        
                    # Handle other non-200 status codes
                    if status != 200:
                        logger.warning(f"Unexpected status code {status} for API user '{user_id}' - Attempt {attempt + 1}/{MAX_RETRIES}")
                        continue
                    
                    # Process successful JSON response
                    if "application/json" in content_type:
                        result = await response.json()
                        logger.debug(f"Received JSON with {len(result)} keys for API user '{user_id}'")
                        
                        # Filter for relevant data types based on user selection
                        selected_options = {}
                        
                        for key, value in result.items():
                            if any(export_type in key.lower() for export_type in self.export_types):
                                selected_options[key] = value
                        
                        logger.info(f"Found {len(selected_options)} relevant data options for API user '{user_id}'")
                        return selected_options
                    
                    # Handle unexpected content types
                    else:
                        response_text = await response.text()
                        logger.warning(f"Unexpected content type {content_type} for API user '{user_id}'")
                        logger.debug(f"Response content: {response_text[:500]}...")
                        return {}
                    
            except aiohttp.ClientError as e:
                error_msg = f"Network error for API user '{user_id}': {e}"
                logger.error(error_msg)
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Retrying request for user '{user_id}' (attempt {attempt + 1}/{MAX_RETRIES})")
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                self.add_user_error(user_id, error_msg)
                
            except Exception as e:
                error_msg = f"Error while getting API user articles for '{user_id}': {e}"
                logger.error(error_msg)
                logger.debug(traceback.format_exc())
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Retrying request for user '{user_id}' (attempt {attempt + 1}/{MAX_RETRIES})")
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                self.add_user_error(user_id, error_msg)
        
        # Final failure message after all retries exhausted
        final_error = f"Failed to fetch articles after {MAX_RETRIES} attempts"
        logger.error(f"❌ {final_error} for user '{user_id}'")
        self.add_user_error(user_id, final_error)
        return {}


    async def download_csv_file(self, session: aiohttp.ClientSession, url: str, save_dir: str) -> bool:
        """
        Download a CSV file from the given URL.
        
        Args:
            session: aiohttp session for making requests
            url: URL to download from
            save_dir: Directory to save files to
            
        Returns:
            True if download successful, False otherwise
        """
        # Add random delay for politeness
        delay = random.uniform(*DELAY_RANGE)
        await asyncio.sleep(delay)
        
        # Generate filename and path
        filename = generate_csv_filename(url)
        save_path = os.path.join(save_dir, filename)
        
        logger.info(f"⏳ Downloading: {url}")
        
        for attempt in range(MAX_RETRIES):
            try:
                # Extract base URL for auth data lookup
                parsed = urlparse(url)
                base_url = f"{parsed.scheme}://{parsed.netloc}"
                
                # Get fresh cookies for download
                cookies_data = get_auth_data(base_url, "cookies")
                if not cookies_data:
                    error_msg = f"No cookies available for download from {base_url}"
                    logger.error(error_msg)
                    # Find user ID for this URL
                    user_id = self.url_to_user.get(url)
                    if user_id:
                        self.add_user_error(user_id, error_msg)
                        self.add_user_download(user_id, url, success=False)
                    return False
                
                # Convert cookies to aiohttp format
                cookies = self.convert_cookies_format(cookies_data)
                
                async with session.get(url, headers=HEADERS_GET, cookies=cookies) as response:
                    content_type = response.headers.get("Content-Type", "")
                    status = response.status
                    
                    logger.debug(f"Download response: status={status}, content-type={content_type}, url={url}")
                    
                    if status != 200:
                        error_msg = f"Unexpected status code {status} for {url}"
                        logger.warning(f"⚠️ {error_msg}")
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(RETRY_DELAY)
                            continue
                        user_id = self.url_to_user.get(url)
                        if user_id:
                            self.add_user_error(user_id, error_msg)
                            self.add_user_download(user_id, url, success=False)
                        return False
                    
                    # Check for expected content types
                    if "text/csv" in content_type or "application/octet-stream" in content_type or "text/plain" in content_type:
                        content = await response.read()
                        logger.debug(f"Downloaded {len(content)} bytes from {url}")
                        
                        try:
                            # Ensure output directory exists
                            os.makedirs(save_dir, exist_ok=True)
                            
                            # Save file
                            with open(save_path, "wb") as f:
                                f.write(content)
                            
                            file_size = len(content)
                            logger.info(f"✅ Saved: {save_path} ({file_size} bytes)")
                            # Find user ID for this URL and track success
                            user_id = self.url_to_user.get(url)
                            if user_id:
                                self.add_user_download(user_id, url, success=True)
                            return True
                            
                        except IOError as e:
                            error_msg = f"File I/O error saving '{save_path}': {e}"
                            logger.error(f"❌ {error_msg}")
                            user_id = self.url_to_user.get(url)
                            if user_id:
                                self.add_user_error(user_id, error_msg)
                                self.add_user_download(user_id, url, success=False)
                            return False
                            
                    else:
                        error_msg = f"Unexpected content type {content_type} from {url}"
                        logger.warning(f"⚠️ {error_msg}")
                        user_id = self.url_to_user.get(url)
                        if user_id:
                            self.add_user_error(user_id, error_msg)
                            self.add_user_download(user_id, url, success=False)
                        return False
                        
            except aiohttp.ClientError as e:
                error_msg = f"Network error downloading {url}: {e}"
                logger.error(f"❌ {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Retrying download for {url} (attempt {attempt + 1}/{MAX_RETRIES})")
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                user_id = self.url_to_user.get(url)
                if user_id:
                    self.add_user_error(user_id, error_msg)
                    self.add_user_download(user_id, url, success=False)
                
            except Exception as e:
                error_msg = f"Error downloading {url}: {e}"
                logger.error(f"❌ {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Retrying download for {url} (attempt {attempt + 1}/{MAX_RETRIES})")
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                user_id = self.url_to_user.get(url)
                if user_id:
                    self.add_user_error(user_id, error_msg)
                    self.add_user_download(user_id, url, success=False)
        
        # Final failure message after all retries exhausted
        final_error = f"Failed to download after {MAX_RETRIES} attempts"
        logger.error(f"❌ {final_error} for {url}")
        user_id = self.url_to_user.get(url)
        if user_id:
            self.add_user_error(user_id, final_error)
            self.add_user_download(user_id, url, success=False)
        return False


    async def download_with_semaphore(self, session: aiohttp.ClientSession, url: str, save_dir: str) -> bool:
        """
        Download a file with semaphore-controlled concurrency.
        
        Args:
            session: aiohttp session
            url: URL to download
            save_dir: Directory to save files to
            
        Returns:
            True if download successful, False otherwise
        """
        async with self.download_semaphore:
            logger.debug(f"Acquired semaphore for {url}")
            try:
                return await self.download_csv_file(session, url, save_dir)
            finally:
                logger.debug(f"Released semaphore for {url}")


    def extract_download_urls(self, base_url: str, options: Dict[str, Any], user_id: int) -> List[str]:
        """
        Extract download URLs from API response options and map them to user.
        
        Args:
            base_url: Base URL to prepend to relative paths
            options: Dictionary containing API response data
            user_id: User ID to associate with these URLs
            
        Returns:
            List of complete download URLs
        """
        urls = []
        
        for key, value in options.items():
            if isinstance(value, str):
                if value.startswith('/'):
                    # Relative URL - prepend base URL
                    full_url = f"{base_url.rstrip('/')}{value}"
                    urls.append(full_url)
                    # Map URL to user for tracking
                    self.url_to_user[full_url] = user_id
                elif value.startswith('http'):
                    # Already complete URL
                    urls.append(value)
                    # Map URL to user for tracking
                    self.url_to_user[value] = user_id
                else:
                    logger.warning(f"Unexpected URL format in options: '{value}'")
            else:
                logger.warning(f"Non-string value found in options: '{value}'")
        
        return urls


    async def download_all_data(self) -> bool:
        """
        Main function to download billing data for all API users.
        
        Returns:
            True if automation completed successfully, False otherwise
        """
        logger.info(f"Starting CSV download for {len(self.api_users_data)} API users")
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                # Phase 1: Collect all download URLs from all API users
                logger.info("Phase 1: Collecting download URLs from API users")
                all_urls = []
                
                for user_data in self.api_users_data:
                    user_id = user_data.get("user_id")
                    api_url = user_data.get("api_url")
                    
                    if not api_url:
                        error_msg = f"No API URL found for user {user_id}"
                        logger.warning(error_msg)
                        self.add_user_error(user_id, error_msg)
                        continue
                        
                    # Extract base URL for building download URLs
                    parsed = urlparse(api_url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    
                    options = await self.get_apiuser_articles_with_retry(user_data, session)
                    
                    if not options:
                        error_msg = f"No options found for user {user_id}"
                        logger.warning(error_msg)
                        self.add_user_error(user_id, error_msg)
                        continue
                    
                    # Extract URLs from options and map to user
                    user_urls = self.extract_download_urls(base_url, options, user_id)
                    logger.info(f"Found {len(user_urls)} download URLs for user {user_id}")
                    if user_urls:
                        all_urls.extend(user_urls)
                    else:
                        error_msg = f"No download URLs generated for user {user_id}"
                        self.add_user_error(user_id, error_msg)
                
                # Phase 2: Download all collected URLs with concurrency control
                if all_urls:
                    # Create date-based subfolder for downloads
                    date_folder = create_date_folder(self.start_date, self.end_date)
                    
                    # Update summary with total downloads
                    if self.user_report:
                        self.user_report["summary"]["total_downloads"] = len(all_urls)
                    
                    logger.info(f"Phase 2: Starting download of {len(all_urls)} files with max {MAX_CONCURRENT_REQUESTS} concurrent connections")
                    logger.info(f"Files will be saved to: {date_folder}")
                    
                    # Create download tasks
                    download_tasks = [
                        self.download_with_semaphore(session, url, date_folder) 
                        for url in all_urls
                    ]
                    
                    # Execute downloads
                    results = await asyncio.gather(*download_tasks, return_exceptions=True)
                    
                    # Count successful downloads
                    successful_downloads = sum(1 for result in results if result is True)
                    failed_downloads = len(results) - successful_downloads
                    
                    logger.info(f"Download summary: {successful_downloads} successful, {failed_downloads} failed")
                    
                    elapsed = time.time() - start_time
                    logger.info(f"CSV download completed in {format_duration(elapsed)}")
                    
                    return successful_downloads > 0
                    
                else:
                    logger.warning("No download URLs found for any API users")
                    return False
            
        except Exception as e:
            error_msg = f"Error in CSV download: {e}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            return False



if __name__ == "__main__":
    pass