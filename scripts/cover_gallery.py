"""Build a numbered contact sheet from the planned cover candidates."""

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


THUMBNAIL_SIZE = (320, 180)


def _library_file(root: Path, relative: str | None) -> Path | None:
    if not relative:
        return None
    try:
        path = (root / relative).resolve(strict=True)
        return path if path.is_relative_to(root) and path.is_file() else None
    except (OSError, RuntimeError, ValueError):
        return None


def _contact_sheet(candidates: list[dict], thumbnails: list[Image.Image]) -> Image.Image:
    columns = min(3, len(candidates))
    rows = (len(candidates) + columns - 1) // columns
    thumbnail_width, thumbnail_height = THUMBNAIL_SIZE
    card_width = thumbnail_width + 16
    card_height = thumbnail_height + 52
    margin = 20
    gap = 16
    width = 2 * margin + columns * card_width + (columns - 1) * gap
    height = 2 * margin + rows * card_height + (rows - 1) * gap
    sheet = Image.new("RGB", (width, height), "#EBF0F7")
    draw = ImageDraw.Draw(sheet)
    label_font = ImageFont.load_default(size=18)
    number_font = ImageFont.load_default(size=16)

    for index, (candidate, thumbnail) in enumerate(zip(candidates, thumbnails, strict=True)):
        row, column = divmod(index, columns)
        cells_in_row = min(columns, len(candidates) - row * columns)
        row_width = cells_in_row * card_width + (cells_in_row - 1) * gap
        x = (width - row_width) // 2 + column * (card_width + gap)
        y = margin + row * (card_height + gap)
        draw.rounded_rectangle(
            (x, y, x + card_width - 1, y + card_height - 1),
            radius=10,
            fill="white",
            outline="#CFD9E7",
        )
        sheet.paste(thumbnail, (x + 8, y + 8))
        label_center = y + thumbnail_height + 30
        draw.rounded_rectangle(
            (x + 12, label_center - 13, x + 44, label_center + 13),
            radius=7,
            fill="#244A80",
        )
        draw.text(
            (x + 28, label_center),
            f"{candidate['number']:02d}",
            font=number_font,
            fill="white",
            anchor="mm",
        )
        draw.text(
            (x + 56, label_center),
            candidate["layout_id"],
            font=label_font,
            fill="#182E4E",
            anchor="lm",
        )
    return sheet


def build_cover_gallery(library: Path, cover_choice: dict, output: Path) -> dict:
    """Render available previews without changing the plan or its source assets."""
    library = library.resolve()
    output = output.absolute()
    result = {"status": "unavailable", "image_path": None, "candidates": [], "warnings": []}
    candidates, thumbnails = [], []
    warnings = result["warnings"]

    for summary in cover_choice.get("candidate_summaries", []):
        layout_id = summary["layout_id"]
        preview = _library_file(library, summary.get("source_preview"))
        if preview is None:
            warnings.append(f"{layout_id} 缺少库内缩略图")
            continue
        binding = _library_file(library, (summary.get("capacity_preflight") or {}).get("binding_path"))
        if binding is None:
            warnings.append(f"{layout_id} 缺少库内字段绑定文件")
            continue
        try:
            with Image.open(preview) as image:
                thumbnail = ImageOps.pad(
                    image.convert("RGB"), THUMBNAIL_SIZE,
                    method=Image.Resampling.LANCZOS, color="#182E4E",
                )
        except (Image.DecompressionBombError, OSError, ValueError):
            warnings.append(f"{layout_id} 的缩略图无法读取")
            continue

        candidates.append({
            "number": len(candidates) + 1,
            "layout_id": layout_id,
            "binding_path": str(binding),
            "source_preview": str(preview),
        })
        thumbnails.append(thumbnail)

    if not candidates:
        warnings.append("当前封面候选没有可展示的缩略图")
        return result

    try:
        rendered = BytesIO()
        _contact_sheet(candidates, thumbnails).save(rendered, format="PNG")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as file:
            file.write(rendered.getbuffer())
    except FileExistsError:
        warnings.append("封面预览输出已存在")
        return result
    except OSError:
        warnings.append("封面预览无法保存")
        return result

    result.update(status="ready", image_path=str(output), candidates=candidates)
    return result
