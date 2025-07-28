"""
Pakaneo Billing Automation

This module handles the main automation workflow for downloading billing data
from the Pakaneo API. It includes CSRF token handling, concurrent downloads,
and comprehensive error handling.
"""

import aiohttp
import asyncio
import json
import os
import random
import logging
import time
import traceback
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional

from logs.custom_logging import setup_logging 
from utils.helpers import get_auth_data, HEADERS_GET, generate_csv_filename, format_duration, validate_auth_data
from input.base_input import MAX_CONCURRENT_REQUESTS, MAX_RETRIES, RETRY_DELAY

logger = setup_logging(logger_name="PakaneoBillingAutomation", log_file="automation.log", console_level=logging.INFO)

# Random delay between requests for politeness
DELAY_RANGE = (0.2, 1.0)

class PakaneCsvDownloader:
    """Handles CSV file downloads from Pakaneo API."""
    
    def __init__(
        self,
        api_users_data: List[Dict[str, Any]],
        start_date: str,
        end_date: str
    ):
        self.api_users_data = api_users_data
        self.start_date = start_date
        self.end_date = end_date
        self.download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    
    
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
        max_retries: int = MAX_RETRIES,
    ) -> Dict[str, Any]:
        """
        Fetch articles for an API user with automatic retry.
        
        Args:
            user_data: Dictionary containing user API data
            session: aiohttp session for making requests
            max_retries: Maximum number of retries for errors
            
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
        
        for attempt in range(max_retries + 1):
            logger.debug(f"Fetching articles for API user '{user_id}' ({self.start_date} to {self.end_date}) - Attempt {attempt + 1}")
            
            try:
                # Extract base URL from api_url for auth data lookup
                from urllib.parse import urlparse
                parsed = urlparse(api_url)
                base_url = f"{parsed.scheme}://{parsed.netloc}"
                
                # Get fresh auth data for each attempt
                cookies_data = get_auth_data(base_url, "cookies")
                
                if not cookies_data:
                    logger.error(f"Missing cookies for API user '{user_id}'")
                    return {}
                    
                if not api_headers:
                    logger.error(f"Missing API headers for API user '{user_id}'")
                    return {}
                
                # Convert cookies to aiohttp format
                cookies = self.convert_cookies_format(cookies_data)
                
                async with session.post(api_url, cookies=cookies, headers=api_headers, data=data) as response:
                    content_type = response.headers.get("Content-Type", "")
                    status = response.status
                    
                    logger.debug(f"API response for user '{user_id}': status={status}, content-type={content_type}")
        
                    # Handle other non-200 status codes
                    if status != 200:
                        logger.warning(f"Unexpected status code {status} for API user '{user_id}' - Attempt {attempt + 1}")
                        continue
                    
                    # Process successful JSON response
                    if "application/json" in content_type:
                        result = await response.json()
                        logger.debug(f"Received JSON with {len(result)} keys for API user '{user_id}'")
                        
                        # Filter for relevant data types
                        wanted_keys = ["storeproducts", "storedproducts", "packedproducts", "packedorders"]
                        selected_options = {}
                        
                        for key, value in result.items():
                            if any(wanted in key.lower() for wanted in wanted_keys):
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
                logger.error(f"Network error for API user '{user_id}': {e}")
                if attempt < max_retries:
                    logger.info(f"Retrying request for user '{user_id}'")
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                return {}
                
            except Exception as e:
                logger.error(f"Error while getting API user articles for '{user_id}': {e}")
                import traceback
                logger.debug(traceback.format_exc())
                if attempt < max_retries:
                    logger.info(f"Retrying request for user '{user_id}'")
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                return {}
        return {}


    async def download_csv_file(self, session: aiohttp.ClientSession, url: str, save_dir: str = "billing_exports") -> bool:
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
        
        try:
            # Extract base URL for auth data lookup
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            # Get fresh cookies for download
            cookies_data = get_auth_data(base_url, "cookies")
            if not cookies_data:
                logger.error(f"No cookies available for download from {base_url}")
                return False
            
            # Convert cookies to aiohttp format
            cookies = self.convert_cookies_format(cookies_data)
            
            async with session.get(url, headers=HEADERS_GET, cookies=cookies) as response:
                content_type = response.headers.get("Content-Type", "")
                status = response.status
                
                logger.debug(f"Download response: status={status}, content-type={content_type}, url={url}")
                
                if status != 200:
                    logger.warning(f"⚠️ Unexpected status code {status} for {url}")
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
                        return True
                        
                    except IOError as e:
                        logger.error(f"❌ File I/O error saving '{save_path}': {e}")
                        return False
                        
                else:
                    logger.warning(f"⚠️ Unexpected content type {content_type} from {url}")
                    return False
                    
        except aiohttp.ClientError as e:
            logger.error(f"❌ Network error downloading {url}: {e}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error downloading {url}: {e}")
            return False


    async def download_with_semaphore(self, session: aiohttp.ClientSession, url: str) -> bool:
        """
        Download a file with semaphore-controlled concurrency.
        
        Args:
            session: aiohttp session
            url: URL to download
            
        Returns:
            True if download successful, False otherwise
        """
        async with self.download_semaphore:
            logger.debug(f"Acquired semaphore for {url}")
            try:
                return await self.download_csv_file(session, url)
            finally:
                logger.debug(f"Released semaphore for {url}")


    def extract_download_urls(self, base_url: str, options: Dict[str, Any]) -> List[str]:
        """
        Extract download URLs from API response options.
        
        Args:
            base_url: Base URL to prepend to relative paths
            options: Dictionary containing API response data
            
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
                elif value.startswith('http'):
                    # Already complete URL
                    urls.append(value)
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
                        logger.warning(f"No API URL found for user {user_id}")
                        continue
                        
                    # Extract base URL for building download URLs
                    parsed = urlparse(api_url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    
                    options = await self.get_apiuser_articles_with_retry(user_data, session)
                    
                    if not options:
                        logger.warning(f"No options found for user {user_id}")
                        continue
                    
                    # Extract URLs from options
                    user_urls = self.extract_download_urls(base_url, options)
                    logger.info(f"Found {len(user_urls)} download URLs for user {user_id}")
                    all_urls.extend(user_urls)
                
                # Phase 2: Download all collected URLs with concurrency control
                if all_urls:
                    logger.info(f"Phase 2: Starting download of {len(all_urls)} files with max {MAX_CONCURRENT_REQUESTS} concurrent connections")
                    
                    # Create download tasks
                    download_tasks = [
                        self.download_with_semaphore(session, url) 
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
            logger.error(f"Error in CSV download: {e}")
            logger.debug(traceback.format_exc())
            return False



if __name__ == "__main__":
    pass