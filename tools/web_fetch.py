import logging
import urllib.error
import urllib.request

from research.html_parser import extract_html_content
from .registry import Tool, ToolParameter


logger = logging.getLogger(__name__)


DEFAULT_TIMEOUT = 20
DEFAULT_MAX_CHARS = 12000
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)


def _normalize_input(data):
    if isinstance(data, str):
        return {"url": data}
    return dict(data or {})



def _prepare_request(url):
    return urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
    )



def _decode_body(response):
    body = response.read()
    if response.headers.get("Content-Encoding", "").lower() == "gzip":
        import gzip

        body = gzip.decompress(body)

    encoding = response.headers.get_content_charset() or "utf-8"
    try:
        return body.decode(encoding, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")



def _content_is_text(headers):
    content_type = headers.get_content_type().lower()
    full_content_type = headers.get("Content-Type", "").lower()
    disposition = headers.get("Content-Disposition", "").lower()

    if "attachment" in disposition:
        return False

    value = f"{content_type}; {full_content_type}"
    return any(
        marker in value
        for marker in (
            "text/html",
            "text/plain",
            "application/xhtml+xml",
            "application/xml",
            "text/xml",
        )
    )



def fetch_url(data):
    data = _normalize_input(data)
    url = str(data.get("url", "")).strip()
    timeout = int(data.get("timeout", DEFAULT_TIMEOUT) or DEFAULT_TIMEOUT)
    max_chars = int(data.get("max_chars", DEFAULT_MAX_CHARS) or DEFAULT_MAX_CHARS)
    timeout = max(1, min(timeout, 60))
    max_chars = max(1000, min(max_chars, 50000))

    if not url:
        return {
            "status": "error",
            "error": "'url' is required"
        }

    if not url.startswith(("http://", "https://")):
        return {
            "status": "error",
            "url": url,
            "error": "Only http:// and https:// URLs are supported"
        }

    logger.info("Fetching URL: %s", url)

    try:
        request = _prepare_request(url)
        response = urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        logger.warning("HTTP error fetching %s: %s", url, exc)
        return {
            "status": "error",
            "url": url,
            "error": f"HTTP error: {exc.code}"
        }
    except urllib.error.URLError as exc:
        logger.warning("URL error fetching %s: %s", url, exc)
        return {
            "status": "error",
            "url": url,
            "error": f"URL error: {exc.reason}"
        }
    except TimeoutError:
        logger.warning("Timeout fetching %s", url)
        return {
            "status": "error",
            "url": url,
            "error": "Timeout while fetching URL"
        }
    except Exception as exc:
        logger.exception("Unexpected error fetching %s", url)
        return {
            "status": "error",
            "url": url,
            "error": f"Unexpected error: {exc}"
        }

    try:
        final_url = response.geturl()
        headers = response.headers
        raw_body = _decode_body(response)
        if not _content_is_text(headers):
            content = raw_body[:max_chars]
            title = ""
        else:
            title, content = extract_html_content(raw_body)
            if len(content) > max_chars:
                content = content[:max_chars].rsplit(" ", 1)[0] + " …"

        payload = {
            "status": "ok",
            "url": url,
            "final_url": final_url,
            "title": title,
            "content": content
        }
        return payload
    except Exception as exc:
        logger.exception("Failed to process fetched URL: %s", url)
        return {
            "status": "error",
            "url": url,
            "error": f"Failed to process response: {exc}"
        }


web_fetch_tool = Tool(
    name="web_fetch",
    description="Ruft eine URL ab und extrahiert den lesbaren Webseiteninhalt für Research-Aufgaben.",
    parameters=[
        ToolParameter(
            name="url",
            type="string",
            required=True,
            description="Die abzurufende URL"
        ),
        ToolParameter(
            name="timeout",
            type="integer",
            required=False,
            description="Timeout in Sekunden",
            default=20
        ),
        ToolParameter(
            name="max_chars",
            type="integer",
            required=False,
            description="Maximale Anzahl extrahierter Zeichen",
            default=12000
        )
    ],
    execute_fn=fetch_url,
    permission="network",
    requires_confirmation=False,
    accepts_scalar=False,
)
