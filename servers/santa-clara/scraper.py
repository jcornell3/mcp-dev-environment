"""
Santa Clara County Property Tax Web Scraper
Uses Playwright to scrape real-time property tax data from TellerOnline
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

# Cache for scraped data (APN -> {data, timestamp})
_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_HOURS = 24


def _is_cache_valid(apn: str) -> bool:
    """Check if cached data exists and is still valid"""
    if apn not in _cache:
        return False

    cached_time = _cache[apn].get("cached_at")
    if not cached_time:
        return False

    # Check if cache is still within TTL
    cache_age = datetime.now() - datetime.fromisoformat(cached_time)
    return cache_age < timedelta(hours=CACHE_TTL_HOURS)


def _get_cached_data(apn: str) -> Optional[Dict[str, Any]]:
    """Get cached property data if available and valid"""
    if _is_cache_valid(apn):
        logger.info(f"Cache hit for APN {apn}")
        return _cache[apn]["data"]
    return None


def _cache_data(apn: str, data: Dict[str, Any]):
    """Cache property data with timestamp"""
    _cache[apn] = {
        "data": data,
        "cached_at": datetime.now().isoformat()
    }
    logger.info(f"Cached data for APN {apn}")


async def scrape_property_tax(apn: str) -> Dict[str, Any]:
    """
    Scrape property tax information from Santa Clara County TellerOnline

    Args:
        apn: Assessor's Parcel Number (e.g., "288-13-033")

    Returns:
        Dictionary containing property tax information

    Raises:
        ValueError: If APN is invalid or not found
        Exception: If scraping fails
    """

    # Check cache first
    cached_data = _get_cached_data(apn)
    if cached_data:
        return cached_data

    logger.info(f"Scraping property tax data for APN: {apn}")

    # Normalize APN format (remove spaces, ensure dashes)
    apn_normalized = apn.replace(" ", "").strip()

    try:
        async with async_playwright() as p:
            # Launch browser in headless mode
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()

            try:
                # Navigate to TellerOnline search page
                logger.debug(f"Navigating to TellerOnline for APN {apn_normalized}")
                await page.goto("https://santaclaracounty.telleronline.net/search/1",
                               wait_until="networkidle", timeout=30000)

                # Wait for search input to be visible
                await page.wait_for_selector('input[type="text"]', timeout=10000)

                # Enter APN in search field
                await page.fill('input[type="text"]', apn_normalized)

                # Click search button or press Enter
                await page.press('input[type="text"]', 'Enter')

                # Wait for results to load
                await page.wait_for_load_state("networkidle", timeout=15000)

                # Check if property was found
                # Look for error messages or "no results" text
                page_content = await page.content()
                if "not found" in page_content.lower() or "no results" in page_content.lower():
                    raise ValueError(f"Property with APN {apn} not found in Santa Clara County database")

                # Extract property information
                # This will need to be adjusted based on actual page structure
                property_data = await _extract_property_data(page, apn_normalized)

                # Cache the results
                _cache_data(apn_normalized, property_data)

                return property_data

            finally:
                await browser.close()

    except PlaywrightTimeout as e:
        logger.error(f"Timeout while scraping APN {apn}: {str(e)}")
        raise Exception(f"Timeout while fetching property data for APN {apn}. The website may be slow or unavailable.")
    except ValueError:
        # Re-raise ValueError (APN not found)
        raise
    except Exception as e:
        logger.error(f"Error scraping APN {apn}: {str(e)}")
        raise Exception(f"Failed to scrape property tax data: {str(e)}")


async def _extract_property_data(page, apn: str) -> Dict[str, Any]:
    """
    Extract property tax data from the page

    This function needs to be customized based on the actual HTML structure
    of the TellerOnline results page.
    """

    # TODO: Implement actual extraction logic based on page HTML structure
    # For now, this is a placeholder that would need to be filled in
    # after inspecting the actual rendered page

    logger.warning("Using placeholder extraction logic - needs implementation")

    # Placeholder structure - replace with actual scraping
    data = {
        "apn": apn,
        "address": "PLACEHOLDER - Need to extract from page",
        "tax_rate_area": "PLACEHOLDER",
        "property_type": "PLACEHOLDER",
        "tax_year": "2025/2026",
        "annual_tax_bill": 0.0,
        "installment_1": {
            "tax_amount": 0.0,
            "status": "UNKNOWN",
            "balance_due": 0.0,
            "pay_by_date": "PLACEHOLDER"
        },
        "installment_2": {
            "tax_amount": 0.0,
            "status": "UNKNOWN",
            "balance_due": 0.0,
            "pay_by_date": "PLACEHOLDER"
        },
        "county": "Santa Clara",
        "retrieved_at": datetime.now().isoformat(),
        "scraped": True,
        "note": "Extraction logic needs implementation - see scraper.py:_extract_property_data"
    }

    return data


def clear_cache():
    """Clear all cached property data"""
    global _cache
    _cache = {}
    logger.info("Property tax cache cleared")


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    valid_entries = sum(1 for apn in _cache if _is_cache_valid(apn))
    return {
        "total_entries": len(_cache),
        "valid_entries": valid_entries,
        "expired_entries": len(_cache) - valid_entries,
        "cache_ttl_hours": CACHE_TTL_HOURS
    }
