import io
import json
import os
import unittest
import urllib.error
from unittest import mock

from namedaemon import NameDaemon, NameDaemonError, RateLimitError


class FakeResp:
    def __init__(self, body, status=200, headers=None):
        self._b = body if isinstance(body, str) else json.dumps(body)
        self.status = status
        self.headers = headers or {}

    def read(self):
        return self._b.encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def http_error(status, body, headers=None):
    return urllib.error.HTTPError("u", status, "x", headers or {}, io.BytesIO(json.dumps(body).encode()))


class ClientTests(unittest.TestCase):
    @mock.patch("urllib.request.urlopen")
    def test_rate_url_and_agent(self, uo):
        uo.return_value = FakeResp({"name": "example", "score": 95.5})
        r = NameDaemon().rate("example")
        self.assertEqual(r["score"], 95.5)
        req = uo.call_args[0][0]
        self.assertEqual(req.full_url, "https://namedaemon.com/wp-json/nd/v1/rate?name=example")
        self.assertTrue(req.get_header("User-agent").startswith("namedaemon-py/"))

    @mock.patch("urllib.request.urlopen")
    def test_lists_join_and_none_dropped(self, uo):
        uo.return_value = FakeResp({"results": []})
        NameDaemon().tld_check("nova", ["com", "io"])
        self.assertIn("label=nova&tlds=com%2Cio", uo.call_args[0][0].full_url)

    @mock.patch("urllib.request.urlopen")
    def test_check_posts_json(self, uo):
        uo.return_value = FakeResp({"results": []})
        NameDaemon().check(["a", "b"], verify=2)
        req = uo.call_args[0][0]
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(json.loads(req.data), {"domains": ["a", "b"], "verify": 2})

    @mock.patch("urllib.request.urlopen")
    def test_429(self, uo):
        uo.side_effect = http_error(429, {"code": "ndt_rate_limited", "message": "Too many requests."}, {"Retry-After": "30"})
        with self.assertRaises(RateLimitError) as cm:
            NameDaemon().rate("example")
        self.assertEqual(cm.exception.retry_after, 30)

    @mock.patch("urllib.request.urlopen")
    def test_400(self, uo):
        uo.side_effect = http_error(400, {"code": "rest_invalid_param", "message": "Invalid parameter(s): name"})
        with self.assertRaises(NameDaemonError) as cm:
            NameDaemon().rate("x1")
        self.assertEqual(cm.exception.status, 400)
        self.assertIn("name", cm.exception.message)

    @mock.patch("urllib.request.urlopen")
    def test_non_json(self, uo):
        uo.return_value = FakeResp("<html>challenge</html>")
        with self.assertRaises(NameDaemonError):
            NameDaemon().rate("example")

    @unittest.skipUnless(os.environ.get("NAMEDAEMON_LIVE"), "set NAMEDAEMON_LIVE=1")
    def test_live(self):
        r = NameDaemon().rate("example")
        self.assertEqual(r["name"], "example")
        self.assertIsInstance(r["score"], (int, float))


if __name__ == "__main__":
    unittest.main()
