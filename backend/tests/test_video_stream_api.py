from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_video_stream_returns_file_for_uploaded_video(monkeypatch, tmp_path: Path) -> None:
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    video_path = uploads_dir / "stream_test.mp4"
    video_path.write_bytes(b"fake mp4 bytes")

    monkeypatch.setattr("app.services.video_service.get_upload_directory", lambda: uploads_dir)
    client = TestClient(app)

    response = client.get("/api/videos/stream_test/stream")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("video/")
    assert response.content == b"fake mp4 bytes"


def test_video_stream_missing_video_returns_404(monkeypatch, tmp_path: Path) -> None:
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("app.services.video_service.get_upload_directory", lambda: uploads_dir)
    client = TestClient(app)

    response = client.get("/api/videos/missing_video/stream")

    assert response.status_code == 404
    assert "detail" in response.json()
