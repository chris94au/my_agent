import unittest

from research.html_parser import extract_html_content, parse_html_document


class HtmlParserTests(unittest.TestCase):

    def test_extract_html_content_removes_navigation_and_ads(self):
        html = """
        <html>
          <head><title>Research Example</title></head>
          <body>
            <nav>Menu Home About Contact</nav>
            <header><h1>Ignored Header</h1></header>
            <main>
              <article>
                <h2>Important Article</h2>
                <p>Actual content here.</p>
              </article>
            </main>
            <aside class="advertisement">Buy now</aside>
            <footer>Footer links</footer>
          </body>
        </html>
        """

        title, content = extract_html_content(html)
        self.assertEqual(title, "Research Example")
        self.assertIn("Important Article", content)
        self.assertIn("Actual content here.", content)
        self.assertNotIn("Menu Home About Contact", content)
        self.assertNotIn("Buy now", content)
        self.assertNotIn("Footer links", content)


    def test_parse_html_document_falls_back_to_heading_title(self):
        html = """
        <html>
          <body>
            <h1>Fallback Title</h1>
            <p>Text body.</p>
          </body>
        </html>
        """

        parsed = parse_html_document(html)
        self.assertEqual(parsed["title"], "Fallback Title")
        self.assertIn("Text body.", parsed["content"])


if __name__ == "__main__":
    unittest.main()
