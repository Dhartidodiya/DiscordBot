from dateparser import parse
from datetime import datetime, timedelta
import re
import calendar

def parse_date_range(message: str):
    message = message.lower().strip()
    today = datetime.today().date()

    # Relaxed parsing settings for natural French phrases
    relaxed_settings = {
        "PREFER_DATES_FROM": "past",
        "DATE_ORDER": "DMY"
    }

    #  Today
    if "today" in message or "aujourd'hui" in message:
        return today, today

    # Yesterday
    if "yesterday" in message or "hier" in message:
        return today - timedelta(days=1), today - timedelta(days=1)

    # Format: dd/mm/yyyy - dd/mm/yyyy
    match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})\s*[-àto]+\s*(\d{1,2}/\d{1,2}/\d{4})", message)
    if match:
        d1 = parse(match.group(1), settings=relaxed_settings, languages=["fr", "en"])
        d2 = parse(match.group(2), settings=relaxed_settings, languages=["fr", "en"])
        if d1 and d2:
            return d1.date(), d2.date()

    # Format: "du 5 juin au 10 juin"  or "from 5 June to 10 June"
    match = re.search(r"(?:from|du)\s+(.*?)\s+(?:to|au|jusqu[’']?à)\s+(.*)", message)
    if match:
        d1 = parse(match.group(1), settings=relaxed_settings, languages=["fr", "en"])
        d2 = parse(match.group(2), settings=relaxed_settings, languages=["fr", "en"])
        if d1 and d2:
            return d1.date(), d2.date()
        
        
    # Format: "May 2025" or "juin 2025"
    match = re.search(r"([a-zéû]+)\s+(\d{4})", message)
    if match:
        month_str, year = match.groups()
        d1 = parse(f"1 {month_str} {year}", settings=relaxed_settings, languages=["fr", "en"])
        if d1:
            _, last_day = calendar.monthrange(d1.year, d1.month)
            d2 = datetime(d1.year, d1.month, last_day)
            return d1.date(), d2.date()
    
    # Format: Week 
    week_map = {
        "première": 1, "1ère": 1, "first": 1, "1st": 1,
        "deuxième": 2, "2ème": 2, "second": 2, "2nd": 2,
        "troisième": 3, "3ème": 3, "third": 3, "3rd": 3,
        "quatrième": 4, "4ème": 4, "fourth": 4, "4th": 4,
        "cinquième": 5, "5ème": 5, "fifth": 5, "5th": 5
    }

    
    match = re.search(r"(première|1ère|deuxième|2ème|troisième|3ème|quatrième|4ème|cinquième|5ème)\s+semaine\s+de\s+([a-zéû]+)(?:\s+(\d{4}))?", message)
    if match:
        week_label, month_name, year = match.groups()
        week_number = week_map.get(week_label)
        year = int(year) if year else today.year
        month_date = parse(f"1 {month_name} {year}", settings=relaxed_settings, languages=["fr", "en"])

        if week_number and month_date:
            first_day = datetime(month_date.year, month_date.month, 1).date()
            start = first_day + timedelta(days=(week_number - 1) * 7)
            end = start + timedelta(days=6)
            _, last_day = calendar.monthrange(month_date.year, month_date.month)
            if end.day > last_day:
                end = datetime(month_date.year, month_date.month, last_day).date()
            return start, end
    
    # Format: whole year
    match = re.fullmatch(r"(?:year\s+)?(\d{4})", message)
    if match:
        year = int(match.group(1))
        d1 = datetime(year, 1, 1).date()
        d2 = datetime(year, 12, 31).date()
        return d1, d2
    
    # Single date (like "5 juin")
    d = parse(message, settings=relaxed_settings, languages=["fr", "en"])
    if d:
        return d.date(), d.date()

    # No result
    return None, None
