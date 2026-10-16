# namedaemon

Python client and command-line tool for [NameDaemon](https://namedaemon.com), a free set of .com domain tools: availability,
brandability scores, name ideas, extension costs, domain health and more. No API key, no dependencies.

```
pip install namedaemon
```

Needs Python 3.9 or newer.

## Command line

```
namedaemon rate example
namedaemon ideas nova 10
namedaemon check nova novax mybrand
namedaemon tld nova com io ai
namedaemon tco io
namedaemon health example
namedaemon --json appraise example
```

`python -m namedaemon ...` works too. `--json` (before the command) prints the raw response.

## Library

```python
from namedaemon import NameDaemon

nd = NameDaemon()

r = nd.rate("example")
print(r["score"], r["verdict"])  # 95.5 Excellent

ideas = nd.ideas("nova", limit=10)["ideas"]
results = nd.check(["nova", "novax"])["results"]
cost = nd.tco("io", years=5)
health = nd.domain_health("example")
```

| Method | What it returns |
|---|---|
| `rate(name)` | brandability score, verdict, breakdown, tips |
| `ideas(keyword, limit=None)` | two-word .com ideas built around a keyword |
| `check(names, verify=0)` | zone status of up to 50 names, optional live checks |
| `verify(names)` | live availability of up to 10 names |
| `tld_check(label, tlds)` | one label across up to 12 extensions |
| `tco(tld, **options)` | registration, renewal and total cost by registrar |
| `hacks(word=...)` | domain hacks such as `hack.er` |
| `names(seeds, vibe=..., count=...)` | brand-name generator |
| `domain_health(name)` | registration, DNS, email and blocklist checks |
| `appraise(name, deep=False)` | strength report (no price) |
| `handles(name)` | username availability on social platforms |
| `web3(name)`, `screen(name)`, `hosting()`, `trend(keyword)` | ENS/Solana names, name screening, hosting share, keyword trend |
| `get(path, **params)`, `post(path, body)` | any other public route under `/wp-json/nd/v1/` |

Every method returns the parsed JSON of the matching REST route. The package is typed (`py.typed`).

### Errors and rate limits

The public API is free and shared, so it limits each visitor to roughly 20 requests a minute. Heavier routes count for more.
When the limit is hit the client raises `RateLimitError` (with `retry_after` in seconds, 60 by default); pass `retries=1` to wait
and retry automatically. Other failures raise `NameDaemonError` with `status`, `code` and the server's `message`.

```python
from namedaemon import NameDaemon, RateLimitError

nd = NameDaemon(timeout=20, retries=1)
try:
    nd.rate("example")
except RateLimitError as e:
    print(e.retry_after)
```

Please keep usage reasonable. For bulk work, see the paid plan at https://namedaemon.com.

## Links

- Website and free tools: https://namedaemon.com
- Issues: https://github.com/krasenslavov/namedaemon-pypi/issues
- JavaScript version: `npm install namedaemon`

MIT license.
