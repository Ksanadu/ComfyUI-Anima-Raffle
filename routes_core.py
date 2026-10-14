import asyncio
import os

from aiohttp import web

from . import artist_data
from .preview_history import PreviewHistory


def register_core_routes(server, require_local_token=None):
    try:
        img_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "js", "images"))
        os.makedirs(img_path, exist_ok=True)
        server.instance.app.router.add_static("/anima/images/", img_path, show_index=False, follow_symlinks=False)
        print(f" [AnimaStyleExplorer] Static route registered: /anima/images/ -> {img_path}")
    except Exception as e:
        print(f" [AnimaStyleExplorer] Static route error: {e}")

    @server.instance.routes.get("/anima/test")
    async def test_route(request):
        return web.json_response({"status": "ok", "message": "Anima routes are active"})

    @server.instance.routes.post("/anima/preview_history/clear")
    async def clear_preview_history(request):
        if require_local_token is not None:
            denied = require_local_token(request)
            if denied is not None:
                return denied
        try:
            counts = await asyncio.to_thread(PreviewHistory.clear_history)
        except OSError as e:
            print(f"[PreviewHistory] Could not clear history: {e}")
            return web.json_response({
                "success": False,
                "error": "Could not clear history. Check folder permissions.",
            }, status=500)
        server.instance.send_sync("raffle.preview_history.cleared", counts)
        return web.json_response({"success": True, **counts})

    @server.instance.routes.get("/anima/artists")
    async def get_artists(request):
        if str(request.query.get("source", "")).strip().lower() == "animadex":
            source_kind = str(request.query.get("kind", "")).strip().lower()
            return web.json_response(artist_data.load_animadex(source_kind))
        return web.json_response(artist_data.load())

    @server.instance.routes.get("/anima/data_stats")
    async def data_stats(request):
        return web.json_response(artist_data.stats())

    @server.instance.routes.get("/anima/random")
    async def get_random(request):
        artist = artist_data.pick_random()
        if not artist:
            return web.json_response({"error": "No artists loaded"}, status=404)
        return web.json_response(artist)

    @server.instance.routes.post("/anima/update")
    async def update_artists(request):
        if require_local_token is not None:
            denied = require_local_token(request)
            if denied is not None:
                return denied

        try:
            body = await request.json()
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}

        include_animadex = str(request.query.get("animadex", "")).strip().lower() in ("1", "true", "yes", "on")
        include_animadex = include_animadex or bool(body.get("animadex"))

        raw_modes = request.query.get("animadex_modes") or body.get("animadexModes") or ""
        animadex_modes = [
            part.strip().lower()
            for part in str(raw_modes).split(",")
            if part.strip()
        ] or None

        try:
            max_pages = int(request.query.get("animadex_max_pages") or body.get("animadexMaxPages") or 0)
        except Exception:
            max_pages = 0
        max_pages = max_pages or None

        success = artist_data.download(
            include_animadex=include_animadex,
            animadex_modes=animadex_modes,
            max_pages=max_pages,
        )
        return web.json_response({
            "success": success,
            "includeAnimadex": include_animadex,
            "stats": artist_data.stats(),
        })

    @server.instance.routes.post("/anima/download_images")
    async def download_images(request):
        if require_local_token is not None:
            denied = require_local_token(request)
            if denied is not None:
                return denied
        success = artist_data.start_image_download()
        return web.json_response({"success": success})

    @server.instance.routes.get("/anima/download_status")
    async def download_status(request):
        return web.json_response(artist_data.get_download_status())

