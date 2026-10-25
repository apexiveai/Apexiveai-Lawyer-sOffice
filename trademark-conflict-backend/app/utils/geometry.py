from typing import Tuple

def expand_bbox(

    bbox: Tuple[int, int, int, int],

    image_width: int,

    image_height: int,

    padding: float = 0.15,

):

    x, y, w, h = bbox

    pad_x = int(w * padding)

    pad_y = int(h * padding)

    x1 = max(0, x - pad_x)

    y1 = max(0, y - pad_y)

    x2 = min(

        image_width,

        x + w + pad_x,

    )

    y2 = min(

        image_height,

        y + h + pad_y,

    )

    return (

        x1,

        y1,

        x2 - x1,

        y2 - y1,

    )

def bbox_center(

    bbox: Tuple[int, int, int, int]

):

    x, y, w, h = bbox

    return (

        x + w // 2,

        y + h // 2,

    )