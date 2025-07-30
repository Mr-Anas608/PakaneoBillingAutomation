import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Default configuration for testing - can be overridden via CLI
API_USERS_IDS = [
    205,
    206,
    207,
    211,
    215,
    216,
    221,
    222,
    223,
    224,
    225,
    226,
    229,
    228
]

START_DATE = '2025-07-01'
END_DATE = '2025-07-15'

# Concurrency settings - optimized for stability and performance
MAX_CONCURRENT_REQUESTS = 20  # Conservative for CSV downloads to avoid overwhelming server
MAX_BROWSER_SESSIONS = 10     # Limited browser sessions to reduce memory usage

# Request timing - polite delays to avoid rate limiting
DELAY_RANGE = (0.5, 2.0)      # Longer delays between requests for politeness

# Timeout settings (in milliseconds)
PAGE_LOAD_TIMEOUT = 60000     # 60 seconds for page loads
API_REQUEST_TIMEOUT = 30000    # 30 seconds for API requests
LOGIN_TIMEOUT = 45000          # 45 seconds for login operations

# Retry settings
MAX_RETRIES = 3                # Maximum retry attempts for failed operations
RETRY_DELAY = 2.0              # Delay between retries in seconds

# Authentication credentials
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

# Base URLs to try for authentication
BASE_URLS = [
    "https://millerbecker.pakaneo.com",
    "https://millerbecker2.pakaneo.com"
]
