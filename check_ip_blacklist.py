import os
import sys
from pathlib import Path

import requests
from loguru import logger as log
from tabulate import tabulate

from controller import GREEN, RED, TABLE_FORMAT, YELLOW

# Single check:
# https://www.abuseipdb.com/check/193.124.7.9
blacklist = Path("controller", "confs", "fail2ban", "ip.blacklist")

API_URL = "https://api.abuseipdb.com/api/v2/check"
API_KEY = os.getenv("ABUSEIPDB_APIKEY")

if not API_KEY:
    log.critical("ABUSEIPDB_APIKEY environment variable not found")
    sys.exit(1)

if not blacklist.exists():
    log.critical("Blacklist file not found: {}", blacklist)
    sys.exit(1)

blacklist_data = []
with open(blacklist) as blacklist_file:
    for IP in blacklist_file.readlines():
        IP = IP.strip()

        r = requests.get(
            API_URL,
            params={"ipAddress": IP},
            data={"maxAgeInDays": 180},
            headers={"Key": API_KEY, "Accept": "application/json"},
            timeout=15,
        )
        data = r.json().get("data", {})
        score = data.get("abuseConfidenceScore", 0)
        total_reports = data.get("totalReports", 0)
        last_report = data.get("lastReportedAt", "N/A")
        if last_report is None:
            last_report = "N/A"
        else:
            last_report = last_report.replace("+00:00", "").replace("T", " ")
        country = data.get("countryCode", "XX")
        domain = data.get("domain", "N/A")

        if score > 80:
            color = RED
        elif score > 0:
            color = YELLOW
        else:
            color = GREEN
        blacklist_data.append(
            [
                color(IP),
                color(country),
                color(domain),
                color(score),
                color(total_reports),
                color(last_report),
            ]
        )

print(
    tabulate(
        blacklist_data,
        tablefmt=TABLE_FORMAT,
        headers=["IP", "COUNTRY", "DOMAIN", "SCORE", "REPORTS", "LAST REPORT"],
    )
)
