import unittest

from hiddifypanel.hutils.user_html import clean_user_html


class UserHtmlTest(unittest.TestCase):
    def test_html5_layout_and_inline_styles_stay(self):
        html = (
            '<div align="center" dir="rtl" style="display: flex; gap: 8px; padding: 12px; border-radius: 12px; '
            'background: linear-gradient(90deg, #4f46e5, #06b6d4); color: #fff">'
            '<section><h5>Support</h5><p style="text-align: center">24/7</p></section>'
            '<details open><summary>FAQ</summary><table border="1"><tr><td colspan="2">x</td></tr></table></details>'
            '<font color="red" size="3">!</font><img src="https://example.com/a.png" alt="a" width="32"></div>'
        )
        self.assertEqual(clean_user_html(html), html.replace("<tr>", "<tbody><tr>").replace("</table>", "</tbody></table>"))

    def test_scripts_and_handlers_go(self):
        out = clean_user_html('<div onclick="alert(1)">a<script>alert(1)</script><style>body{display:none}</style></div><iframe src="https://example.com"></iframe>')
        self.assertNotIn("onclick", out)
        self.assertNotIn("<script", out)
        self.assertNotIn("<style", out)
        self.assertNotIn("<iframe", out)
        self.assertEqual(out, "<div>a</div>")

    def test_links(self):
        self.assertIn('href="tg://resolve?domain=x"', clean_user_html('<a href="tg://resolve?domain=x">t</a>'))
        self.assertIn('href="https://t.me/x"', clean_user_html('<a href="https://t.me/x" target="_blank">t</a>'))
        self.assertNotIn("javascript", clean_user_html('<a href="javascript:alert(1)">x</a>'))
        self.assertNotIn("data:", clean_user_html('<img src="data:text/html,x">'))

    def test_css_cannot_load_or_cover_the_page(self):
        out = clean_user_html('<div style="position: fixed; inset: 0; z-index: 9; background: url(https://example.com/t.png); background-image: u\\rl(x); color: red">x</div>')
        self.assertEqual(out, '<div style="color: red">x</div>')

    def test_logical_properties(self):
        html = '<ul style="list-style: disc; padding-inline-start: 1.5em"><li>a</li></ul><blockquote style="border-inline-start: 4px solid #455fe9; margin-inline-end: 8px">q</blockquote>'
        self.assertEqual(clean_user_html(html), html)

    def test_empty(self):
        self.assertEqual(clean_user_html(None), "")
        self.assertEqual(clean_user_html("plain <b>text</b>"), "plain <b>text</b>")


if __name__ == "__main__":
    unittest.main()
