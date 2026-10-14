import importlib.util
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import Mock, patch

import numpy as np
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
folder_paths = types.ModuleType("folder_paths")
server_module = types.ModuleType("server")
server_module.PromptServer = types.SimpleNamespace(instance=None)
package = types.ModuleType("preview_history_test_package")
package.__path__ = [str(ROOT)]
package.artist_data = types.ModuleType("artist_data")


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {
        "folder_paths": folder_paths, "server": server_module,
        package.__name__: package,
        f"{package.__name__}.preview_history": globals().get("history", module),
    }):
        spec.loader.exec_module(module)
    return module


history = load_module(f"{package.__name__}.preview_history", "preview_history.py")
routes = load_module(f"{package.__name__}.routes_core", "routes_core.py")


class HistoryFixture:
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.history_dir = self.root / "history"
        self.temp_dir = self.root / "temp"
        self.history_dir.mkdir()
        self.temp_dir.mkdir()
        patches = [
            patch.object(history, "DEFAULT_HISTORY_FOLDER", str(self.history_dir)),
            patch.object(history.folder_paths, "get_temp_directory", return_value=str(self.temp_dir), create=True),
            patch.object(history.folder_paths, "get_save_image_path", side_effect=lambda prefix, directory, *_:
                         (directory, prefix, 1, "", prefix), create=True),
            patch.object(history.server.PromptServer, "instance", types.SimpleNamespace()),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)


class PreviewHistoryTests(HistoryFixture, unittest.TestCase):
    def test_clear_only_owned_top_level_files(self):
        for directory, owned, unrelated in (
            (self.history_dir, "history_test.png", "keep.png"),
            (self.temp_dir, "PreviewHistory_Item_00__00001_.png", "SaveImage.png"),
        ):
            (directory / owned).write_bytes(b"image")
            (directory / unrelated).write_bytes(b"keep")
            (directory / "history_notes.txt").write_text("keep")
            nested = directory / "history_nested.png"
            nested.mkdir()
            (nested / owned).write_bytes(b"keep")
        self.assertEqual(history.PreviewHistory.clear_history(), {"deleted_history": 1, "deleted_previews": 1})
        for directory, unrelated in ((self.history_dir, "keep.png"), (self.temp_dir, "SaveImage.png")):
            self.assertTrue((directory / unrelated).exists())
            self.assertTrue((directory / "history_notes.txt").exists())
            self.assertTrue((directory / "history_nested.png").is_dir())

    def test_missing_directories_and_repeated_clear_are_safe(self):
        self.history_dir.rmdir()
        self.temp_dir.rmdir()
        expected = {"deleted_history": 0, "deleted_previews": 0}
        self.assertEqual(history.PreviewHistory.clear_history(), expected)
        self.assertEqual(history.PreviewHistory.clear_history(), expected)

    def test_clear_invalidates_cached_outputs(self):
        before = history.PreviewHistory.IS_CHANGED(None, 9)
        history.PreviewHistory.clear_history()
        self.assertNotEqual(history.PreviewHistory.IS_CHANGED(None, 9), before)

    def test_preview_copies_are_removed_and_new_history_still_works(self):
        node = history.PreviewHistory()
        Image.new("RGB", (8, 8)).save(self.history_dir / "history_old.png")
        self.assertEqual(len(node.execute(None, 9)["ui"]["images"]), 1)
        self.assertEqual(history.PreviewHistory.clear_history(), {"deleted_history": 1, "deleted_previews": 1})
        self.assertEqual(node.execute(None, 9), {"ui": {"images": []}})
        image = Mock()
        image.nelement.return_value = 192
        image.dim.return_value = 3
        image.cpu.return_value.numpy.return_value = np.zeros((8, 8, 3))
        self.assertEqual(len(node.execute(image, 9)["ui"]["images"]), 1)
        self.assertEqual(len(list(self.history_dir.glob("history_*.png"))), 1)

    def test_delete_failure_is_reported_and_invalidates_cache(self):
        (self.history_dir / "history_locked.png").touch()
        before = history.PreviewHistory.IS_CHANGED(None, 9)
        with patch.object(history.os, "remove", side_effect=PermissionError("locked")):
            with self.assertRaises(PermissionError):
                history.PreviewHistory.clear_history()
        self.assertTrue((self.history_dir / "history_locked.png").exists())
        self.assertNotEqual(history.PreviewHistory.IS_CHANGED(None, 9), before)

    def test_clear_waits_for_in_progress_preview_copy(self):
        copying = threading.Event()
        release = threading.Event()
        clearing = threading.Event()
        cleared = threading.Event()
        errors = []

        def blocked_copy(*args):
            copying.set()
            if not release.wait(3):
                raise TimeoutError("test copy was not released")
            (self.temp_dir / "PreviewHistory_Item_pending.png").touch()

        def run_execute():
            try:
                history.PreviewHistory().execute(None, 9)
            except Exception as error:
                errors.append(error)

        def run_clear():
            clearing.set()
            try:
                history.PreviewHistory.clear_history()
                cleared.set()
            except Exception as error:
                errors.append(error)

        with patch.object(history.PreviewHistory, "_execute", side_effect=blocked_copy):
            executor = threading.Thread(target=run_execute)
            clearer = threading.Thread(target=run_clear)
            executor.start()
            try:
                self.assertTrue(copying.wait(3))
                clearer.start()
                self.assertTrue(clearing.wait(3))
                self.assertFalse(cleared.wait(0.05))
            finally:
                release.set()
                executor.join(3)
                if clearer.ident is not None:
                    clearer.join(3)
        self.assertFalse(executor.is_alive())
        self.assertFalse(clearer.is_alive())
        self.assertEqual(errors, [])
        self.assertTrue(cleared.is_set())
        self.assertFalse((self.temp_dir / "PreviewHistory_Item_pending.png").exists())


class PreviewHistoryRouteTests(HistoryFixture, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        app = web.Application()
        self.broadcast = Mock()
        server = types.SimpleNamespace(instance=types.SimpleNamespace(
            app=app, routes=web.RouteTableDef(), send_sync=self.broadcast,
        ))

        def require_local_token(request):
            if request.headers.get("x-anima-local-token") == "local-test-token":
                return None
            return web.json_response({"error": "Invalid local request token"}, status=403)

        with patch.object(routes, "__file__", str(self.root / "routes_core.py")):
            routes.register_core_routes(server, require_local_token)
        app.add_routes(server.instance.routes)
        self.client = TestClient(TestServer(app))
        await self.client.start_server()
        self.addAsyncCleanup(self.client.close)
        self.headers = {"x-anima-local-token": "local-test-token"}

    async def test_unauthorized_request_cannot_clear_history(self):
        file = self.history_dir / "history_keep.png"
        file.touch()
        response = await self.client.post("/anima/preview_history/clear")
        self.assertEqual(response.status, 403)
        self.assertTrue(file.exists())
        self.broadcast.assert_not_called()

    async def test_authorized_request_clears_and_broadcasts(self):
        (self.history_dir / "history_old.png").touch()
        response = await self.client.post("/anima/preview_history/clear", headers=self.headers)
        self.assertEqual(response.status, 200)
        self.assertEqual(await response.json(), {"success": True, "deleted_history": 1, "deleted_previews": 0})
        self.broadcast.assert_called_once_with("raffle.preview_history.cleared", {
            "deleted_history": 1, "deleted_previews": 0,
        })

    async def test_failure_does_not_broadcast_success(self):
        with patch.object(history.PreviewHistory, "clear_history", side_effect=PermissionError("locked")):
            response = await self.client.post("/anima/preview_history/clear", headers=self.headers)
        self.assertEqual(response.status, 500)
        self.assertFalse((await response.json())["success"])
        self.broadcast.assert_not_called()
