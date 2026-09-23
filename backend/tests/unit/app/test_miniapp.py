from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.http.miniapp import IMMUTABLE, REVALIDATE, mount_miniapp


def _app(tmp_path: Path) -> TestClient:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<div id=root></div>")
    (tmp_path / "assets" / "index-abc.js").write_text("console.log(1)")

    app = FastAPI()

    @app.get("/api/v1/ping")
    async def ping() -> dict[str, bool]:
        return {"ok": True}

    mount_miniapp(app, tmp_path)
    return TestClient(app)


def test_index_is_served_at_root_and_revalidated(tmp_path: Path) -> None:
    response = _app(tmp_path).get("/")

    assert response.status_code == 200
    assert "root" in response.text
    assert response.headers["cache-control"] == REVALIDATE


def test_hashed_assets_are_cached_forever(tmp_path: Path) -> None:
    response = _app(tmp_path).get("/assets/index-abc.js")

    assert response.status_code == 200
    assert response.headers["cache-control"] == IMMUTABLE


def test_api_routes_registered_earlier_win(tmp_path: Path) -> None:
    assert _app(tmp_path).get("/api/v1/ping").json() == {"ok": True}
