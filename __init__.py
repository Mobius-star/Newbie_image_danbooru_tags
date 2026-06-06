from .parser import DanbooruSmartMart
from .wrapper import WrapperNode

NODE_CLASS_MAPPINGS = {
    "DanbooruSmartMart": DanbooruSmartMart,
    "wrapper": WrapperNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DanbooruSmartMart": "Newbie_image_danbooru_tags (Parser)",
    "wrapper": "Newbie_image_danbooru_tags (Wrapper)",
}

WEB_DIRECTORY = "./web"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']