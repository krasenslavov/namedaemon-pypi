"""Command line: ``namedaemon rate example`` or ``python -m namedaemon rate example``."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, List, Optional

from . import __version__
from .client import NameDaemon, NameDaemonError, RateLimitError


def _pretty(cmd: str, r: Any) -> str:
    if cmd == "rate":
        line = f"{r['name']}: {r['score'] if r.get('score') is not None else 'no score'} {r.get('verdict') or ''}".strip()
        tips = r.get("tips") or []
        return line + ("\n- " + "\n- ".join(tips) if tips else "")
    if cmd == "ideas":
        return "\n".join(f"{i['domain']}.com  {i['score']}" for i in r["ideas"])
    if cmd in ("check", "verify", "tld"):
        return "\n".join(
            f"{x['domain']}  {x['status']}" + (f" (drops {x['est_drop']})" if x.get("est_drop") else "")
            for x in r["results"]
        )
    return json.dumps(r, indent=2)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="namedaemon", description="NameDaemon .com domain tools (https://namedaemon.com)")
    p.add_argument("--version", action="version", version=f"namedaemon {__version__}")
    p.add_argument("--json", action="store_true", help="print the raw JSON response")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("rate", help="brandability score for one name").add_argument("name")
    ideas = sub.add_parser("ideas", help="two-word .com ideas around a keyword")
    ideas.add_argument("keyword")
    ideas.add_argument("limit", nargs="?", type=int)
    sub.add_parser("check", help="status of up to 50 names").add_argument("names", nargs="+")
    sub.add_parser("verify", help="live availability of up to 10 names").add_argument("names", nargs="+")
    tld = sub.add_parser("tld", help="one label across several extensions")
    tld.add_argument("label")
    tld.add_argument("tlds", nargs="+")
    sub.add_parser("tco", help="cost of ownership for an extension").add_argument("tld")
    sub.add_parser("health", help="DNS, email and registration health").add_argument("name")
    sub.add_parser("appraise", help="strength report (no price)").add_argument("name")
    sub.add_parser("handles", help="username availability on social platforms").add_argument("name")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    nd = NameDaemon()
    try:
        if args.cmd == "rate":
            res = nd.rate(args.name)
        elif args.cmd == "ideas":
            res = nd.ideas(args.keyword, args.limit)
        elif args.cmd == "check":
            res = nd.check(args.names)
        elif args.cmd == "verify":
            res = nd.verify(args.names)
        elif args.cmd == "tld":
            res = nd.tld_check(args.label, args.tlds)
        elif args.cmd == "tco":
            res = nd.tco(args.tld)
        elif args.cmd == "health":
            res = nd.domain_health(args.name)
        elif args.cmd == "appraise":
            res = nd.appraise(args.name)
        else:
            res = nd.handles(args.name)
    except RateLimitError as e:
        print(f"Rate limit reached. Try again in about {e.retry_after} seconds.", file=sys.stderr)
        return 1
    except NameDaemonError as e:
        print(f"Error{' ' + str(e.status) if e.status else ''}: {e.message}", file=sys.stderr)
        return 1
    print(json.dumps(res, indent=2) if args.json else _pretty(args.cmd, res))
    return 0
