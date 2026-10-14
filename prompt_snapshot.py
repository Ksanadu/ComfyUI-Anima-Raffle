SNAPSHOT_KEY = "anima_prompt_snapshot"
REQUEST_KEY = "anima_prompt_snapshot_request"


def find_snapshot_node(workflow, unique_id):
    """Resolve root nodes and execution paths into serialized subgraph nodes."""
    if not isinstance(workflow, dict) or unique_id is None:
        return None
    node_id = str(unique_id)
    for node in workflow.get("nodes", []):
        if str(node.get("id")) == node_id:
            return node
    definitions = workflow.get("definitions", {}).get("subgraphs", [])
    subgraphs = {str(graph.get("id")): graph for graph in definitions}
    graph = workflow
    parts = node_id.split(":")
    for index, part in enumerate(parts):
        node = next((node for node in graph.get("nodes", []) if str(node.get("id")) == part), None)
        if node is None:
            return None
        if index == len(parts) - 1:
            return node
        graph = subgraphs.get(str(node.get("type")))
        if graph is None:
            return None
    return None


def record_snapshot(workflow, unique_id, text):
    node = find_snapshot_node(workflow, unique_id)
    if node is None:
        return ""
    properties = node.setdefault("properties", {})
    properties[SNAPSHOT_KEY] = text
    return properties.get(REQUEST_KEY, "")


def sync_running_workflow(unique_id, text):
    # PromptQueue keeps a deep copy for /history, separate from the metadata
    # passed to Save Image. Update that copy while this exact job is executing.
    try:
        from comfy_execution.utils import get_executing_context
        from server import PromptServer
    except ImportError:
        return
    context = get_executing_context()
    queue = getattr(PromptServer.instance, "prompt_queue", None)
    if context is None or queue is None:
        return
    with queue.mutex:
        for item in queue.currently_running.values():
            if item[1] == context.prompt_id:
                metadata = item[3].get("extra_pnginfo", {})
                if isinstance(metadata, dict):
                    record_snapshot(metadata.get("workflow"), unique_id, text)
                break


class PromptSnapshot:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"forceInput": True,
                                    "tooltip": "The exact prompt to record in this image's workflow."}),
            },
            "optional": {
                "images": ("IMAGE", {"tooltip": "Connect decoded images here and route the images output to Save Image to record the prompt before saving."}),
            },
            "hidden": {"unique_id": "UNIQUE_ID", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ("STRING", "IMAGE")
    RETURN_NAMES = ("text", "images")
    FUNCTION = "capture"
    OUTPUT_NODE = True
    CATEGORY = "Raffle/Previews"
    DESCRIPTION = "Records the received text in the image workflow. Connect the images output to Save Image to ensure capture happens before saving."

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Each queued job has its own workflow metadata, even with cached images.
        return float("nan")

    def capture(self, text, images=None, unique_id=None, extra_pnginfo=None):
        request_id = ""
        if isinstance(extra_pnginfo, dict):
            request_id = record_snapshot(extra_pnginfo.get("workflow"), unique_id, text)
        sync_running_workflow(unique_id, text)
        return {
            "ui": {"saved_text": [text], "snapshot_request": [request_id]},
            "result": (text, images),
        }
