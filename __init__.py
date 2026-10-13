from .nodes import NODE_CLASS_MAPPINGS as ANIMA_NODE_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS as ANIMA_DISPLAY_NAME_MAPPINGS
from .raffle import NODE_CLASS_MAPPINGS as RAFFLE_NODE_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS as RAFFLE_DISPLAY_NAME_MAPPINGS
from .preview_history import PreviewHistory
from .tag_category_strength import TagCategoryStrength
from .curved_rescale_cfg import CurvedRescaleCFG

NODE_CLASS_MAPPINGS = {
    **ANIMA_NODE_MAPPINGS,
    **RAFFLE_NODE_MAPPINGS,
    "PreviewHistory": PreviewHistory,
    "TagCategoryStrength": TagCategoryStrength,
    "CurvedRescaleCFG": CurvedRescaleCFG,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    **ANIMA_DISPLAY_NAME_MAPPINGS,
    **RAFFLE_DISPLAY_NAME_MAPPINGS,
    "PreviewHistory": "Preview History (Raffle)",
    "TagCategoryStrength": "Tag Category Strength (Raffle)",
    "CurvedRescaleCFG": "Curved Rescale CFG (Raffle)",
}

WEB_DIRECTORY = "./js"

try:
    from server import PromptServer
    from . import routes
    routes.register(PromptServer)
    print(" [AnimaStyleExplorer] Routes registered successfully.")
except Exception as e:
    print(f" [AnimaStyleExplorer] Error registering routes: {e}")

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
