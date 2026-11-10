"""Conservative, local text-PDF supplement; not a universal reading-order engine.

Two-column geometry cannot distinguish prose from borderless paired records.
Auto mode therefore writes a review candidate and exits 2 for such pages.
Use two-column only after visually confirming left-column-first prose.
"""
from pathlib import Path
import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
import math
import re
from statistics import median
import pdfplumber

MIN_GUTTER = 18.0


def box(words):
    return [min(w["x0"] for w in words), min(w["top"] for w in words),
            max(w["x1"] for w in words), max(w["bottom"] for w in words)]


def rows_for(words):
    rows = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if rows and abs(word["top"] - median(w["top"] for w in rows[-1])) <= 2.5:
            rows[-1].append(word)
        else:
            rows.append([word])
    return [sorted(row, key=lambda w: w["x0"]) for row in rows]


def relation(row, split):
    left = [w for w in row if w["x1"] <= split]
    right = [w for w in row if w["x0"] >= split]
    if len(left) + len(right) != len(row):
        return "span"
    if not right:
        return "left"
    if not left:
        return "right"
    return "pair" if right[0]["x0"] - left[-1]["x1"] >= MIN_GUTTER else "span"


def detect_columns(rows, width, min_rows=3, x_offset=0):
    """Find persistent central whitespace, including staggered column baselines."""
    candidates = []
    for split in range(int(x_offset + width * .30), int(x_offset + width * .70) + 1, 2):
        labels = [relation(row, split) for row in rows]
        left = [box(row)[1] for row, label in zip(rows, labels) if label in {"left", "pair"}]
        right = [box(row)[1] for row, label in zip(rows, labels) if label in {"right", "pair"}]
        if len(left) < min_rows or len(right) < min_rows:
            continue
        overlap = max(0., min(max(left), max(right)) - max(min(left), min(right)))
        extent = max(max(left)-min(left), max(right)-min(right), 1.)
        if overlap / extent < .45:
            continue
        score = labels.count("pair") * 2 + min(len(left), len(right)) - labels.count("span")
        candidates.append((score, split, labels))
    if not candidates:
        return None
    best = max(s for s, _, _ in candidates)
    finalists = [(x, labels) for s, x, labels in candidates if s == best]
    # Center of a consecutive best interval avoids a narrow accidental word gap.
    runs = []
    for x, labels in finalists:
        if not runs or x != runs[-1][-1][0] + 2:
            runs.append([])
        runs[-1].append((x, labels))
    run = max(runs, key=lambda r: (len(r), -abs(median(x for x, _ in r)-(x_offset+width/2))))
    split, labels = run[len(run)//2]
    return {"split_x": split, "gutter_search_interval": [run[0][0], run[-1][0]],
            "left_rows": sum(s in {"left", "pair"} for s in labels),
            "right_rows": sum(s in {"right", "pair"} for s in labels),
            "paired_rows": labels.count("pair"), "spanning_rows": labels.count("span")}


def is_three_column(rows):
    return sum(sum(b["x0"]-a["x1"] >= MIN_GUTTER for a, b in zip(row, row[1:])) >= 2
               for row in rows) >= 3


def text_block(words, column="full"):
    return {"kind": "text", "bbox": box(words), "column": column,
            "text": " ".join(w["text"] for w in sorted(words, key=lambda w: w["x0"])),
            "word_ids": [w["id"] for w in words]}


def order_blocks(rows, tables, split):
    events = [(box(row)[1], "row", row) for row in rows]
    events += [(t["bbox"][1], "table", t) for t in tables]
    events.sort(key=lambda event: event[0])
    result, pending = [], []
    body_size = median(w.get("size", 10) for row in rows for w in row) if rows else 10

    def isolated_heading(row):
        side = relation(row, split)
        if side not in {"left", "right"} or max(w.get("size", 10) for w in row) <= body_size * 1.15:
            return False
        _, top, _, bottom = box(row)
        for other in rows:
            for word in other:
                opposite = word["x0"] >= split if side == "left" else word["x1"] <= split
                if opposite and word["bottom"] >= top-body_size and word["top"] <= bottom+body_size:
                    return False
        return True

    def flush():
        if split is None:
            result.extend(text_block(row) for row in pending)
        else:
            for side in ["left", "right"]:
                for row in pending:
                    words = [w for w in row if (w["x1"] <= split if side == "left" else w["x0"] >= split)]
                    if words:
                        result.append(text_block(words, side))
        pending.clear()

    for _, kind, item in events:
        if kind == "table":
            flush()
            result.append(item)
        elif split is not None and (relation(item, split) == "span" or isolated_heading(item)):
            flush()
            result.append(text_block(item))
        else:
            pending.append(item)
    flush()
    return result


def extract_page(page, layout):
    reasons = []
    if any(not c.get("upright", True) for c in page.chars):
        reasons.append("rotated_text_not_supported")
    if page.images:
        reasons.append("images_not_transcribed")
    words = page.extract_words(x_tolerance=2, y_tolerance=2, use_text_flow=False,
                               extra_attrs=["size"])
    for index, word in enumerate(words):
        word["id"] = index
    tables, assigned = [], set()
    for table in page.find_tables():
        x0, top, x1, bottom = table.bbox
        table_words = [w for w in words if x0 <= (w["x0"]+w["x1"])/2 <= x1
                       and top <= (w["top"]+w["bottom"])/2 <= bottom]
        ids = {w["id"] for w in table_words}
        if assigned & ids:
            reasons.append("overlapping_tables")
        assigned |= ids
        cells = table.extract(x_tolerance=2, y_tolerance=2)
        source_tokens = Counter(w["text"] for w in table_words)
        cell_tokens = Counter(token for row in cells for cell in row
                              for token in re.findall(r"\S+", cell or ""))
        text_coverage = {"source_tokens": sum(source_tokens.values()),
                         "cell_tokens": sum(cell_tokens.values()),
                         "exact_token_multiset": source_tokens == cell_tokens}
        if not text_coverage["exact_token_multiset"]:
            reasons.append("table_cell_text_coverage_failure")
        if any(cell is None for row in cells for cell in row):
            reasons.append("merged_or_missing_table_cells")
        tables.append({"kind": "table", "bbox": list(table.bbox), "cells": cells,
                       "word_ids": sorted(ids), "text_coverage": text_coverage})
    rows = rows_for([w for w in words if w["id"] not in assigned])
    x_offset = getattr(page, "bbox", (0, 0, page.width, page.height))[0]
    columns = detect_columns(rows, page.width, x_offset=x_offset)
    if is_three_column(rows):
        reasons.append("three_or_more_columns_or_borderless_table")
        columns = None
    elif not columns and (detect_columns(rows, page.width, min_rows=2, x_offset=x_offset) or
                          any(relation(row, x_offset+page.width/2) == "pair" for row in rows)):
        reasons.append("insufficient_column_evidence")
    if columns and layout != "two-column":
        reasons.append("confirm_two_column_prose_semantics")
    if columns and layout == "single":
        reasons.append("single_column_hint_conflicts_with_geometry")
    if columns and any(t["bbox"][2] < columns["split_x"] or t["bbox"][0] > columns["split_x"] for t in tables):
        reasons.append("column_local_table_requires_review")
    if columns:
        labels = [relation(row, columns["split_x"]) for row in rows]
        body_size = median(w["size"] for row in rows for w in row)
        for index, (row, label) in enumerate(zip(rows, labels)):
            if label in {"left", "right"} and max(w["size"] for w in row) <= body_size * 1.15:
                # Opposite-column proximity, rather than aligned baselines:
                # staggered columns have no "pair" rows but the same ambiguity.
                opposite = "right" if label == "left" else "left"
                before = [j for j in range(index) if labels[j] in {opposite, "pair"}]
                after = [j for j in range(index+1, len(rows)) if labels[j] in {opposite, "pair"}]
                height = median(w["bottom"]-w["top"] for w in row)
                if before and after:
                    if box(row)[1]-box(rows[before[-1]])[3] > height and box(rows[after[0]])[1]-box(row)[3] > height:
                        reasons.append("ambiguous_single_sided_separator")
                if before and box(row)[1]-box(rows[before[-1]])[3] > height:
                    if any(0 <= t["bbox"][1]-box(row)[3] <= 4*height for t in tables):
                        reasons.append("ambiguous_single_sided_separator")
    if not words:
        reasons.append("no_extractable_text_requires_visual_check_or_ocr")
    split = columns["split_x"] if columns and layout != "single" else None
    blocks = order_blocks(rows, tables, split)
    emitted = [i for b in blocks for i in b["word_ids"]]
    coverage = {"source_word_count": len(words), "emitted_word_count": len(emitted),
                "each_source_word_once": Counter(emitted) == Counter(range(len(words)))}
    if not coverage["each_source_word_once"]:
        reasons.append("word_coverage_failure")
    return {"page": page.page_number, "width": page.width, "height": page.height,
            "status": "review_required" if reasons else "accepted",
            "reasons": sorted(set(reasons)), "layout": "two-column" if split else "row-order",
            "geometry_evidence": columns, "coverage": coverage, "blocks": blocks}


def block_markdown(block):
    if block["kind"] == "text":
        return block["text"]
    def escaped(value):
        return str(value or "").replace("|", "\\|").replace("\n", "<br>")
    rows = block["cells"]
    if not rows:
        return "[Empty table: review required]"
    lines = ["| " + " | ".join(map(escaped, row)) + " |" for row in rows]
    lines.insert(1, "| " + " | ".join("---" for _ in rows[0]) + " |")
    return "\n".join(lines)


def normalize_crop(crop):
    if crop is None:
        return None
    if not isinstance(crop, (list, tuple)) or len(crop) != 4:
        raise ValueError("crop must contain four numbers: x0,top,x1,bottom")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in crop):
        raise ValueError("crop coordinates must be finite numbers")
    try:
        finite = all(math.isfinite(v) for v in crop)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError("crop coordinates must be finite numbers")
    x0, top, x1, bottom = map(float, crop)
    if x0 >= x1 or top >= bottom:
        raise ValueError("crop must have positive width and height")
    return (x0, top, x1, bottom)


def parse_crop(value):
    try:
        return normalize_crop(tuple(float(v.strip()) for v in value.split(",")))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def crop_page(source_page, crop):
    x0, top, x1, bottom = crop
    bx0, btop, bx1, bbottom = source_page.bbox
    if x0 < bx0 or top < btop or x1 > bx1 or bottom > bbottom:
        raise ValueError(f"crop lies outside source page {source_page.page_number} bounds {source_page.bbox}")
    source_words = source_page.extract_words(x_tolerance=2, y_tolerance=2,
                                             use_text_flow=False, extra_attrs=["size"])
    cut_word = any(
        min(w["x1"], x1) > max(w["x0"], x0) and min(w["bottom"], bottom) > max(w["top"], top)
        and not (x0 <= w["x0"] and w["x1"] <= x1 and top <= w["top"] and w["bottom"] <= bottom)
        for w in source_words
    )
    region = source_page.crop(crop, relative=False, strict=True)
    # pdfplumber retains edge-touching chars/images with zero width or height.
    # Such objects have no visible area inside the requested region.
    region = region.filter(lambda obj: obj.get("object_type") not in {"char", "image"}
                           or (obj["x1"] > obj["x0"] and obj["bottom"] > obj["top"]))
    return region, cut_word


def extract(path, layout="auto", pages=None, crop=None):
    if layout not in {"auto", "single", "two-column"}:
        raise ValueError("layout must be auto, single, or two-column")
    crop = normalize_crop(crop)
    path = Path(path).resolve(strict=True)
    if path.suffix.lower() != ".pdf":
        raise ValueError("input must be a PDF file")
    page_numbers = list(pages) if pages is not None else None
    if page_numbers is not None and (not page_numbers or len(set(page_numbers)) != len(page_numbers)):
        raise ValueError("pages must be a non-empty list without duplicates")
    with pdfplumber.open(path) as pdf:
        if not pdf.pages:
            raise ValueError("PDF contains no pages")
        if page_numbers is None:
            page_numbers = list(range(1, len(pdf.pages)+1))
        if any(type(n) is not int or n < 1 or n > len(pdf.pages) for n in page_numbers):
            raise ValueError("page numbers must be within the PDF and use one-based integers")
        selected = []
        for number in page_numbers:
            source_page = pdf.pages[number-1]
            region, cut_word = crop_page(source_page, crop) if crop else (source_page, False)
            page = extract_page(region, layout)
            bounds = list(crop or source_page.bbox)
            page.update(width=source_page.width, height=source_page.height,
                        region_width=region.width, region_height=region.height,
                        crop=list(crop) if crop else None, extraction_bounds=bounds,
                        source_bounds=list(source_page.bbox), coordinate_system="PDF_POINTS_TOP_LEFT",
                        extraction_scope="cropped_region" if crop else "full_page")
            page["coverage"].update(source_scope=page["extraction_scope"], bounds=bounds)
            if cut_word:
                page["reasons"] = sorted(set(page["reasons"] + ["crop_intersects_text"]))
                page["status"] = "review_required"
            selected.append(page)
    status = "accepted" if all(p["status"] == "accepted" for p in selected) else "review_required"
    text = "\n\n".join("\n\n".join(block_markdown(b) for b in p["blocks"]) for p in selected)
    return {"schema_version": 1, "input": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "engine": {"pdfplumber": importlib.metadata.version("pdfplumber"),
                       "pdfminer.six": importlib.metadata.version("pdfminer.six")},
            "layout_hint": layout, "status": status, "pages": selected, "text": text,
            "crop": list(crop) if crop else None,
            "coordinate_system": "PDF_POINTS_TOP_LEFT", "crop_relative": False,
            "extraction_scope": "selected_page_regions" if crop else "selected_full_pages",
            "limits": ["Geometry confidence is not proof of semantic reading order.",
                       "Ruled tables only; borderless tables may resemble prose columns.",
                       "No OCR, mathematical reconstruction, or text-layer accuracy guarantee.",
                       "When crop is supplied, output and word conservation cover only that explicit region, not a complete source page."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--layout", choices=["auto", "single", "two-column"], default="auto")
    parser.add_argument("--pages", help="Comma-separated one-based page numbers, in output order")
    parser.add_argument("--crop", type=parse_crop,
                        help="Explicit x0,top,x1,bottom in PDF points/top-left; applies to selected pages only")
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    pages = [int(value) for value in args.pages.split(",")] if args.pages else None
    result = extract(args.pdf, args.layout, pages, args.crop)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "extraction.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    header = "# Extraction candidate: review required\n\n" if result["status"] != "accepted" else ""
    if result["crop"] is not None:
        header += f"> Scope: explicit region {result['crop']} (PDF points, top-left). This is not a complete source-page extraction.\n\n"
    markdown = header + "\n\n".join(f"<!-- Source page {p['page']}; bounds {p['extraction_bounds']}; scope {p['extraction_scope']} -->\n\n" +
        "\n\n".join(block_markdown(b) for b in p["blocks"]) for p in result["pages"])
    (args.output_dir / "extraction.md").write_text(markdown + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "pages": len(result["pages"]),
                      "extraction_scope": result["extraction_scope"], "crop": result["crop"],
                      "output_dir": str(args.output_dir.resolve())}))
    return 0 if result["status"] == "accepted" else 2


if __name__ == "__main__":
    raise SystemExit(main())
