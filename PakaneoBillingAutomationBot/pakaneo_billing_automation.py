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
from typing import List, Dict, Any, Optional

from logs.custom_logging import setup_logging 
from utils.helpers import get_auth_data, HEADERS_GET, generate_csv_filename, format_duration, validate_auth_data
from input.base_input import BASE_URL, MAX_CONCURRENT_REQUESTS, START_DATE, END_DATE, API_USERS_ID

logger = setup_logging(logger_name="PakaneoBillingAutomation", log_file="automation.log", console_level=logging.INFO)

# Random delay between requests for politeness
DELAY_RANGE = (0.2, 1.0)


def convert_cookies_format(cookies_data):
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


async def handle_csrf_error(base_url: str) -> bool:
    """
    Handle CSRF token expiration by regenerating authentication data.
    
    Args:
        base_url: The base URL to regenerate auth data for
        
    Returns:
        True if regeneration successful, False otherwise
    """
    logger.warning("CSRF token expired, regenerating authentication...")
    
    try:
        # Import here to avoid circular imports
        from PakaneoBillingAutomationBot.pakaneo_billing_automation_bot import refresh_auth_data
        
        success = await refresh_auth_data(base_url)
        if success:
            logger.info("Successfully regenerated authentication data")
            return True
        else:
            logger.error("Failed to regenerate authentication data")
            return False
            
    except Exception as e:
        logger.error(f"Error handling CSRF error: {e}")
        return False


async def get_apiuser_articles_with_retry(
    apiuser_id: int, 
    session: aiohttp.ClientSession, 
    start_date: str = START_DATE, 
    end_date: str = END_DATE, 
    max_retries: int = 2
) -> Dict[str, Any]:
    """
    Fetch articles for an API user with automatic CSRF token retry.
    
    Args:
        apiuser_id: The API user ID to fetch articles for
        session: aiohttp session for making requests
        start_date: Start date for the query (YYYY-MM-DD)
        end_date: End date for the query (YYYY-MM-DD)
        max_retries: Maximum number of retries for CSRF errors
        
    Returns:
        Dictionary containing article data options
    """
    url = f"{BASE_URL}/get_apiuser_articles"
    data = {
        "apiuser": apiuser_id,
        'start': start_date,
        'end': end_date,
    }
    
    for attempt in range(max_retries + 1):
        logger.debug(f"Fetching articles for API user {apiuser_id} ({start_date} to {end_date}) - Attempt {attempt + 1}")
        
        try:
            # Get fresh auth data for each attempt
            cookies_data = get_auth_data(BASE_URL, "cookies")
            post_headers = get_auth_data(BASE_URL, "api_headers")
            
            if not cookies_data or not post_headers:
                logger.error(f"Missing authentication data for API user {apiuser_id}")
                return {}
            
            # Convert cookies to aiohttp format
            cookies = convert_cookies_format(cookies_data)
            
            async with session.post(url, cookies=cookies, headers=post_headers, data=data) as response:
                content_type = response.headers.get("Content-Type", "")
                status = response.status
                
                logger.debug(f"API response for user {apiuser_id}: status={status}, content-type={content_type}")
                
                # Handle CSRF token error
                if status == 419:
                    response_text = await response.text()
                    logger.debug(f"API response for user {apiuser_id}: {response_text}")
                    
                    if "CSRF token mismatch" in response_text and attempt < max_retries:
                        logger.warning(f"CSRF token mismatch for user {apiuser_id}, attempting to regenerate...")
                        
                        # Regenerate auth data
                        if await handle_csrf_error(BASE_URL):
                            logger.info(f"Retrying request for user {apiuser_id}")
                            await asyncio.sleep(1)  # Brief delay before retry
                            continue
                        else:
                            logger.error(f"Failed to regenerate auth data for user {apiuser_id}")
                            return {}
                    else:
                        logger.error(f"CSRF error persists for user {apiuser_id} after {max_retries} retries")
                        return {}
                
                # Handle other non-200 status codes
                if status != 200:
                    logger.warning(f"Unexpected status code {status} for API user {apiuser_id}")
                    return {}
                
                # Process successful JSON response
                if "application/json" in content_type:
                    result = await response.json()
                    logger.debug(f"Received JSON with {len(result)} keys for API user {apiuser_id}")
                    
                    # Filter for relevant data types
                    wanted_keys = ["storeproducts", "storedproducts", "packedproducts", "packedorders"]
                    selected_options = {}
                    
                    for key, value in result.items():
                        if any(wanted in key.lower() for wanted in wanted_keys):
                            selected_options[key] = value
                    
                    logger.info(f"Found {len(selected_options)} relevant data options for API user {apiuser_id}")
                    return selected_options
                
                # Handle unexpected content types
                else:
                    response_text = await response.text()
                    logger.warning(f"Unexpected content type {content_type} for API user {apiuser_id}")
                    logger.debug(f"Response content: {response_text[:500]}...")
                    return {}
                
        except aiohttp.ClientError as e:
            logger.error(f"Network error for API user {apiuser_id}: {e}")
            if attempt < max_retries:
                logger.info(f"Retrying request for user {apiuser_id}")
                await asyncio.sleep(1)
                continue
            return {}
            
        except Exception as e:
            logger.error(f"Error while getting API user articles for {apiuser_id}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            if attempt < max_retries:
                logger.info(f"Retrying request for user {apiuser_id}")
                await asyncio.sleep(1)
                continue
            return {}
    
    return {}


async def download_csv_file(session: aiohttp.ClientSession, url: str, save_dir: str = "billing_exports") -> bool:
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
    
    # Ensure URL is absolute
    if not url.startswith(BASE_URL) and not url.startswith("http"):
        url = BASE_URL + url
    
    logger.info(f"⏳ Downloading: {url}")
    
    try:
        # Get fresh cookies for download
        cookies_data = get_auth_data(BASE_URL, "cookies")
        if not cookies_data:
            logger.error("No cookies available for download")
            return False
        
        # Convert cookies to aiohttp format
        cookies = convert_cookies_format(cookies_data)
        
        async with session.get(url, headers=HEADERS_GET, cookies=cookies) as response:
            content_type = response.headers.get("Content-Type", "")
            status = response.status
            
            logger.debug(f"Download response: status={status}, content-type={content_type}, url={url}")
            
            if status != 200:
                logger.warning(f"⚠️ Unexpected status code {status} for {url}")
                return False
            
            # Check for expected content types
            if "text/csv" in content_type or "application/octet-stream" in content_type:
                content = await response.read()
                logger.debug(f"Downloaded {len(content)} bytes from {url}")
                
                try:
                    # Ensure output directory exists
                    os.makedirs(save_dir, exist_ok=True)
                    
                    # Save file
                    with open(save_path, "wb") as f:
                        f.write(content)
                    
                    logger.info(f"✅ Saved: {save_path}")
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


# Semaphore for controlling concurrent downloads
download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)


async def download_with_semaphore(session: aiohttp.ClientSession, url: str) -> bool:
    """
    Download a file with semaphore-controlled concurrency.
    
    Args:
        session: aiohttp session
        url: URL to download
        
    Returns:
        True if download successful, False otherwise
    """
    async with download_semaphore:
        logger.debug(f"Acquired semaphore for {url}")
        try:
            return await download_csv_file(session, url)
        finally:
            logger.debug(f"Released semaphore for {url}")


def extract_download_urls(options: Dict[str, Any]) -> List[str]:
    """
    Extract download URLs from API response options.
    
    Args:
        options: Dictionary containing API response data
        
    Returns:
        List of download URLs
    """
    urls = []
    
    for key, value in options.items():
        if isinstance(value, str) and (value.startswith('http') or value.startswith('/')):
            urls.append(value)
        elif isinstance(value, dict) and 'url' in value and isinstance(value['url'], str):
            urls.append(value['url'])
    
    return urls


async def pakaneo_billing_automation(
    apiuser_ids: List[int], 
    start_date: str = START_DATE, 
    end_date: str = END_DATE
) -> bool:
    """
    Main automation function to download billing data for multiple API users.
    
    Args:
        apiuser_ids: List of API user IDs to process
        start_date: Start date for the query (YYYY-MM-DD)
        end_date: End date for the query (YYYY-MM-DD)
        
    Returns:
        True if automation completed successfully, False otherwise
    """
    logger.info(f"Starting Pakaneo billing automation for {len(apiuser_ids)} API users")
    logger.info(f"Date range: {start_date} to {end_date}")
    
    # Validate authentication data before starting
    if not validate_auth_data(BASE_URL, ['cookies', 'api_headers']):
        logger.error("Authentication data validation failed. Please run the bot first.")
        return False
    
    start_time = time.time()
    
    try:
        async with aiohttp.ClientSession() as session:
            # Phase 1: Collect all download URLs from all API users
            logger.info("Phase 1: Collecting download URLs from API users")
            all_urls = []
            
            for apiuser_id in apiuser_ids:
                logger.info(f"Processing API user ID: {apiuser_id}")
                
                options = await get_apiuser_articles_with_retry(
                    apiuser_id, session, start_date, end_date
                )
                
                if not options or not isinstance(options, dict):
                    logger.warning(f"No valid options found for API user {apiuser_id}")
                    continue
                
                # Extract URLs from options
                user_urls = extract_download_urls(options)
                logger.info(f"Found {len(user_urls)} download URLs for API user {apiuser_id}")
                all_urls.extend(user_urls)
            
            # Phase 2: Download all collected URLs with concurrency control
            if all_urls:
                logger.info(f"Phase 2: Starting download of {len(all_urls)} files with max {MAX_CONCURRENT_REQUESTS} concurrent connections")
                
                # Create download tasks
                download_tasks = [
                    download_with_semaphore(session, url) 
                    for url in all_urls
                ]
                
                # Execute downloads with progress tracking
                results = await asyncio.gather(*download_tasks, return_exceptions=True)
                
                # Count successful downloads
                successful_downloads = sum(1 for result in results if result is True)
                failed_downloads = len(results) - successful_downloads
                
                logger.info(f"Download summary: {successful_downloads} successful, {failed_downloads} failed")
                
            else:
                logger.warning("No download URLs found for any API users")
                return False
        
        elapsed = time.time() - start_time
        logger.info(f"Pakaneo billing automation completed in {format_duration(elapsed)}")
        return True
        
    except Exception as e:
        logger.error(f"Error in billing automation: {e}")
        return False


async def main():
    """Main entry point for the automation."""
    try:
        logger.info("=== Pakaneo Billing Automation Started ===")
        
        success = await pakaneo_billing_automation(API_USERS_ID, START_DATE, END_DATE)
        
        if success:
            logger.info("✅ Automation completed successfully")
        else:
            logger.error("❌ Automation failed")
            
    except KeyboardInterrupt:
        logger.info("Automation interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
    finally:
        logger.info("=== Pakaneo Billing Automation Finished ===")


if __name__ == "__main__":
    asyncio.run(main())