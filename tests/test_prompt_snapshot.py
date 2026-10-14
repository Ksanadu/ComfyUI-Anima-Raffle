import copy
import importlib.util
import math
from pathlib import Path
import sys
import threading
import types
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("prompt_snapshot_tests", Path(__file__).resolve().parents[1] / "prompt_snapshot.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PromptSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.node = module.PromptSnapshot()
        self.metadata = {"workflow": {"nodes": [
            {"id": 3, "type": "PromptSnapshot", "properties": {
                module.REQUEST_KEY: "job-a", "keep": "unchanged",
            }, "widgets_values": []},
            {"id": 4, "type": "SaveImage", "properties": {}},
        ]}, "keep": {"other": "metadata"}}

    def test_exact_prompt_and_images_pass_through_and_are_saved(self):
        text = "  @artist, 1girl, ^_^, o_o\n中文提示词  "
        images = object()
        result = self.node.capture(text, images, 3, self.metadata)
        self.assertEqual(result["result"][0], text)
        self.assertIs(result["result"][1], images)
        self.assertEqual(result["ui"], {"saved_text": [text], "snapshot_request": ["job-a"]})
        saved = self.metadata["workflow"]["nodes"][0]
        self.assertEqual(saved["properties"][module.SNAPSHOT_KEY], text)
        self.assertEqual(saved["properties"]["keep"], "unchanged")
        self.assertEqual(saved["widgets_values"], [])
        self.assertEqual(self.metadata["keep"], {"other": "metadata"})
        self.assertEqual(self.metadata["workflow"]["nodes"][1]["properties"], {})

    def test_new_job_does_not_change_previous_workflow_record(self):
        next_metadata = copy.deepcopy(self.metadata)
        self.node.capture("picture A", unique_id="3", extra_pnginfo=self.metadata)
        self.node.capture("picture B", unique_id="3", extra_pnginfo=next_metadata)
        self.assertEqual(self.metadata["workflow"]["nodes"][0]["properties"][module.SNAPSHOT_KEY], "picture A")
        self.assertEqual(next_metadata["workflow"]["nodes"][0]["properties"][module.SNAPSHOT_KEY], "picture B")

    def test_empty_prompt_overwrites_old_record_without_formatting(self):
        self.node.capture("old", unique_id="3", extra_pnginfo=self.metadata)
        result = self.node.capture("", unique_id="3", extra_pnginfo=self.metadata)
        self.assertEqual(result["ui"]["saved_text"], [""])
        self.assertEqual(self.metadata["workflow"]["nodes"][0]["properties"][module.SNAPSHOT_KEY], "")

    def test_api_without_workflow_metadata_still_returns_text(self):
        for metadata in (None, {}, {"workflow": None}, {"workflow": {"nodes": []}}):
            self.assertEqual(self.node.capture("prompt", unique_id="3", extra_pnginfo=metadata)["result"], ("prompt", None))

    def test_each_job_captures_even_when_upstream_inputs_are_cached(self):
        self.assertTrue(math.isnan(self.node.IS_CHANGED(text="same text")))
        self.assertNotEqual(self.node.IS_CHANGED(), self.node.IS_CHANGED())

    def test_multiple_snapshot_nodes_keep_separate_texts(self):
        self.metadata["workflow"]["nodes"].append({"id": 5, "type": "PromptSnapshot"})
        self.node.capture("first", unique_id="3", extra_pnginfo=self.metadata)
        self.node.capture("second", unique_id="5", extra_pnginfo=self.metadata)
        self.assertEqual(self.metadata["workflow"]["nodes"][0]["properties"][module.SNAPSHOT_KEY], "first")
        self.assertEqual(self.metadata["workflow"]["nodes"][2]["properties"][module.SNAPSHOT_KEY], "second")

    def test_subgraph_execution_path_updates_the_contained_node(self):
        workflow = {"nodes": [{"id": 10, "type": "outer"}], "definitions": {"subgraphs": [
            {"id": "outer", "nodes": [{"id": 20, "type": "inner"}]},
            {"id": "inner", "nodes": [{"id": 3, "type": "PromptSnapshot"}]},
        ]}}
        self.node.capture("nested", unique_id="10:20:3", extra_pnginfo={"workflow": workflow})
        self.assertEqual(workflow["definitions"]["subgraphs"][1]["nodes"][0]["properties"][module.SNAPSHOT_KEY], "nested")
        self.assertIsNone(module.find_snapshot_node(workflow, "10:99:3"))

    def running_queue(self, context):
        current = copy.deepcopy(self.metadata)
        unrelated = copy.deepcopy(self.metadata)
        queue = types.SimpleNamespace(mutex=threading.RLock(), currently_running={
            0: (0, "job-a", {}, {"extra_pnginfo": current}, []),
            1: (1, "job-b", {}, {"extra_pnginfo": unrelated}, []),
        })
        utils = types.ModuleType("comfy_execution.utils")
        utils.get_executing_context = lambda: context
        server = types.ModuleType("server")
        server.PromptServer = types.SimpleNamespace(instance=types.SimpleNamespace(prompt_queue=queue))
        return queue, current, unrelated, patch.dict(sys.modules, {
            "comfy_execution": types.ModuleType("comfy_execution"),
            "comfy_execution.utils": utils, "server": server,
        })

    def test_background_job_updates_history_copy_without_touching_another_job(self):
        _, current, unrelated, modules = self.running_queue(types.SimpleNamespace(prompt_id="job-a"))
        with modules:
            self.node.capture("background prompt", unique_id="3", extra_pnginfo=self.metadata)
        self.assertEqual(current["workflow"]["nodes"][0]["properties"][module.SNAPSHOT_KEY], "background prompt")
        self.assertNotIn(module.SNAPSHOT_KEY, unrelated["workflow"]["nodes"][0]["properties"])
        self.assertEqual(current["workflow"]["nodes"][0]["properties"][module.REQUEST_KEY], "job-a")

    def test_missing_execution_context_still_records_png_metadata(self):
        _, current, _, modules = self.running_queue(None)
        with modules:
            self.node.capture("PNG prompt", unique_id="3", extra_pnginfo=self.metadata)
        self.assertEqual(self.metadata["workflow"]["nodes"][0]["properties"][module.SNAPSHOT_KEY], "PNG prompt")
        self.assertNotIn(module.SNAPSHOT_KEY, current["workflow"]["nodes"][0]["properties"])

    def test_missing_job_does_not_update_a_different_running_job(self):
        _, current, unrelated, modules = self.running_queue(types.SimpleNamespace(prompt_id="unknown-job"))
        with modules:
            self.node.capture("another request", unique_id="3", extra_pnginfo=self.metadata)
        for metadata in (current, unrelated):
            self.assertNotIn(module.SNAPSHOT_KEY, metadata["workflow"]["nodes"][0]["properties"])
