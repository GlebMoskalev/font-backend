from sqlalchemy import func, select

from app.models import Font
from tests.conftest import to_flavor


async def count_rows(client) -> int:
    async with client.app.state.font_service.sessions() as s:
        return await s.scalar(select(func.count()).select_from(Font))


def upload(client, name, data, content_type="application/octet-stream"):
    return client.post("/api/fonts", files={"file": (name, data, content_type)})


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_upload_ttf_and_get(client, ttf_bytes):
    resp = upload(client, "MyFont.ttf", ttf_bytes)
    assert resp.status_code == 201, resp.text
    meta = resp.json()
    assert meta["format"] == "ttf"
    assert meta["size"] == len(ttf_bytes)
    assert meta["original_name"] == "MyFont.ttf"

    got = client.get(f"/api/fonts/{meta['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == meta["id"]

    file = client.get(f"/api/fonts/{meta['id']}/file")
    assert file.status_code == 200
    assert file.content == ttf_bytes
    assert file.headers["content-type"] == "font/ttf"


def test_upload_woff_and_woff2(client, ttf_bytes):
    for flavor in ("woff", "woff2"):
        resp = upload(client, f"font.{flavor}", to_flavor(ttf_bytes, flavor))
        assert resp.status_code == 201, resp.text
        assert resp.json()["format"] == flavor


def test_format_detected_by_content_not_extension(client, ttf_bytes):
    resp = upload(client, "font.otf", ttf_bytes)
    assert resp.status_code == 201
    assert resp.json()["format"] == "ttf"


def test_renamed_png_rejected(client):
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    resp = upload(client, "fake.ttf", png)
    assert resp.status_code == 415
    assert resp.json()["code"] == "unsupported_format"


def test_wrong_extension_rejected(client, ttf_bytes):
    resp = upload(client, "font.exe", ttf_bytes)
    assert resp.status_code == 415
    assert resp.json()["code"] == "unsupported_extension"


def test_truncated_font_rejected(client, ttf_bytes):
    resp = upload(client, "broken.ttf", ttf_bytes[:40])
    assert resp.status_code == 400
    assert resp.json()["code"] == "corrupted_font"


def test_empty_file_rejected(client):
    resp = upload(client, "empty.ttf", b"")
    assert resp.status_code == 400
    assert resp.json()["code"] == "empty_file"


def test_too_large_rejected(make_client, ttf_bytes):
    client = make_client(max_upload_bytes=100)
    resp = upload(client, "big.ttf", ttf_bytes)
    assert resp.status_code == 413
    assert resp.json()["code"] == "file_too_large"


def test_path_in_filename_stripped(client, ttf_bytes):
    resp = upload(client, "../../etc/evil.ttf", ttf_bytes)
    assert resp.status_code == 201
    assert resp.json()["original_name"] == "evil.ttf"


def test_delete(client, ttf_bytes):
    font_id = upload(client, "a.ttf", ttf_bytes).json()["id"]
    assert client.delete(f"/api/fonts/{font_id}").status_code == 204
    assert client.get(f"/api/fonts/{font_id}").status_code == 404
    assert client.delete(f"/api/fonts/{font_id}").status_code == 404


def test_unknown_and_invalid_id(client):
    assert client.get("/api/fonts/00000000-0000-0000-0000-000000000000").status_code == 404
    assert client.get("/api/fonts/not-a-uuid").status_code == 422


def test_delete_removes_file(client, ttf_bytes):
    font_id = upload(client, "a.ttf", ttf_bytes).json()["id"]
    assert client.portal.call(count_rows, client) == 1
    client.delete(f"/api/fonts/{font_id}")
    assert client.portal.call(count_rows, client) == 0


def test_cyrillic_filename_download(client, ttf_bytes):
    font_id = upload(client, "Мой шрифт.ttf", ttf_bytes).json()["id"]
    resp = client.get(f"/api/fonts/{font_id}/file")
    assert resp.status_code == 200
    assert "filename*=utf-8''" in resp.headers["content-disposition"]
