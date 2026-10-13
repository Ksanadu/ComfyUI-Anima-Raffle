import nodes
import sys

class AnimaStyleExplorer(nodes.CLIPTextEncode):

    CATEGORY = "Anima"
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clip": ("CLIP",),
                "text": ("STRING", {
                    "multiline": True,
                    "default": "1girl, masterpiece, best quality",
                }),
            },
        }
    
class AnimaStyleExplorerText:

    CATEGORY = "Anima"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "execute"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {
                    "multiline": True,
                    "default": "1girl, masterpiece, best quality",
                }),
            },
        }

    def execute(self, text):
        return (text,)


NODE_CLASS_MAPPINGS = {
    "AnimaStyleExplorer": AnimaStyleExplorer,
    "AnimaStyleExplorerText": AnimaStyleExplorerText,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AnimaStyleExplorer": "Anima Style Explorer",
    "AnimaStyleExplorerText": "Anima Style Explorer (Text)",
}
