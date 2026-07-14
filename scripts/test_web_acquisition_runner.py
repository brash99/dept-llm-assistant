import threading
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)

import pytest

from app.acquisition import (
    AcquisitionManifest,
    SourceAuthority,
    WebAcquisitionRunner,
    WebAcquisitionService,
)


class CrawlHTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        pages = {
            "/": (
                "text/html; charset=utf-8",
                b"""
                <html>
                  <head><title>Home</title></head>
                  <body>
                    <a href="/academics/">Academics</a>
                    <a href="/about/">About</a>
                    <a href="/private/">Private</a>
                    <a href="https://example.org/offsite">
                      Offsite
                    </a>
                  </body>
                </html>
                """,
            ),
            "/academics/": (
                "text/html; charset=utf-8",
                b"""
                <html>
                  <head><title>Academics</title></head>
                  <body>
                    <a href="/academics/programs/">
                      Programs
                    </a>
                    <a href="/">Home</a>
                  </body>
                </html>
                """,
            ),
            "/academics/programs/": (
                "text/html; charset=utf-8",
                b"""
                <html>
                  <head><title>Programs</title></head>
                  <body>Programs page</body>
                </html>
                """,
            ),
            "/about/": (
                "text/html; charset=utf-8",
                b"""
                <html>
                  <head><title>About</title></head>
                  <body>About page</body>
                </html>
                """,
            ),
            "/private/": (
                "text/html; charset=utf-8",
                b"""
                <html>
                  <head><title>Private</title></head>
                  <body>Private page</body>
                </html>
                """,
            ),
            "/robots.txt": (
                "text/plain; charset=utf-8",
                b"User-agent: *\nDisallow: /private/\n",
            ),
        }

        response = pages.get(self.path)

        if response is None:
            self.send_response(404)
            self.end_headers()
            return

        content_type, content = response

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        pass


@pytest.fixture
def crawl_server():
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        CrawlHTTPHandler,
    )

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()

    host, port = server.server_address

    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        thread.join()


def build_runner(tmp_path):
    storage_root = tmp_path / "raw_web"
    manifest_path = tmp_path / "manifest.jsonl"

    web_service = WebAcquisitionService(
        storage_root,
        timeout_seconds=5.0,
    )

    manifest = AcquisitionManifest(manifest_path)

    runner = WebAcquisitionRunner(
        web_service=web_service,
        manifest=manifest,
        request_delay_seconds=0.0,
    )

    return manifest, runner


def test_bounded_same_site_crawl(
    tmp_path,
    crawl_server,
):
    manifest, runner = build_runner(tmp_path)

    report = runner.run(
        seed_url=f"{crawl_server}/",
        source_organization="Test University",
        authority=(
            SourceAuthority.INSTITUTIONAL_PRIMARY
        ),
        max_pages=10,
        max_depth=2,
    )

    assert report.pages_acquired == 4
    assert report.new_documents == 4
    assert report.robots_denied == 1
    assert report.offsite_links_skipped == 1
    assert report.failed_pages == 0
    assert len(manifest.read_all()) == 4


def test_second_crawl_is_unchanged(
    tmp_path,
    crawl_server,
):
    _, runner = build_runner(tmp_path)

    first = runner.run(
        seed_url=f"{crawl_server}/",
        source_organization="Test University",
        authority=(
            SourceAuthority.INSTITUTIONAL_PRIMARY
        ),
        max_pages=10,
        max_depth=2,
    )

    second = runner.run(
        seed_url=f"{crawl_server}/",
        source_organization="Test University",
        authority=(
            SourceAuthority.INSTITUTIONAL_PRIMARY
        ),
        max_pages=10,
        max_depth=2,
    )

    assert first.new_documents == 4
    assert second.new_documents == 0
    assert second.unchanged_documents == 4


def test_page_limit_is_enforced(
    tmp_path,
    crawl_server,
):
    _, runner = build_runner(tmp_path)

    report = runner.run(
        seed_url=f"{crawl_server}/",
        source_organization="Test University",
        authority=(
            SourceAuthority.INSTITUTIONAL_PRIMARY
        ),
        max_pages=2,
        max_depth=5,
    )

    assert report.pages_attempted == 2
    assert report.pages_acquired == 2


def test_depth_limit_is_enforced(
    tmp_path,
    crawl_server,
):
    _, runner = build_runner(tmp_path)

    report = runner.run(
        seed_url=f"{crawl_server}/",
        source_organization="Test University",
        authority=(
            SourceAuthority.INSTITUTIONAL_PRIMARY
        ),
        max_pages=10,
        max_depth=0,
    )

    assert report.pages_acquired == 1


def test_url_normalization_removes_fragments():
    normalized = WebAcquisitionRunner.normalize_url(
        "https://Example.edu//academics/?b=2&a=1#section"
    )

    assert normalized == (
        "https://example.edu/academics/?a=1&b=2"
    )


def test_invalid_page_limit_is_rejected(
    tmp_path,
    crawl_server,
):
    _, runner = build_runner(tmp_path)

    with pytest.raises(
        ValueError,
        match="max_pages",
    ):
        runner.run(
            seed_url=f"{crawl_server}/",
            source_organization="Test University",
            authority=(
                SourceAuthority.INSTITUTIONAL_PRIMARY
            ),
            max_pages=0,
        )


def test_allowed_prefix_prevents_scope_escape(
    tmp_path,
    crawl_server,
):
    _, runner = build_runner(tmp_path)

    report = runner.run(
        seed_url=f"{crawl_server}/academics/",
        source_organization="Test University",
        authority=(
            SourceAuthority.INSTITUTIONAL_PRIMARY
        ),
        max_pages=10,
        max_depth=5,
        allowed_prefixes=(
            f"{crawl_server}/academics/",
        ),
    )

    assert report.pages_acquired == 2
