import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

API_USERS_ID = [
    204,
    205,
    206,
    207,
]

START_DATE = '2025-07-01'
END_DATE = '2025-07-15'

BASE_URL = "https://millerbecker2.pakaneo.com" # OR https://millerbecker.pakaneo.com

MAX_CONCURRENT_REQUESTS = 20

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
