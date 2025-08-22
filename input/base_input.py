import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Default configuration for testing - can be overridden via CLI
API_USERS_IDS = [
   145,
   2046,
]

START_DATE = '2025-07-16'
END_DATE = '2025-07-31'

# Concurrency settings - optimized for stability and performance
MAX_CONCURRENT_REQUESTS = 10  # Conservative for CSV downloads to avoid overwhelming server
MAX_BROWSER_SESSIONS = 10     # Limited browser sessions to reduce memory usage

# Request timing - polite delays to avoid rate limiting
DELAY_RANGE = (0.5, 2.0)      # Longer delays between requests for politeness

# Timeout settings (in milliseconds)
PAGE_LOAD_TIMEOUT = 120000     # 120 seconds for page loads
API_REQUEST_TIMEOUT = 60000    # 60 seconds for API requests
LOGIN_TIMEOUT = 90000          # 90 seconds for login operations

# Retry settings
MAX_RETRIES = 3               # Maximum retry attempts for failed operations
RETRY_DELAY = 2.0              # Delay between retries in seconds

# Authentication credentials
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

# Available accounts for selection
SELECTED_ACCOUNTS = ['millerbecker2', 'millerbecker']  # Default: both selected

# Account URL mapping
ACCOUNT_URLS = {
    'millerbecker2': 'https://millerbecker2.pakaneo.com',
    'millerbecker': 'https://millerbecker.pakaneo.com'
}
