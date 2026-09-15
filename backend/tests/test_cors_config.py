from app.config import settings


def test_cors_origins_include_vite_frontend() -> None:
    assert "http://localhost:3000" in settings.cors_origins
    assert "http://127.0.0.1:3000" in settings.cors_origins
    assert "http://localhost:5173" in settings.cors_origins
    assert "http://127.0.0.1:5173" in settings.cors_origins
    assert "*" not in settings.cors_origins
