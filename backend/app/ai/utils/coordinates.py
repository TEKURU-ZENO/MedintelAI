from app.schemas.document import BoundingBox, NormalizedBoundingBox


def rendered_to_source(x: float, y: float, rendered_width: int, rendered_height: int,
                       source_width: float, source_height: float) -> tuple[float, float]:
    """Map rendered pixel coordinates to source coordinates using measured dimensions."""
    if min(rendered_width, rendered_height, source_width, source_height) <= 0:
        raise ValueError("Coordinate system dimensions must be positive.")
    if x < 0 or y < 0 or x > rendered_width or y > rendered_height:
        raise ValueError("Rendered coordinates must fit within the rendered page.")
    return x * source_width / rendered_width, y * source_height / rendered_height


def source_to_rendered(x: float, y: float, rendered_width: int, rendered_height: int,
                       source_width: float, source_height: float) -> tuple[float, float]:
    if min(rendered_width, rendered_height, source_width, source_height) <= 0:
        raise ValueError("Coordinate system dimensions must be positive.")
    if x < 0 or y < 0 or x > source_width or y > source_height:
        raise ValueError("Source coordinates must fit within the source page.")
    return x * rendered_width / source_width, y * rendered_height / source_height


def crop_to_global(x: float, y: float, crop_x: int, crop_y: int) -> tuple[float, float]:
    if min(x, y, crop_x, crop_y) < 0:
        raise ValueError("Crop and local coordinates must be non-negative.")
    return crop_x + x, crop_y + y


def crop_box_to_global(box: BoundingBox, crop_x: int, crop_y: int) -> BoundingBox:
    if min(crop_x, crop_y) < 0:
        raise ValueError("Crop origin must be non-negative.")
    return BoundingBox(x=crop_x + box.x, y=crop_y + box.y,
                       width=box.width, height=box.height)


def rendered_box_to_source(box: BoundingBox, rendered_width: int, rendered_height: int,
                           source_width: float, source_height: float) -> BoundingBox:
    x1, y1 = rendered_to_source(box.x, box.y, rendered_width, rendered_height, source_width, source_height)
    x2, y2 = rendered_to_source(box.x + box.width, box.y + box.height,
                                rendered_width, rendered_height, source_width, source_height)
    return BoundingBox(x=round(x1), y=round(y1), width=round(x2) - round(x1), height=round(y2) - round(y1))


def normalize_box(box: BoundingBox, page_width: int, page_height: int) -> NormalizedBoundingBox:
    if page_width <= 0 or page_height <= 0:
        raise ValueError("Page dimensions must be positive.")
    if box.x + box.width > page_width or box.y + box.height > page_height:
        raise ValueError("Bounding box must fit within page dimensions.")
    return NormalizedBoundingBox(x=box.x / page_width, y=box.y / page_height,
                                 width=box.width / page_width, height=box.height / page_height)


def denormalize_box(box: NormalizedBoundingBox, page_width: int, page_height: int) -> BoundingBox:
    if page_width <= 0 or page_height <= 0:
        raise ValueError("Page dimensions must be positive.")
    x, y = round(box.x * page_width), round(box.y * page_height)
    width, height = round(box.width * page_width), round(box.height * page_height)
    if width <= 0 or height <= 0:
        raise ValueError("Normalized box maps to an empty pixel region.")
    return BoundingBox(x=x, y=y, width=width, height=height)
