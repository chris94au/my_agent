import html
import logging
import re
from html.parser import HTMLParser


logger = logging.getLogger(__name__)


SKIP_TAGS = {
    "script",
    "style",
    "noscript",
    "nav",
    "aside",
    "footer",
    "form",
    "iframe",
    "template",
    "svg",
}

BLOCK_TAGS = {
    "article",
    "section",
    "main",
    "header",
    "div",
    "p",
    "li",
    "ul",
    "ol",
    "table",
    "tr",
    "td",
    "th",
    "blockquote",
    "pre",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "br",
}

AD_PATTERNS = re.compile(r"\b(ad|ads|advert|advertisement|sponsor|sponsored|promo|banner|cookie|newsletter)\b", re.I)


def clean_whitespace(text):
    return " ".join(str(text).split())


class ResearchHTMLParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self._in_title = False
        self._heading_level = None
        self._title_parts = []
        self._heading_candidate_parts = []
        self._text_parts = []
        self._title_from_meta = None
        self._first_heading = None


    def _is_boilerplate(self, attrs):
        attr_map = {key.lower(): value for key, value in attrs}
        combined = " ".join(
            [str(attr_map.get("id", "")), str(attr_map.get("class", ""))]
        )
        return bool(combined and AD_PATTERNS.search(combined))


    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in SKIP_TAGS or self._is_boilerplate(attrs):
            self._skip_depth += 1
            return

        if self._skip_depth:
            return

        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            attr_map = {key.lower(): value for key, value in attrs}
            if str(attr_map.get("property", "")).lower() in {"og:title", "twitter:title"}:
                content = clean_whitespace(html.unescape(attr_map.get("content", "")))
                if content:
                    self._title_from_meta = content
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._heading_level = tag
            self._heading_candidate_parts = []
            self._text_parts.append("\n")
        elif tag in BLOCK_TAGS:
            self._text_parts.append("\n")


    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
            return

        if self._skip_depth:
            return

        if tag == "title":
            self._in_title = False
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            heading = clean_whitespace(" ".join(self._heading_candidate_parts))
            if heading and not self._first_heading:
                self._first_heading = heading
            self._heading_level = None
            self._heading_candidate_parts = []
            self._text_parts.append("\n")
        elif tag in BLOCK_TAGS:
            self._text_parts.append("\n")


    def handle_data(self, data):
        if self._skip_depth:
            return

        text = clean_whitespace(html.unescape(data))
        if not text:
            return

        if self._in_title:
            self._title_parts.append(text)
        elif self._heading_level:
            self._heading_candidate_parts.append(text)

        self._text_parts.append(text)


    def get_title(self):
        if self._title_parts:
            return clean_whitespace(" ".join(self._title_parts))
        if self._title_from_meta:
            return self._title_from_meta
        return self._first_heading or ""


    def get_text(self):
        return clean_whitespace(" ".join(self._text_parts))



def parse_html_document(html_text):
    if html_text is None:
        return {"title": "", "content": ""}

    parser = ResearchHTMLParser()
    try:
        parser.feed(str(html_text))
        parser.close()
    except Exception as exc:
        logger.warning("HTML parsing fallback due to error: %s", exc)
        text = clean_whitespace(html.unescape(str(html_text)))
        return {
            "title": "",
            "content": text
        }

    title = parser.get_title()
    content = parser.get_text()

    if not content:
        content = clean_whitespace(html.unescape(str(html_text)))

    content = re.sub(r"\s+", " ", content).strip()
    title = re.sub(r"\s+", " ", title).strip()

    return {
        "title": title,
        "content": content
    }



def extract_html_content(html_text):
    parsed = parse_html_document(html_text)
    return parsed["title"], parsed["content"]
