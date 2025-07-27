"""
Main entry point for Pakaneo Billing Automation

This script provides a simple interface for running the billing automation
with user-specified parameters.
"""

import asyncio
import argparse
import sys
from typing import List
import logging

from logs.custom_logging import setup_logging
from input.base_input import BASE_URL
from PakaneoBillingAutomationBot.pakaneo_billing_automation_bot import pakaneo_billing_automation_bot
from PakaneoBillingAutomationBot.pakaneo_billing_automation import pakaneo_billing_automation
from utils.helpers import validate_auth_data

logger = setup_logging(logger_name="PakaneoBillingMain", log_file="main.log", console_level=logging.INFO)


def parse_apiuser_ids(ids_str: str) -> List[int]:
    """Parse comma-separated API user IDs."""
    try:
        return [int(id.strip()) for id in ids_str.split(',')]
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Invalid API user IDs: {e}")


async def run_automation(apiuser_ids: List[int], start_date: str, end_date: str):
    """Run the complete automation workflow."""
    logger.info("=== Pakaneo Billing Automation Started ===")
    logger.info(f"API User IDs: {apiuser_ids}")
    logger.info(f"Date range: {start_date} to {end_date}")
    
    # Check if we have valid auth data
    if not validate_auth_data(BASE_URL, ['cookies', 'api_headers']):
        logger.info("No valid authentication data found. Running bot to generate auth data...")
        
        # Run bot to get auth data
        bot_success = await pakaneo_billing_automation_bot(BASE_URL)
        
        if not bot_success:
            logger.error("❌ Authentication failed, cannot proceed")
            return False
        
        logger.info("✅ Authentication completed")
    else:
        logger.info("Using existing authentication data")
    
    # Run the automation
    logger.info("Starting billing data download...")
    automation_success = await pakaneo_billing_automation(apiuser_ids, start_date, end_date)
    
    if automation_success:
        logger.info("✅ Automation completed successfully")
        return True
    else:
        logger.error("❌ Automation failed")
        return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Pakaneo Billing Automation - Download billing data for specified API users and date range",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --apiuser-ids 204,205,206 --start-date 2025-06-01 --end-date 2025-06-30
  python main.py --apiuser-ids 207 --start-date 2025-07-01 --end-date 2025-07-15
        """
    )
    
    # Required arguments
    parser.add_argument(
        '--apiuser-ids',
        type=parse_apiuser_ids,
        required=True,
        help='Comma-separated API user IDs (e.g., 204,205,206)'
    )
    parser.add_argument(
        '--start-date',
        required=True,
        help='Start date in YYYY-MM-DD format (e.g., 2025-06-01)'
    )
    parser.add_argument(
        '--end-date',
        required=True,
        help='End date in YYYY-MM-DD format (e.g., 2025-06-30)'
    )
    
    # Optional arguments
    parser.add_argument(
        '--base-url',
        default=BASE_URL,
        help=f'Base URL for Pakaneo (default: {BASE_URL})'
    )
    
    args = parser.parse_args()
    
    # Update global BASE_URL if provided
    if args.base_url != BASE_URL:
        import input.base_input
        input.base_input.BASE_URL = args.base_url
    
    async def run_main():
        """Run the main automation."""
        try:
            return await run_automation(args.apiuser_ids, args.start_date, args.end_date)
        except KeyboardInterrupt:
            logger.info("Operation interrupted by user")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False
    
    # Run the automation
    success = asyncio.run(run_main())
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()