"""
Date and time utility functions for CellMage.

This module provides functions for parsing and manipulating dates and times.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from dateutil.parser import parse as dateutil_parse
    from dateutil.relativedelta import relativedelta

    _DATEUTIL_AVAILABLE = True
except ImportError:
    _DATEUTIL_AVAILABLE = False


def parse_date_input(date_str: Optional[str]) -> Optional[str]:
    """Parse a date string in YYYY-MM-DD format or natural language.

    Args:
        date_str: A date string in YYYY-MM-DD format or natural language (e.g., "3 days ago")

    Returns:
        A date string in YYYY-MM-DD format or None if the input was None or couldn't be parsed
    """
    if not date_str:
        return None

    # Remove any surrounding quotes that might have been passed from command line
    date_str = date_str.strip("\"'")

    logger.info(f"Parsing date input: '{date_str}'")

    # If already in YYYY-MM-DD format, return as is
    if date_str and len(date_str) == 10 and date_str[4] == "-" and date_str[7] == "-":
        try:
            # Validate it's a proper date
            year = int(date_str[0:4])
            month = int(date_str[5:7])
            day = int(date_str[8:10])
            if 1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= 2100:
                logger.info(f"Date already in YYYY-MM-DD format: {date_str}")
                return date_str
        except ValueError:
            logger.info("Not a valid YYYY-MM-DD date, trying natural language parsing")

    # Try natural language parsing
    try:
        date_str_lower = date_str.lower().strip()
        now = datetime.now()
        logger.info(f"Current date for reference: {now.strftime('%Y-%m-%d')}")

        # Check if it's a simple "X unit(s)" or "X unit(s) ago" format
        parts = date_str_lower.split()
        logger.info(f"Split date parts: {parts}")

        if len(parts) >= 1:
            try:
                # Simple formats like "5 days ago" or "3 weeks"
                if len(parts) >= 2:
                    quantity = int(parts[0])
                    unit = parts[1]
                    logger.info(f"Detected quantity: {quantity}, unit: {unit}")

                    # Handle day/days
                    if unit.startswith("day"):
                        date = now - timedelta(days=quantity)
                        result = date.strftime("%Y-%m-%d")
                        logger.info(f"Parsed as {quantity} days ago: {result}")
                        return result

                    # Handle week/weeks
                    elif unit.startswith("week"):
                        date = now - timedelta(weeks=quantity)
                        result = date.strftime("%Y-%m-%d")
                        logger.info(f"Parsed as {quantity} weeks ago: {result}")
                        return result

                    # Handle month/months
                    elif unit.startswith("month"):
                        # We need to use relativedelta for months
                        if _DATEUTIL_AVAILABLE:
                            date = now - relativedelta(months=quantity)
                            result = date.strftime("%Y-%m-%d")
                            logger.info(f"Parsed as {quantity} months ago: {result}")
                            return result
                        else:
                            logger.warning("dateutil not available for month calculation")

                    # Handle year/years
                    elif unit.startswith("year"):
                        # We need to use relativedelta for years
                        if _DATEUTIL_AVAILABLE:
                            date = now - relativedelta(years=quantity)
                            result = date.strftime("%Y-%m-%d")
                            logger.info(f"Parsed as {quantity} years ago: {result}")
                            return result
                        else:
                            logger.warning("dateutil not available for year calculation")

                # Try simple words
                if len(parts) == 1:
                    if parts[0] == "today":
                        result = now.strftime("%Y-%m-%d")
                        logger.info(f"Parsed as today: {result}")
                        return result
                    elif parts[0] == "yesterday":
                        date = now - timedelta(days=1)
                        result = date.strftime("%Y-%m-%d")
                        logger.info(f"Parsed as yesterday: {result}")
                        return result
                    elif parts[0] == "tomorrow":
                        date = now + timedelta(days=1)
                        result = date.strftime("%Y-%m-%d")
                        logger.info(f"Parsed as tomorrow: {result}")
                        return result

            except (ValueError, IndexError) as e:
                logger.warning(f"Error in simple date parsing: {e}")
                # Continue with dateutil if the simple parsing fails

        # Use dateutil if available for more complex parsing
        if _DATEUTIL_AVAILABLE:
            try:
                logger.info(f"Attempting to parse with dateutil: {date_str}")
                parsed_date = dateutil_parse(date_str)
                result = parsed_date.strftime("%Y-%m-%d")
                logger.info(f"Successfully parsed with dateutil: {result}")
                return result
            except Exception as e:
                logger.warning(f"Could not parse date string with dateutil: {date_str}, error: {e}")

    except Exception as e:
        logger.warning(f"Error parsing date string: {date_str}, error: {e}")

    # Return None if parsing failed instead of the original string
    logger.warning(f"Failed to parse date string: {date_str}")
    return None
