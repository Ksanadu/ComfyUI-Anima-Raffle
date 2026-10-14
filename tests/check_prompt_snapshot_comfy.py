"""Run with ComfyUI's Python: python tests/check_prompt_snapshot_comfy.py /path/to/ComfyUI."""
import asyncio
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch


async def main(comfy_root):
    sys.path.insert(0, str(comfy_root))
    from comfy.cli_args import args
    args.cpu = True
    args.disable_metadata = False
    import execution
    import folder_paths
    import nodes
    import server
    import torch
    from aiohttp import web
    from PIL import Image

    events = []
    test_server = SimpleNamespace(
        app=web.Application(), routes=web.RouteTableDef(), client_id=None,
        sockets_metadata={}, send_sync=lambda *event: events.append(event),
        queue_updated=lambda: None,
    )
    server.PromptServer.instance = test_server
    package_root = Path(__file__).resolve().parents[1]
    assert await nodes.load_custom_node(str(package_root))
    assert "PromptSnapshot" in nodes.NODE_CLASS_MAPPINGS
    executions = []

    class TestImageSource:
        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {}}
        RETURN_TYPES = ("IMAGE",)
        FUNCTION = "generate"
        CATEGORY = "Tests"

        def generate(self):
            executions.append("image source")
            return (torch.zeros(2, 8, 8, 3),)

    nodes.NODE_CLASS_MAPPINGS["SnapshotTestImageSource"] = TestImageSource
    executor = execution.PromptExecutor(test_server, execution.CacheType.CLASSIC,
                                        {"ram": 0, "ram_inactive": 0})
    queue = execution.PromptQueue(test_server)
    test_server.prompt_queue = queue
    text_a = "picture A, 中文, ^_^, o_o\n  keep whitespace  "
    text_b = "picture B, different prompt"
    images_written = []
    with tempfile.TemporaryDirectory() as temp, patch.object(folder_paths, "get_output_directory", return_value=temp):
        for index, text in enumerate((text_a, text_b, text_b)):
            prompt = {
                "1": {"class_type": "SnapshotTestImageSource", "inputs": {}},
                "2": {"class_type": "AnimaStyleExplorerText", "inputs": {"text": text}},
                "3": {"class_type": "PromptSnapshot", "inputs": {"text": ["2", 0], "images": ["1", 0]}},
                "4": {"class_type": "SaveImage", "inputs": {"images": ["3", 1], "filename_prefix": "SnapshotTest"}},
            }
            workflow = {"nodes": [{"id": 3, "type": "PromptSnapshot", "properties": {
                "anima_prompt_snapshot": "stale preview from a previous job",
                "anima_prompt_snapshot_request": f"job-{index}",
            }, "widgets_values": []}]}
            valid, error, outputs, node_errors = await execution.validate_prompt(f"job-{index}", prompt, None)
            assert valid, (error, node_errors)
            extra_data = {
                "client_id": "snapshot-test", "extra_pnginfo": {"workflow": workflow},
            }
            queue.put((index, f"job-{index}", copy.deepcopy(prompt), extra_data, sorted(outputs, reverse=True), {}))
            item, item_id = queue.get()
            await executor.execute_async(item[2], item[1], item[3].copy(), item[4])
            assert executor.success, executor.status_messages
            result = executor.history_result["outputs"]
            assert result["3"]["saved_text"] == [text]
            assert result["3"]["snapshot_request"] == [f"job-{index}"]
            assert len(result["4"]["images"]) == 2
            for entry in result["4"]["images"]:
                file = Path(temp) / entry["subfolder"] / entry["filename"]
                with Image.open(file) as image:
                    saved_workflow = json.loads(image.info["workflow"])
                properties = saved_workflow["nodes"][0]["properties"]
                assert properties["anima_prompt_snapshot"] == text
                assert properties["anima_prompt_snapshot_request"] == f"job-{index}"
                images_written.append((file, text))
            queue.task_done(item_id, executor.history_result, None, lambda item: item[:5])
            recorded = queue.get_history(f"job-{index}")[f"job-{index}"]
            history_workflow = recorded["prompt"][3]["extra_pnginfo"]["workflow"]
            saved_prompt = history_workflow["nodes"][0]["properties"]["anima_prompt_snapshot"]
            assert saved_prompt == text, "Inactive workflow's task history kept the previous prompt"
        assert len(executions) == 1, "Snapshot must not invalidate cached upstream images"
        assert len({file for file, _ in images_written}) == 6, "Each queue must save a new image with its own record"
        for file, expected in images_written:
            with Image.open(file) as image:
                saved = json.loads(image.info["workflow"])["nodes"][0]["properties"]["anima_prompt_snapshot"]
            assert saved == expected, "Later jobs changed an older image's saved prompt"
        cached = [event[1]["nodes"] for event in events if event[0] == "execution_cached"]
        assert {"1", "2"} <= set(cached[-1])
        assert not {"3", "4"}.intersection(cached[-1])
    print("PASS: real ComfyUI executor and Save Image; A/B PNG round-trip, repeated prompt,")
    print("      two-image batches, cached upstream images and per-job PNG/task-history records.")


if __name__ == "__main__":
    comfy_root = Path(sys.argv[1]).resolve()
    sys.argv = [sys.argv[0]]
    asyncio.run(main(comfy_root))
