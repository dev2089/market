#!/usr/bin/env python3
"""Small, local-only Google Shopping comparison app powered by SerpApi."""

from __future__ import annotations

import json
import os
import statistics
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
HOST = os.environ.get("SHOP_SIGNAL_HOST", "127.0.0.1")
PORT = int(os.environ.get("SHOP_SIGNAL_PORT", "8000"))
API_ENDPOINT = "https://serpapi.com/search.json"
RESULT_LIMIT = 12
CACHE_SECONDS = 3600
MIN_REQUEST_INTERVAL = 4
cache: dict[str, tuple[float, dict]] = {}
last_request_at = 0.0


class UserError(Exception):
    pass


def clean_text(value: object, limit: int = 240) -> str:
    return " ".join(str(value or "").split())[:limit]


def safe_url(value: object) -> str:
    url = clean_text(value, 1000)
    return url if url.startswith("https://") else ""


def search_products(query: str, location: str) -> dict:
    global last_request_at
    api_key = os.environ.get("SERPAPI_API_KEY", "").strip()
    if not api_key:
        raise UserError("Set SERPAPI_API_KEY in the server environment first. The key stays on this device and is never sent to the browser.")

    cache_key = f"{query.casefold()}|{location.casefold()}"
    now = time.time()
    cached = cache.get(cache_key)
    if cached and now - cached[0] < CACHE_SECONDS:
        return {**cached[1], "cached": True}
    if now - last_request_at < MIN_REQUEST_INTERVAL:
        raise UserError("Please wait a few seconds before making another new search.")

    params = {
        "engine": "google_shopping",
        "q": query,
        "location": location,
        "gl": "in",
        "hl": "en",
        "api_key": api_key,
    }
    request = Request(
        f"{API_ENDPOINT}?{urlencode(params)}",
        headers={"User-Agent": "ShopSignal/0.1 (+local small-business research tool)"},
    )
    last_request_at = now
    try:
        with urlopen(request, timeout=25) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise UserError("SerpApi rejected the key. Check it in your SerpApi dashboard; the key was not saved by this app.") from exc
        raise UserError(f"SerpApi returned HTTP {exc.code}. Try again later or review your account quota.") from exc
    except (TimeoutError, URLError, json.JSONDecodeError) as exc:
        raise UserError("Could not reach SerpApi or read its response. Check the connection and try again.") from exc

    if payload.get("error"):
        raise UserError(clean_text(payload["error"], 300))

    rows = []
    numeric_prices = []
    for item in payload.get("shopping_results", [])[:RESULT_LIMIT]:
        price_value = item.get("extracted_price")
        try:
            numeric_price = float(price_value) if price_value is not None else None
        except (TypeError, ValueError):
            numeric_price = None
        if numeric_price is not None and numeric_price > 0:
            numeric_prices.append(numeric_price)
        rows.append({
            "title": clean_text(item.get("title"), 220),
            "price": clean_text(item.get("price"), 80),
            "numeric_price": numeric_price,
            "seller": clean_text(item.get("source"), 100),
            "url": safe_url(item.get("product_link") or item.get("link")),
            "rating": item.get("rating"),
            "reviews": item.get("reviews"),
            "snippet": clean_text(item.get("snippet"), 300),
        })

    result = {
        "query": query,
        "location": location,
        "products": rows,
        "price_sample_count": len(numeric_prices),
        "median_price": statistics.median(numeric_prices) if numeric_prices else None,
        "min_price": min(numeric_prices) if numeric_prices else None,
        "max_price": max(numeric_prices) if numeric_prices else None,
        "currency_context": "India-targeted Google Shopping results; confirm each listing and currency before using these figures.",
        "cached": False,
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    }
    cache[cache_key] = (now, result)
    if len(cache) > 100:
        oldest = sorted(cache, key=lambda key: cache[key][0])[:20]
        for key in oldest:
            cache.pop(key, None)
    return result


class Handler(BaseHTTPRequestHandler):
    server_version = "ShopSignal/0.1"

    def log_message(self, fmt: str, *args) -> None:
        # Avoid logging search terms or request query strings.
        print(f"{self.log_date_time_string()} {self.address_string()} {fmt % args}")

    def send_json(self, status: int, payload: dict) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/search":
            values = parse_qs(parsed.query)
            query = clean_text(values.get("q", [""])[0], 120)
            location = clean_text(values.get("location", ["Mumbai, India"])[0], 100)
            if len(query) < 2:
                self.send_json(400, {"error": "Enter a product and enough detail to distinguish its size or model."})
                return
            if len(location) < 2:
                self.send_json(400, {"error": "Enter a city or region."})
                return
            try:
                self.send_json(200, search_products(query, location))
            except UserError as exc:
                self.send_json(502, {"error": str(exc)})
            return

        relative = "index.html" if parsed.path in ("/", "") else parsed.path.lstrip("/")
        target = (ROOT / "static" / relative).resolve()
        static_root = (ROOT / "static").resolve()
        if static_root not in target.parents and target != static_root:
            self.send_error(404)
            return
        if not target.is_file():
            self.send_error(404)
            return
        body = target.read_bytes()
        content_type = "text/html; charset=utf-8" if target.suffix == ".html" else "text/plain; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src https: data:; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    if not 1 <= PORT <= 65535:
        raise SystemExit("SHOP_SIGNAL_PORT must be between 1 and 65535")
    print(f"ShopSignal is running at http://{HOST}:{PORT}")
    print("The SerpApi key is read from the environment and is not written to disk.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
