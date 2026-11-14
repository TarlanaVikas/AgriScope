import re

from agriscope import create_app
from agriscope.config import Config

from conftest import FakeDetector


def test_pages_render_and_are_branded(client):
    for path in ["/", "/detect", "/about"]:
        r = client.get(path)
        html = r.get_data(as_text=True)
        assert r.status_code == 200, path
        assert "AgriScope" in html
        assert not re.search("|".join(["plant" + "sense", "anand" + "raja"]), html, re.I)  # no legacy branding or author credit


def test_404_page_is_html_and_branded(client):
    r = client.get("/definitely-missing")
    assert r.status_code == 404 and "text/html" in r.content_type and "AgriScope" in r.get_data(as_text=True)


def test_legacy_upload_redirects(client):
    r = client.get("/upload")
    assert r.status_code == 301 and r.headers["Location"].endswith("/detect")


def test_detect_page_warns_when_model_unavailable():
    app = create_app(Config(preload_model=False), detector=FakeDetector(ready=False))
    html = app.test_client().get("/detect").get_data(as_text=True)
    assert "Detection is unavailable" in html and 'data-ready="false"' in html


def test_security_headers(client):
    h = client.get("/").headers
    assert h["X-Content-Type-Options"] == "nosniff" and "frame-ancestors 'none'" in h["Content-Security-Policy"]


def test_no_inline_scripts_so_csp_holds(client):
    for path in ["/", "/detect", "/about"]:
        assert not re.search(r"<script(?![^>]*\bsrc=)", client.get(path).get_data(as_text=True))


def test_static_assets_referenced_exist(client):
    html = client.get("/detect").get_data(as_text=True)
    for url in set(re.findall(r'(?:href|src)="(/static/[^"?]+)', html)):
        assert client.get(url).status_code == 200, url
