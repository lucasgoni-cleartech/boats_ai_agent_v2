"""
Deterministic date normalization utility.

Converts structured time_intent objects into absolute date ranges
in "YYYY-MM-DD to YYYY-MM-DD" format for Looker filters.
"""

import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz

logger = logging.getLogger(__name__)


def to_absolute_range(time_intent: dict, today_iso: str, tz: str = "America/New_York") -> str | None:
    """
    Convert time_intent to absolute date range string.

    Args:
        time_intent: Structured time intent from NL2LookerModule
        today_iso: Current date in YYYY-MM-DD format
        tz: Timezone name (default: America/New_York)

    Returns:
        Date range string "YYYY-MM-DD to YYYY-MM-DD" or None if cannot parse

    Examples:
        >>> to_absolute_range({"preset": "yesterday"}, "2025-09-29")
        "2025-09-28 to 2025-09-28"

        >>> to_absolute_range({"preset": "last_n_days", "n": 7}, "2025-09-29")
        "2025-09-23 to 2025-09-29"

        >>> to_absolute_range({"preset": "mtd"}, "2025-09-29")
        "2025-09-01 to 2025-09-29"
    """
    if not time_intent or not isinstance(time_intent, dict):
        logger.warning("DateNormalizer: Invalid time_intent (not a dict)")
        return None

    preset = time_intent.get("preset")
    if not preset:
        logger.warning("DateNormalizer: Missing 'preset' field in time_intent")
        return None

    try:
        # Parse today_iso in the specified timezone
        timezone = pytz.timezone(tz)
        today = datetime.strptime(today_iso, "%Y-%m-%d").replace(tzinfo=timezone).date()

        start_date = None
        end_date = None

        # Handle each preset type
        if preset == "yesterday":
            start_date = today - timedelta(days=1)
            end_date = start_date

        elif preset == "today":
            start_date = today
            end_date = today

        elif preset == "last_n_days":
            n = time_intent.get("n", 7)
            if not isinstance(n, int) or n < 1:
                logger.warning("DateNormalizer: Invalid 'n' value in last_n_days: %s", n)
                return None
            start_date = today - timedelta(days=n - 1)
            end_date = today

        elif preset == "mtd":
            # Month to date: first day of current month to today
            start_date = today.replace(day=1)
            end_date = today

        elif preset == "qtd":
            # Quarter to date: first day of current quarter to today
            quarter_month = ((today.month - 1) // 3) * 3 + 1
            start_date = today.replace(month=quarter_month, day=1)
            end_date = today

        elif preset == "ytd":
            # Year to date: Jan 1 of current year to today
            start_date = today.replace(month=1, day=1)
            end_date = today

        elif preset == "prev_month":
            # Previous month: first to last day of previous month
            first_of_this_month = today.replace(day=1)
            last_of_prev_month = first_of_this_month - timedelta(days=1)
            start_date = last_of_prev_month.replace(day=1)
            end_date = last_of_prev_month

        elif preset == "prev_quarter":
            # Previous quarter: first to last day of previous quarter
            current_quarter_month = ((today.month - 1) // 3) * 3 + 1
            first_of_current_quarter = today.replace(month=current_quarter_month, day=1)
            last_of_prev_quarter = first_of_current_quarter - timedelta(days=1)
            prev_quarter_month = ((last_of_prev_quarter.month - 1) // 3) * 3 + 1
            start_date = last_of_prev_quarter.replace(month=prev_quarter_month, day=1)
            end_date = last_of_prev_quarter

        elif preset == "prev_year":
            # Previous year: Jan 1 to Dec 31 of previous year
            prev_year = today.year - 1
            start_date = today.replace(year=prev_year, month=1, day=1)
            end_date = today.replace(year=prev_year, month=12, day=31)

        elif preset == "absolute":
            # Absolute range: validate and return as-is
            start_str = time_intent.get("start")
            end_str = time_intent.get("end")

            if not start_str or not end_str:
                logger.warning("DateNormalizer: Missing 'start' or 'end' in absolute preset")
                return None

            try:
                start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
            except ValueError as e:
                logger.warning("DateNormalizer: Invalid date format in absolute preset: %s", e)
                return None

        else:
            logger.warning("DateNormalizer: Unsupported preset '%s'", preset)
            return None

        # Ensure start <= end (swap if needed)
        if start_date and end_date:
            if start_date > end_date:
                logger.info("DateNormalizer: Swapping start/end dates (start > end)")
                start_date, end_date = end_date, start_date

            result = f"{start_date.isoformat()} to {end_date.isoformat()}"
            logger.info("DateNormalizer: %s -> %s", time_intent, result)
            return result

    except Exception as e:
        logger.error("DateNormalizer: Error converting time_intent: %s", e, exc_info=True)
        return None

    return None