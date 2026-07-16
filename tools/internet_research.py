import gzip
import html
import json
import math
import re
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
GLOSSARY_DB_PATH = ROOT_DIR / "web_glossary.db"
DOWNLOAD_DIR = ROOT_DIR / "workspace" / "downloads"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)
DEFAULT_TIMEOUT = 20
DEFAULT_MAX_RESULTS = 5
DEFAULT_MAX_CHARS = 12000
MAX_GLOSSARY_PAGES = 1000

STOPWORDS = {
    "and", "the", "for", "with", "that", "this", "from", "was", "are",
    "you", "your", "they", "their", "have", "has", "not", "but", "can",
    "will", "about", "into", "what", "when", "where", "who", "why",
    "wie", "und", "der", "die", "das", "mit", "für", "von", "den",
    "dem", "des", "ein", "eine", "einer", "einem", "auf", "im", "in",
    "zu", "ist", "sind", "war", "waren", "nicht", "oder", "auch",
    "dass", "wie", "was", "wer", "wo", "wann", "warum", "ohne"
}


class VisibleTextParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.parts = []
        self.title_parts = []
        self.heading_count = 0
        self.link_count = 0
        self._skip_depth = 0
        self._in_title = False


    def handle_starttag(self, tag, attrs):
        tag = tag.lower()

        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return

        if self._skip_depth:
            return

        if tag == "title":
            self._in_title = True
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.heading_count += 1
            self.parts.append("\n")
        elif tag == "a":
            self.link_count += 1
        elif tag in {"p", "div", "li", "section", "article", "br", "tr", "table", "header", "footer", "pre", "blockquote"}:
            self.parts.append("\n")


    def handle_endtag(self, tag):
        tag = tag.lower()

        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
            return

        if self._skip_depth:
            return

        if tag == "title":
            self._in_title = False
        elif tag in {"p", "div", "li", "section", "article", "pre", "blockquote", "tr", "table", "header", "footer"}:
            self.parts.append("\n")


    def handle_data(self, data):
        if self._skip_depth:
            return

        text = clean_whitespace(html.unescape(data))
        if not text:
            return

        if self._in_title:
            self.title_parts.append(text)

        self.parts.append(text)


    def get_title(self):
        return clean_whitespace(" ".join(self.title_parts))


    def get_text(self):
        return clean_whitespace(" ".join(self.parts))


class ResearchGlossary:

    def __init__(self, db_path=GLOSSARY_DB_PATH):
        self.connection = sqlite3.connect(str(db_path))
        self.create_tables()


    def create_tables(self):
        cursor = self.connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pages (
                url TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                title TEXT,
                summary TEXT,
                score REAL NOT NULL,
                word_count INTEGER NOT NULL,
                keywords TEXT,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS domains (
                domain TEXT PRIMARY KEY,
                score REAL NOT NULL,
                page_count INTEGER NOT NULL,
                last_title TEXT,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        self.connection.commit()


    def _page_count(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM pages")
        row = cursor.fetchone()
        return row[0] if row else 0


    def _prune_pages(self):
        overflow = self._page_count() - MAX_GLOSSARY_PAGES
        if overflow <= 0:
            return

        cursor = self.connection.cursor()
        cursor.execute(
            """
            DELETE FROM pages
            WHERE url IN (
                SELECT url
                FROM pages
                ORDER BY score ASC, last_seen ASC, created_at ASC
                LIMIT ?
            )
            """,
            (overflow,)
        )
        self.connection.commit()


    def _score_page(self, text, heading_count=0, link_count=0):
        words = tokenize(text)
        word_count = len(words)

        if not word_count:
            return 0.05

        unique_ratio = len(set(words)) / max(word_count, 1)
        length_score = min(word_count / 800.0, 1.0)
        heading_score = min(heading_count / 6.0, 1.0)
        link_density = link_count / max(word_count, 1)
        link_penalty = min(link_density * 3.0, 0.5)

        score = (
            0.12
            + (0.48 * length_score)
            + (0.18 * unique_ratio)
            + (0.14 * heading_score)
            + (0.08 * min(math.log1p(word_count) / math.log1p(2500), 1.0))
            - link_penalty
        )

        return max(0.05, min(score, 0.99))


    def _summary(self, text, max_sentences=3):
        cleaned = clean_whitespace(text)
        if not cleaned:
            return ""

        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        summary = " ".join(sentences[:max_sentences]).strip()
        if summary:
            return summary[:1000]
        return cleaned[:1000]


    def _keywords(self, text, limit=12):
        words = [
            word
            for word in tokenize(text)
            if word not in STOPWORDS and len(word) > 2
        ]

        if not words:
            return []

        counts = Counter(words)
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return [word for word, _ in ranked[:limit]]


    def _upsert_domain(self, domain, page_score, title):
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT score, page_count FROM domains WHERE domain = ?",
            (domain,)
        )
        row = cursor.fetchone()

        if row:
            existing_score, page_count = row
            new_score = (existing_score * 0.85) + (page_score * 0.15)
            cursor.execute(
                """
                UPDATE domains
                SET score = ?,
                    page_count = ?,
                    last_title = ?,
                    last_seen = CURRENT_TIMESTAMP
                WHERE domain = ?
                """,
                (
                    new_score,
                    page_count + 1,
                    title,
                    domain
                )
            )
        else:
            cursor.execute(
                """
                INSERT INTO domains (domain, score, page_count, last_title)
                VALUES (?, ?, ?, ?)
                """,
                (
                    domain,
                    page_score,
                    1,
                    title
                )
            )


    def update_from_page(self, url, title, text, heading_count=0, link_count=0):
        parsed = urllib.parse.urlsplit(url)
        domain = parsed.netloc.lower()
        if not domain:
            return None

        score = self._score_page(text, heading_count=heading_count, link_count=link_count)
        summary = self._summary(text)
        keywords = self._keywords(text)
        word_count = len(tokenize(text))

        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT INTO pages (url, domain, title, summary, score, word_count, keywords, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(url) DO UPDATE SET
                domain = excluded.domain,
                title = excluded.title,
                summary = excluded.summary,
                score = excluded.score,
                word_count = excluded.word_count,
                keywords = excluded.keywords,
                last_seen = CURRENT_TIMESTAMP
            """,
            (
                url,
                domain,
                title[:300] if title else None,
                summary,
                score,
                word_count,
                json.dumps(keywords, ensure_ascii=False)
            )
        )

        self._upsert_domain(domain, score, title[:300] if title else None)
        self.connection.commit()
        self._prune_pages()

        return {
            "domain": domain,
            "score": score,
            "summary": summary,
            "keywords": keywords,
            "word_count": word_count
        }


    def get_domain_score(self, domain):
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT score FROM domains WHERE domain = ?",
            (domain.lower(),)
        )
        row = cursor.fetchone()
        return row[0] if row else 0.0


    def rank_results(self, results, query):
        query_terms = set(tokenize(query))
        ranked = []

        for index, result in enumerate(results):
            domain = urllib.parse.urlsplit(result["url"]).netloc.lower()
            domain_score = self.get_domain_score(domain)
            title_tokens = set(tokenize(result.get("title", "")))
            snippet_tokens = set(tokenize(result.get("snippet", "")))
            overlap = len(query_terms & (title_tokens | snippet_tokens))
            overlap_score = min(overlap / max(len(query_terms), 1), 1.0)
            positional_score = 1.0 / (index + 1)

            final_score = (
                positional_score * 0.55
                + domain_score * 0.3
                + overlap_score * 0.15
            )

            ranked.append(
                {
                    **result,
                    "domain": domain,
                    "glossary_score": round(domain_score, 4),
                    "query_overlap": round(overlap_score, 4),
                    "rank_score": round(final_score, 4)
                }
            )

        ranked.sort(key=lambda item: item["rank_score"], reverse=True)
        return ranked


    def close(self):
        self.connection.close()


class DuckDuckGoParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.results = []
        self._current = None
        self._capture_title = False
        self._capture_snippet = False
        self._title_chunks = []
        self._snippet_chunks = []


    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        class_name = attrs.get("class", "")
        tag = tag.lower()

        if tag == "a" and "result__a" in class_name:
            self._current = {
                "url": attrs.get("href", ""),
                "title": "",
                "snippet": ""
            }
            self._capture_title = True
            self._title_chunks = []
            self._snippet_chunks = []
        elif self._current and "result__snippet" in class_name:
            self._capture_snippet = True
            self._snippet_chunks = []


    def handle_endtag(self, tag):
        tag = tag.lower()

        if tag == "a" and self._capture_title:
            self._capture_title = False
            if self._current is not None:
                self._current["title"] = clean_whitespace(" ".join(self._title_chunks))
        elif tag in {"a", "div", "span"} and self._capture_snippet:
            self._capture_snippet = False
            if self._current is not None:
                snippet = clean_whitespace(" ".join(self._snippet_chunks))
                if snippet:
                    self._current["snippet"] = snippet
        elif tag == "div" and self._current is not None and not self._capture_snippet and not self._capture_title:
            if self._current.get("title"):
                self.results.append(self._current)
                self._current = None


    def handle_data(self, data):
        text = clean_whitespace(html.unescape(data))
        if not text:
            return

        if self._capture_title:
            self._title_chunks.append(text)
        elif self._capture_snippet:
            self._snippet_chunks.append(text)


    def close(self):
        super().close()
        if self._current and self._current.get("title"):
            self.results.append(self._current)
            self._current = None
        return self.results


class FetchResult:

    def __init__(self, url, content_type, final_url, text=None, raw_bytes=None, title=None, requires_confirmation=False, reason=None, filename=None):
        self.url = url
        self.content_type = content_type
        self.final_url = final_url
        self.text = text
        self.raw_bytes = raw_bytes
        self.title = title
        self.requires_confirmation = requires_confirmation
        self.reason = reason
        self.filename = filename


    def to_text(self):
        if self.requires_confirmation:
            payload = {
                "status": "confirmation_required",
                "url": self.url,
                "final_url": self.final_url,
                "content_type": self.content_type,
                "reason": self.reason,
                "filename": self.filename
            }
            return json.dumps(payload, ensure_ascii=False, indent=2)

        payload = {
            "status": "ok",
            "url": self.url,
            "final_url": self.final_url,
            "content_type": self.content_type,
            "title": self.title,
            "text": self.text
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)



def clean_whitespace(text):
    return " ".join(str(text).split())



def tokenize(text):
    return [
        word.lower()
        for word in re.findall(r"[\wÄÖÜäöüß]+", str(text), flags=re.UNICODE)
        if word
    ]



def _prepare_request(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
    )
    return request



def _decode_response_body(response):
    body = response.read()
    encoding = response.headers.get_content_charset() or "utf-8"
    if response.headers.get("Content-Encoding", "").lower() == "gzip":
        body = gzip.decompress(body)
    try:
        return body.decode(encoding, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")



def _extract_url_redirect(href):
    parsed = urllib.parse.urlsplit(href)
    query = urllib.parse.parse_qs(parsed.query)
    for key in ("uddg", "u", "url"):
        if key in query and query[key]:
            return urllib.parse.unquote(query[key][0])
    if href.startswith("//"):
        return "https:" + href
    return urllib.parse.urljoin("https://duckduckgo.com", href)



def _parse_duckduckgo_results(html_text):
    parser = DuckDuckGoParser()
    parser.feed(html_text)
    results = parser.close()

    cleaned = []
    for result in results:
        url = _extract_url_redirect(result["url"])
        if not url.startswith(("http://", "https://")):
            continue
        cleaned.append(
            {
                "title": result.get("title", ""),
                "url": url,
                "snippet": result.get("snippet", "")
            }
        )
    return cleaned



def _fetch_url(url, timeout=DEFAULT_TIMEOUT):
    request = _prepare_request(url)
    response = urllib.request.urlopen(request, timeout=timeout)
    content_type = response.headers.get_content_type()
    full_content_type = response.headers.get("Content-Type", content_type)
    final_url = response.geturl()
    return response, content_type, full_content_type, final_url



def _is_text_content(content_type, full_content_type):
    value = f"{content_type}; {full_content_type}".lower()
    return any(
        marker in value
        for marker in (
            "text/html",
            "text/plain",
            "application/xhtml+xml",
            "application/xml",
            "text/xml",
            "image/svg+xml"
        )
    )



def _attachment_requested(headers):
    disposition = headers.get("Content-Disposition", "")
    return "attachment" in disposition.lower()



def _filename_from_response(url, headers):
    disposition = headers.get("Content-Disposition", "")
    match = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', disposition, re.I)
    if match:
        return clean_whitespace(urllib.parse.unquote(match.group(1))).replace("/", "_")

    parsed = urllib.parse.urlsplit(url)
    name = Path(parsed.path).name or "downloaded-file"
    if "." not in name:
        content_type = headers.get_content_type()
        extension = {
            "application/pdf": ".pdf",
            "application/zip": ".zip",
            "application/json": ".json",
            "text/csv": ".csv",
            "text/plain": ".txt"
        }.get(content_type, "")
        name = f"{name}{extension}"
    return name



def _save_binary(url, response):
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = _filename_from_response(url, response.headers)
    target = DOWNLOAD_DIR / filename
    data = response.read()
    target.write_bytes(data)
    return target



def web_search(data):
    if isinstance(data, str):
        data = {"query": data}

    query = clean_whitespace(data.get("query", ""))
    if not query:
        return "Fehler: 'query' ist erforderlich."

    max_results = int(data.get("max_results", DEFAULT_MAX_RESULTS) or DEFAULT_MAX_RESULTS)
    max_results = max(1, min(max_results, 10))

    search_url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote_plus(query)

    try:
        response, _, _, _ = _fetch_url(search_url)
        html_text = _decode_response_body(response)
    except Exception as exc:
        return f"Fehler bei der Websuche: {exc}"

    parsed_results = _parse_duckduckgo_results(html_text)
    if not parsed_results:
        return "Keine Suchergebnisse gefunden."

    glossary = ResearchGlossary()
    ranked = glossary.rank_results(parsed_results[: max_results * 3], query)
    glossary.close()

    output = {
        "query": query,
        "results": ranked[:max_results],
        "note": "Ergebnisse werden intern mit einem dynamischen Glossar informativer Websites priorisiert. Das Glossar ist auf 1000 Seiten begrenzt und wird laufend aktualisiert."
    }

    return json.dumps(output, ensure_ascii=False, indent=2)



def read_url(data):
    if isinstance(data, str):
        data = {"url": data}

    url = clean_whitespace(data.get("url", ""))
    if not url:
        return "Fehler: 'url' ist erforderlich."

    max_chars = int(data.get("max_chars", DEFAULT_MAX_CHARS) or DEFAULT_MAX_CHARS)
    max_chars = max(1000, min(max_chars, 50000))
    confirm_download = bool(data.get("confirm_download", False))

    if not url.startswith(("http://", "https://")):
        return "Fehler: Es werden nur http:// und https:// URLs unterstützt."

    try:
        response, content_type, full_content_type, final_url = _fetch_url(url)
    except Exception as exc:
        return f"Fehler beim Öffnen der URL: {exc}"

    headers = response.headers
    attachment = _attachment_requested(headers)
    text_like = _is_text_content(content_type, full_content_type) and not attachment

    if not text_like:
        if not confirm_download:
            payload = {
                "status": "confirmation_required",
                "url": url,
                "final_url": final_url,
                "content_type": full_content_type,
                "reason": "Diese URL liefert keinen Textinhalt oder ist als Download markiert. Ich lade oder öffne solche Inhalte nicht ohne Bestätigung.",
                "filename": _filename_from_response(final_url, headers)
            }
            return json.dumps(payload, ensure_ascii=False, indent=2)

        saved_path = _save_binary(final_url, response)
        payload = {
            "status": "downloaded",
            "url": url,
            "final_url": final_url,
            "content_type": full_content_type,
            "saved_to": str(saved_path),
            "note": "Die Datei wurde nur nach Bestätigung gespeichert und nicht automatisch geöffnet."
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    body = _decode_response_body(response)
    parser = VisibleTextParser()
    parser.feed(body)
    parser.close()

    title = parser.get_title() or ""
    text = parser.get_text() or clean_whitespace(body)
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + " …"

    glossary = ResearchGlossary()
    glossary.update_from_page(
        final_url,
        title or final_url,
        text,
        heading_count=parser.heading_count,
        link_count=parser.link_count
    )
    glossary.close()

    payload = {
        "status": "ok",
        "url": url,
        "final_url": final_url,
        "content_type": full_content_type,
        "title": title,
        "text": text
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
