import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tools.web_fetch import fetch_url


class FakeHeaders(dict):

    def get_content_charset(self):
        return "utf-8"


    def get_content_type(self):
        return self.get("Content-Type", "text/html")


class FakeResponse:

    def __init__(self, body, url="https://example.com", content_type="text/html; charset=utf-8"):
        self._body = body.encode("utf-8")
        self._url = url
        self.headers = FakeHeaders({"Content-Type": content_type})


    def read(self):
        return self._body


    def geturl(self):
        return self._url


class WebFetchTests(unittest.TestCase):

    def test_fetch_url_extracts_title_and_content(self):
        html = """
        <html>
          <head><title>Example Title</title></head>
          <body>
            <nav>Navigation</nav>
            <main>
              <h1>Headline</h1>
              <p>First paragraph.</p>
              <script>ignore me</script>
              <p>Second paragraph.</p>
            </main>
          </body>
        </html>
        """

        with patch("tools.web_fetch.urllib.request.urlopen", return_value=FakeResponse(html)):
            payload = fetch_url({"url": "https://example.com"})

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["url"], "https://example.com")
        self.assertEqual(payload["final_url"], "https://example.com")
        self.assertEqual(payload["title"], "Example Title")
        self.assertIn("Headline", payload["content"])
        self.assertIn("First paragraph.", payload["content"])
        self.assertIn("Second paragraph.", payload["content"])
        self.assertNotIn("Navigation", payload["content"])


    def test_fetch_url_handles_timeout(self):
        def raise_timeout(*args, **kwargs):
            raise TimeoutError("timed out")

        with patch("tools.web_fetch.urllib.request.urlopen", side_effect=raise_timeout):
            payload = fetch_url({"url": "https://example.com", "timeout": 1})

        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["url"], "https://example.com")
        self.assertIn("Timeout", payload["error"])


    def test_fetch_url_rejects_non_http_urls(self):
        payload = fetch_url({"url": "ftp://example.com"})
        self.assertEqual(payload["status"], "error")
        self.assertIn("Only http:// and https:// URLs are supported", payload["error"])


if __name__ == "__main__":
    unittest.main()
