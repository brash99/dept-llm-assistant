import threading
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)

import pytest

from app.acquisition.authority import (
    SourceAuthority,
)
from app.acquisition.observer_v2 import (
    MediaPolicy,
    ObserverV2,
)
from app.acquisition.observers import (
    ObserverAuthorization,
)
from app.acquisition.observer_v2_runner import (
    ObserverV2Runner,
)
from app.acquisition.web import (
    WebAcquisitionService,
)


class ObserverV2HTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            body = b"""
                <html>
                  <head><title>Home</title></head>
                  <body>
                    <a href="/page/">Page</a>
                    <a href="/report.pdf">PDF</a>
                    <a href="/image.jpg">Image</a>
                  </body>
                </html>
            """
            media_type = "text/html"

        elif self.path == "/page/":
            body = b"""
                <html>
                  <head><title>Page</title></head>
                  <body>Institutional page.</body>
                </html>
            """
            media_type = "text/html"

        elif self.path == "/report.pdf":
            body = (
                b"%PDF-1.4\n"
                b"1 0 obj\n"
                b"<<>>\n"
                b"endobj\n"
                b"trailer\n"
                b"<<>>\n"
                b"%%EOF\n"
            )
            media_type = "application/pdf"

        elif self.path == "/robots.txt":
            body = (
                b"User-agent: *\n"
                b"Disallow: /\n"
            )
            media_type = "text/plain"

        else:
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header(
            "Content-Type",
            media_type,
        )
        self.send_header(
            "Content-Length",
            str(len(body)),
        )
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


@pytest.fixture
def test_server():
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        ObserverV2HTTPHandler,
    )

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )

    thread.start()

    host, port = server.server_address

    try:
        yield (
            f"http://{host}:{port}",
            f"{host}:{port}",
        )
    finally:
        server.shutdown()
        thread.join()


def test_runner_acquires_html_and_pdf(
    tmp_path,
    test_server,
):
    base_url, host = test_server

    observer = ObserverV2(
        name="test_observer",
        enabled=True,
        source_organization="Test University",
        authority=(
            SourceAuthority
            .INSTITUTIONAL_PRIMARY
        ),
        purposes=("test",),
        priority_terms=("report",),
        seed_urls=(base_url + "/",),
        allowed_hosts=(host,),
        allowed_prefixes=(base_url + "/",),
        storage_root=tmp_path / "raw",
        manifest_path=tmp_path / "manifest.jsonl",
        budget=3,
        max_depth=2,
        request_delay_seconds=0.0,
        respect_robots=False,
        media_policy=MediaPolicy(
            follow_html=True,
            follow_pdf=True,
        ),
        authorization=ObserverAuthorization(
            mode="institutional_approval",
            approved_by=("Test Provost",),
            scope=(base_url + "/",),
            notes="Offline test authorization.",
        ),
    )

    report = ObserverV2Runner(
        observer
    ).run()

    assert report.observations_acquired == 3
    assert report.media_counts["text/html"] == 2
    assert (
        report.media_counts["application/pdf"]
        == 1
    )

    expected_pdf_path = (
        tmp_path
        / "raw"
        / WebAcquisitionService.storage_path_for_url(
            base_url + "/report.pdf",
            media_type="application/pdf",
        )
    )

    assert expected_pdf_path.exists()
