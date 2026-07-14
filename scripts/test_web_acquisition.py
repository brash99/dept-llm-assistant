import threading
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)

import pytest

from app.acquisition import (
    SourceAuthority,
    WebAcquisitionService,
)


class LocalHTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            content = (
                b"<!doctype html>"
                b"<html><head>"
                b"<title>Christopher Newport University</title>"
                b"</head><body>Home page</body></html>"
            )
            content_type = "text/html; charset=utf-8"

        elif self.path == "/report.pdf":
            content = b"%PDF-1.4\nfake test pdf\n"
            content_type = "application/pdf"

        else:
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        pass


@pytest.fixture
def local_server():
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        LocalHTTPHandler,
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


def test_html_url_produces_source_document(
    tmp_path,
    local_server,
):
    service = WebAcquisitionService(tmp_path)

    document = service.acquire(
        url=f"{local_server}/",
        source_organization=(
            "Christopher Newport University"
        ),
        authority=(
            SourceAuthority.INSTITUTIONAL_PRIMARY
        ),
    )

    assert (
        document.title
        == "Christopher Newport University"
    )
    assert (
        document.source_organization
        == "Christopher Newport University"
    )
    assert document.media_type == "text/html"
    assert document.source_url == f"{local_server}/"
    assert document.relative_path.endswith(
        "/index.html"
    )

    saved_path = tmp_path / document.relative_path
    assert saved_path.exists()
    assert b"Home page" in saved_path.read_bytes()


def test_pdf_url_preserves_pdf_bytes(
    tmp_path,
    local_server,
):
    service = WebAcquisitionService(tmp_path)

    document = service.acquire(
        url=f"{local_server}/report.pdf",
        source_organization="CNU Institutional Research",
        authority=(
            SourceAuthority.INSTITUTIONAL_PRIMARY
        ),
        title="Institutional Research Report",
    )

    assert document.title == "Institutional Research Report"
    assert document.media_type == "application/pdf"
    assert document.relative_path.endswith(
        "/report.pdf"
    )

    saved_path = tmp_path / document.relative_path
    assert saved_path.read_bytes().startswith(b"%PDF")


def test_same_response_produces_same_content_identity(
    tmp_path,
    local_server,
):
    service = WebAcquisitionService(tmp_path)

    first = service.acquire(
        url=f"{local_server}/",
        source_organization="CNU",
        authority=(
            SourceAuthority.INSTITUTIONAL_PRIMARY
        ),
    )

    second = service.acquire(
        url=f"{local_server}/",
        source_organization="CNU",
        authority=(
            SourceAuthority.INSTITUTIONAL_PRIMARY
        ),
    )

    assert first.id == second.id
    assert first.content_hash == second.content_hash
    assert first.relative_path == second.relative_path


def test_query_string_gets_stable_path_suffix():
    first = WebAcquisitionService.storage_path_for_url(
        "https://example.edu/report?year=2026&type=annual",
        media_type="text/html",
    )

    second = WebAcquisitionService.storage_path_for_url(
        "https://example.edu/report?type=annual&year=2026",
        media_type="text/html",
    )

    assert first == second
    assert "__query_" in first.name
    assert first.suffix == ".html"


def test_non_http_url_is_rejected():
    with pytest.raises(
        ValueError,
        match="Unsupported web URL scheme",
    ):
        WebAcquisitionService.storage_path_for_url(
            "file:///tmp/example.html",
            media_type="text/html",
        )
