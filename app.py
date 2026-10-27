"""Uptime Monitor: checks websites and exposes Prometheus metrics."""
import logging
import os
import time

import requests
from prometheus_client import Counter, Gauge, start_http_server

# Settings come from environment variables, so we can change them
# without changing code (same image works in Docker, Kubernetes, ...).
SITES = [s.strip() for s in os.getenv(
    "SITES", "https://google.com,https://github.com,https://example.com"
).split(",") if s.strip()]
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))   # seconds
TIMEOUT = float(os.getenv("TIMEOUT", "10"))               # seconds
PORT = int(os.getenv("PORT", "8000"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("uptime")

SITE_UP = Gauge("uptime_site_up", "1 if the site is up, 0 if down", ["url"])
RESPONSE_SECONDS = Gauge("uptime_site_response_seconds", "Response time of the last check", ["url"])
STATUS_CODE = Gauge("uptime_site_status_code", "HTTP status code of the last check (0 = no answer)", ["url"])
CHECKS_TOTAL = Counter("uptime_checks_total", "Number of checks done", ["url", "result"])


def check_site(url):
    """Check one site and update its metrics."""
    start = time.monotonic()
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        elapsed = time.monotonic() - start
        up = resp.status_code < 400
        STATUS_CODE.labels(url=url).set(resp.status_code)
        RESPONSE_SECONDS.labels(url=url).set(elapsed)
        log.info("%s status=%s time=%.3fs", url, resp.status_code, elapsed)
    except requests.RequestException as err:
        up = False
        STATUS_CODE.labels(url=url).set(0)
        RESPONSE_SECONDS.labels(url=url).set(time.monotonic() - start)
        log.warning("%s DOWN: %s", url, err)
    SITE_UP.labels(url=url).set(1 if up else 0)
    CHECKS_TOTAL.labels(url=url, result="up" if up else "down").inc()


def main():
    start_http_server(PORT)
    log.info("Serving metrics on :%d/metrics, checking %s every %ds", PORT, SITES, CHECK_INTERVAL)
    while True:
        for url in SITES:
            check_site(url)
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()