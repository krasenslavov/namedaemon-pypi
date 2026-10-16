"""NameDaemon client for the public REST layer (https://namedaemon.com/wp-json/nd/v1).

Standard library only (urllib), so it installs with no dependencies.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterable, Optional, Sequence, Union

from . import __version__

DEFAULT_BASE_URL = "https://namedaemon.com/wp-json/nd/v1"

Json = Dict[str, Any]


class NameDaemonError(Exception):
    """Any failed request. `status` is 0 for network errors."""

    def __init__(self, message: str, status: int = 0, code: str = "", body: Any = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.body = body


class RateLimitError(NameDaemonError):
    """HTTP 429: the shared limit was hit. `retry_after` is in seconds."""

    def __init__(self, message: str, retry_after: int = 60, **kw: Any):
        super().__init__(message, status=429, **kw)
        self.retry_after = retry_after


def _clean(params: Optional[Dict[str, Any]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k, v in (params or {}).items():
        if v is None or v == "":
            continue
        if isinstance(v, bool):
            v = "true" if v else "false"
        elif isinstance(v, (list, tuple)):
            v = ",".join(str(x) for x in v)
        out[k] = str(v)
    return out


class NameDaemon:
    """Client for the public NameDaemon API.

    >>> nd = NameDaemon()
    >>> nd.rate("example")["score"]
    95.5
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 20.0,
        retries: int = 0,
        user_agent: Optional[str] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self.user_agent = user_agent or f"namedaemon-py/{__version__}"

    # -- transport ---------------------------------------------------------
    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, body: Any = None) -> Json:
        url = f"{self.base_url}/{path.lstrip('/')}"
        query = urllib.parse.urlencode(_clean(params))
        if query:
            url += "?" + query
        headers = {"Accept": "application/json", "User-Agent": self.user_agent}
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        attempt = 0
        while True:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read().decode("utf-8", "replace")
                    status = resp.status
                    hdrs = resp.headers
            except urllib.error.HTTPError as e:
                raw = e.read().decode("utf-8", "replace")
                status = e.code
                hdrs = e.headers
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                raise NameDaemonError(f"Network error: {e}") from e

            try:
                parsed = json.loads(raw) if raw else None
            except ValueError:
                parsed = None

            if 200 <= status < 300:
                if parsed is None:
                    raise NameDaemonError("Response was not JSON", status=status)
                return parsed

            message = (parsed or {}).get("message") if isinstance(parsed, dict) else None
            code = (parsed or {}).get("code", "") if isinstance(parsed, dict) else ""
            message = message or f"HTTP {status}"
            if status == 429:
                try:
                    retry_after = int(hdrs.get("Retry-After", "")) if hdrs else 60
                except (TypeError, ValueError):
                    retry_after = 60
                if retry_after <= 0:
                    retry_after = 60
                if attempt < self.retries:
                    attempt += 1
                    time.sleep(min(retry_after, 60))
                    continue
                raise RateLimitError(message, retry_after=retry_after, code=code, body=parsed)
            raise NameDaemonError(message, status=status, code=code, body=parsed)

    def get(self, path: str, **params: Any) -> Json:
        """Any public GET route, e.g. ``nd.get("trend", keyword="ai")``."""
        return self._request("GET", path, params)

    def post(self, path: str, body: Any) -> Json:
        """Any public POST route with a JSON body."""
        return self._request("POST", path, body=body)

    # -- tools -------------------------------------------------------------
    def rate(self, name: str) -> Json:
        """Brandability score and breakdown for one name (4-24 letters)."""
        return self.get("rate", name=name)

    def ideas(self, q: str, limit: Optional[int] = None) -> Json:
        """Two-word .com ideas built around a keyword (3-14 letters)."""
        return self.get("ideas", q=q, limit=limit)

    def verify(self, domains: Sequence[str]) -> Json:
        """Live availability of up to 10 names."""
        return self.post("verify", {"domains": list(domains)})

    def check(self, domains: Sequence[str], verify: int = 0) -> Json:
        """Zone status of up to 50 names, with optional live checks (0-10)."""
        return self.post("check", {"domains": list(domains), "verify": verify})

    def tld_check(self, label: str, tlds: Union[str, Iterable[str]]) -> Json:
        """One label across up to 12 extensions."""
        return self.get("tld-check", label=label, tlds=tlds if isinstance(tlds, str) else list(tlds))

    def tco(self, tld: Optional[str] = None, **options: Any) -> Json:
        """Cost of ownership for an extension, or a ranking with q/scope/sort/limit."""
        return self.get("tco", tld=tld, **options)

    def hacks(self, **options: Any) -> Json:
        """Domain hacks (e.g. hack.er). Pass word=... or keyword=... and mode=..."""
        return self.get("hacks", **options)

    def names(self, seeds: Union[str, Iterable[str]], **options: Any) -> Json:
        """Brand-name generator: seeds plus vibe, min_len, max_len, count, variation, hide_taken."""
        return self.get("names", seeds=seeds if isinstance(seeds, str) else list(seeds), **options)

    def domain_health(self, name: str) -> Json:
        """Registration, DNS, email and blocklist checks for a .com label."""
        return self.get("domain-health", name=name)

    def appraise(self, name: str, deep: bool = False) -> Json:
        """Strength report for a name (no price)."""
        return self.get("appraise", name=name, deep=True if deep else None)

    def handles(self, name: str) -> Json:
        """Username availability on social platforms."""
        return self.get("handles", name=name)

    def web3(self, name: str) -> Json:
        """ENS and Solana name availability."""
        return self.get("web3", name=name)

    def screen(self, name: str) -> Json:
        """Name screening: unwanted meanings in other languages."""
        return self.get("screen", name=name)

    def hosting(self, mode: Optional[str] = None, q: Optional[str] = None) -> Json:
        """Hosting provider ranking (mode: top, provider or domain)."""
        return self.get("hosting", mode=mode, q=q)

    def trend(self, keyword: str) -> Json:
        """Daily size history for a keyword in the .com zone."""
        return self.get("trend", keyword=keyword)
