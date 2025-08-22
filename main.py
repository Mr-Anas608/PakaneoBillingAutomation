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
from input.base_input import SELECTED_ACCOUNTS, ACCOUNT_URLS
from PakaneoBillingAutomationBot import PakaneoBillingAutomationBot

logger = setup_logging(logger_name="PakaneoBillingMain", console_level=logging.DEBUG)


def parse_apiuser_ids(ids_str: str) -> List[int]:
    """Parse comma-separated API user IDs."""
    try:
        return [int(id.strip()) for id in ids_str.split(',')]
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Invalid API user IDs: {e}")


async def run_automation(
    apiuser_ids: List[int], 
    start_date: str, 
    end_date: str, 
    selected_accounts: List[str] = None, 
    export_types: List[str] = None
    ):
    """Run the complete automation workflow."""
    if selected_accounts is None:
        selected_accounts = SELECTED_ACCOUNTS
    
    # Convert account keys to URLs
    account_urls = [ACCOUNT_URLS[key] for key in selected_accounts if key in ACCOUNT_URLS]
    
    logger.info("=== Pakaneo Billing Automation Started ===")
    logger.info(f"API User IDs: {apiuser_ids}")
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Selected accounts: {selected_accounts}")
    logger.info(f"Account URLs: {account_urls}")
    logger.info(f"Export types: {export_types or 'All (default)'}")
    logger.debug(f"Configuration loaded successfully")
    
    # Initialize and run the bot
    bot = PakaneoBillingAutomationBot(
        api_user_ids=apiuser_ids,
        start_date=start_date,
        end_date=end_date,
        account_urls=account_urls,
        export_types=export_types
    )
    
    success = await bot.run()
    
    if success:
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
        '--selected-accounts',
        nargs='+',
        default=SELECTED_ACCOUNTS,
        choices=list(ACCOUNT_URLS.keys()),
        help=f'Selected accounts (default: {SELECTED_ACCOUNTS})'
    )
    parser.add_argument(
        '--export-types',
        nargs='+',
        default=None,
        choices=['storeproducts', 'storedproducts', 'packedproducts', 'packedorders'],
        help='Export types to download (default: all types)'
    )
    
    args = parser.parse_args()
    
    async def run_main():
        """Run the main automation."""
        try:
            return await run_automation(args.apiuser_ids, args.start_date, args.end_date, args.selected_accounts, args.export_types)
        except KeyboardInterrupt:
            logger.info("Operation interrupted by user")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            logger.debug(f"Traceback: {e}", exc_info=True)
            return False
    
    # Run the automation
    success = asyncio.run(run_main())
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(run_automation(apiuser_ids=[207], start_date="08/01/2025", end_date="08/15/2025", selected_accounts=['millerbecker']))