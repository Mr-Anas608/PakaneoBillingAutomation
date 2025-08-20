"""
Utility functions for Pakaneo billing automation.

This module provides helper functions for authentication data management,
file operations, and HTTP request utilities.
"""

import os
import sys
import json
import logging
import re
import traceback
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Optional, Dict, Any, List

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from logs.custom_logging import setup_logging

logger = setup_logging(logger_name="PakaneoBillingHelpers", console_level=logging.INFO)

# Standard HTTP headers for GET requests
HEADERS_GET = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Pragma': 'no-cache',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}


def generate_csv_filename(url: str) -> str:
    """
    Generate a descriptive filename from a URL path.
    
    Args:
        url: The URL to generate filename from
        
    Returns:
        A descriptive CSV filename
        
    Examples:
        >>> generate_csv_filename("/stored_products_export/207/2025-07-01/2025-07-15")
        "stored_products_export_207 (2025-07-01 to 2025-07-15).csv"
    """
    try:
        path = urlparse(url).path.strip("/")
        parts = path.split("/")
        
        if len(parts) == 4:
            # Format: endpoint/user_id/start_date/end_date
            filename = f"{parts[0]}_{parts[1]} ({parts[2]} to {parts[3]})"
        elif len(parts) == 3:
            # Format: endpoint/user_id/date
            filename = f"{parts[0]}_{parts[1]} ({parts[2]})"
        else:
            # Fallback for unknown formats
            safe_name = re.sub(r"[^a-zA-Z0-9]", "_", path)
            timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            filename = f"{safe_name} ({timestamp})"
        
        return filename + ".csv"
    
    except Exception as e:
        logger.error(f"Error generating filename for {url}: {e}")
        # Fallback to timestamp-based filename
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"export_{timestamp}.csv"


def save_auth_data(url: str, data_key: str, data_value: Any, filename: str = "auth_details.json") -> bool:
    """
    Save authentication data to JSON file with domain as parent key.
    
    Args:
        url: The URL to extract domain from
        data_key: The key to store data under (e.g., 'cookies', 'headers')
        data_value: The data to store
        filename: The JSON file to save to
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Extract main domain URL only
        parsed = urlparse(url)
        main_domain_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Load existing data or create empty dict
        auth_data = {}
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    auth_data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error reading {filename}: {e}")
                auth_data = {}
        
        # Create URL key if doesn't exist
        if main_domain_url not in auth_data:
            auth_data[main_domain_url] = {}
        
        # Add/update the data
        auth_data[main_domain_url][data_key] = data_value
        
        # Save back to file
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(auth_data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"Successfully saved {data_key} for {main_domain_url}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving auth data: {e}")
        logger.debug(traceback.format_exc())
        return False


def get_auth_data(url: str, data_key: str, filename: str = "auth_details.json") -> Optional[Any]:
    """
    Retrieve authentication data from JSON file by URL and key.
    
    Args:
        url: The URL to extract domain from
        data_key: The key to retrieve data for
        filename: The JSON file to read from
        
    Returns:
        The stored data if found, None otherwise
    """
    try:
        # Extract main domain URL only
        parsed = urlparse(url)
        main_domain_url = f"{parsed.scheme}://{parsed.netloc}"
   
        # Check if file exists
        if not os.path.exists(filename):
            logger.warning(f"Auth file {filename} not found")
            return None
        
        # Load data
        with open(filename, "r", encoding="utf-8") as f:
            auth_data = json.load(f)
        
        # Check if URL exists
        if main_domain_url not in auth_data:
            logger.warning(f"No auth data found for {main_domain_url}")
            return None
        
        # Check if key exists
        if data_key not in auth_data[main_domain_url]:
            logger.warning(f"Key '{data_key}' not found for {main_domain_url}")
            return None
        
        logger.debug(f"Retrieved {data_key} for {main_domain_url}")
        return auth_data[main_domain_url][data_key]
        
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error reading {filename}: {e}")
        logger.debug(traceback.format_exc())
        return None
    except Exception as e:
        logger.error(f"Error getting auth data: {e}")
        logger.debug(traceback.format_exc())
        return None


def format_duration(seconds: float) -> str:
    """
    Format a duration in seconds to a human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
        
    Examples:
        >>> format_duration(45.5)
        "45.5s"
        >>> format_duration(125)
        "2m 5s"
        >>> format_duration(3665)
        "1h 1m 5s"
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{int(minutes)}m {int(seconds)}s"
    
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"


def validate_auth_data(url: str, required_keys: List[str] = None) -> bool:
    """
    Validate that required authentication data exists for a URL.
    
    Args:
        url: The URL to check auth data for
        required_keys: List of required keys (defaults to ['cookies'])
        
    Returns:
        True if all required data exists, False otherwise
    """
    if required_keys is None:
        required_keys = ['cookies']
    
    for key in required_keys:
        data = get_auth_data(url, key)
        if not data:
            logger.warning(f"Missing required auth data: {key} for {url}")
            return False
    
    logger.debug(f"Auth data validation passed for {url}")
    return True


def create_date_folder(start_date: str, end_date: str, base_dir: str = "billing_exports") -> str:
    """
    Create a date-based subfolder for organizing files.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        base_dir: Base directory for exports
        
    Returns:
        Path to the created date folder
    """
    folder_name = f"{start_date} to {end_date}"
    folder_path = os.path.join(base_dir, folder_name)
    
    try:
        os.makedirs(folder_path, exist_ok=True)
        logger.debug(f"Created/verified date folder: {folder_path}")
        return folder_path
    except Exception as e:
        logger.error(f"Error creating date folder {folder_path}: {e}")
        # Fallback to base directory
        os.makedirs(base_dir, exist_ok=True)
        return base_dir


async def save_report(report_data: Dict[str, Any], start_date: str, end_date: str) -> bool:
    """
    Save download report to JSON file in date-based subfolder.
    
    Args:
        report_data: Report data to save
        start_date: Start date for folder creation
        end_date: End date for folder creation
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create date-based subfolder
        date_folder = create_date_folder(start_date, end_date)
        
        report_filename = f"download_report_{start_date}_to_{end_date}.json"
        report_path = os.path.join(date_folder, report_filename)
        
        # Load existing report if exists
        existing_report = {"runs": []}
        if os.path.exists(report_path):
            try:
                with open(report_path, 'r', encoding='utf-8') as f:
                    existing_report = json.load(f)
                if "runs" not in existing_report:
                    existing_report["runs"] = []
            except (json.JSONDecodeError, IOError):
                existing_report = {"runs": []}
        
        # Append current run
        existing_report["runs"].append(report_data)
        
        # Save report
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(existing_report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📊 Report saved: {report_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving report: {e}")
        logger.debug(traceback.format_exc())
        return False