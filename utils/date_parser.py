from dateparser import parse
from datetime import datetime, timedelta
import re

def parse_date_range(message: str):
    message = message.lower()

    if "today" in message or "aujourd'hui" in message:
        today = datetime.today().date()
        return today, today

    if "yesterday" in message or "hier" in message:
        day = datetime.today().date() - timedelta(days=1)
        return day, day

    match = re.search(r"(\d{1,2} \w+) (?:to|au|jusqu[’']?à) (\d{1,2} \w+)", message)
    if match:
        d1 = parse(match.group(1))
        d2 = parse(match.group(2))
        if d1 and d2:
            return d1.date(), d2.date()

    d = parse(message)
    if d:
        return d.date(), d.date()

    return None, None
