#!/usr/bin/env python3
"""Manage the visual-bible reference library.

  library.py new <kind> <id>            write a spec template into visual-bible/_drafts/<id>/
  library.py anchor <id> [--candidates N]  generate anchor candidates from the spec
  library.py pick <id> <letter>         make one candidate the anchor
  library.py pack <id> [--plates a,b]   generate the remaining plates from the anchor
  library.py promote <id>               move a reviewed draft into the library
  library.py registry                   rebuild registry.json, marks.md, and index.html
  library.py check                      validate specs, marks, plates, and shot references

Reads GEMINI_API_KEY from the environment or the project .env file.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
import re
import shutil
import string
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VB = ROOT / "visual-bible"
DRAFTS = VB / "_drafts"
REGISTRY_PATH = VB / "registry.json"
MARKS_PATH = VB / "marks.md"
INDEX_PATH = VB / "index.html"
ENV_PATH = ROOT / ".env"
MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")
ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

KIND_DIRS = {
    "character": "characters",
    "wardrobe": "wardrobe",
    "location": "locations",
    "prop": "props",
    "style": "style",
}
ANCHORS = {"character": "front", "wardrobe": "look", "location": "establishing", "prop": "insert"}
DEFAULT_PLATES = {
    "character": ["front", "three-quarter", "profile", "full-body"],
    "wardrobe": ["look"],
    "location": ["establishing"],
    "prop": ["insert"],
}
STYLE_BOARDS = {
    "still-life": "sources/style-boards/01-still-life-line.jpg",
    "brush-face": "sources/style-boards/02-brush-face.jpg",
    "figure": "sources/style-boards/03-figure-line.jpg",
}
KIND_BOARDS = {
    "character": ["figure", "brush-face"],
    "wardrobe": ["figure"],
    "location": ["still-life", "brush-face"],
    "prop": ["still-life"],
}

STYLE_LOCK = """
STYLE LOCK. The attached images are style references only. Match their drawing language. Do not copy their subjects, poses, costumes, or compositions. Do not draw sunflowers, the reclining brush face, or the jeweled dancer.

Medium: an original hand-drawn black ink illustration on warm off-white paper. No frame, no border, no signature, no caption, no text of any kind, no color.

Line: alive ink. Hairline contours and heavy brush strokes can exist in the same picture. Lines are slightly imperfect.

Black: large flat areas of solid black for hair, deepest shadow, pupils, and graphic accents. The rest of the image stays the paper color. No gray paint, no gradients, no halftone dots. Hatching is sparse and only where a form needs shadow.

Ornament: almost none. Do not add spirals, curls, or dots in the empty paper or around an object. Draw one only when the subject text says that exact mark is required, and draw only that one. Do not copy spirals from the reference images.

Faces: simplified. Almond or lowered eyes with clear lashes, a nose of one or two lines, a small mouth.

Space: generous empty paper. Sparse background. Strong silhouette. Graphic clarity suitable for limited animation.

Forbidden: photorealism, color, gray washes, 3D rendering, anime, clean vector art, watercolor, pencil-only sketch, comic-book screentone, watermarks, letters, numbers, labels, stray spirals, stray curls, decorative dots.
""".strip()

PLATE_TEMPLATES = {
    "character": {
        "front": "Front portrait, head and shoulders, of {name}. Level or slightly lowered gaze. Empty paper background. This is the canonical face that every later image will copy.",
        "three-quarter": "A true three-quarter portrait, head and shoulders, of {name}. The head is turned about thirty to forty-five degrees so one ear is clearly more visible than the other. Both eyes are visible, but the face is not frontal and the crop differs from the anchor. Empty paper.",
        "profile": "A strict side-profile portrait, head and shoulders, of {name}. The nose points at the edge of the frame. Only one eye is visible. The far side of the face is hidden. Empty paper. This must not read as a three-quarter view.",
        "full-body": "Full-body front view of {name} standing quietly, arms relaxed, both feet fully visible. Simplified anatomy. Empty paper with no stray marks near the feet.",
        "sitting": "{name} seated on a simple chair, three-quarter view, hands resting in the lap. The chair is a few ink lines. Empty paper around the figure.",
        "expressions": "Four heads of {name} in a single row on empty paper, equally spaced. Left to right: neutral; a small closed-mouth smile; worry with a slightly gathered brow; eyes fully closed. The same marks on every head. No labels, no boxes.",
        "walking": "Full-body side view of {name} walking slowly, mid-stride, drawn mostly as solid black silhouette with thin paper-white interior lines. The profile of the face stays readable. Empty paper.",
    },
    "wardrobe": {
        "look": "Full body, front view, of {wearer} wearing {name}. Both feet visible. Empty paper. The garment is the subject; the face and marks stay those of the wearer.",
        "side": "Full body, side view, of {wearer} wearing {name}. Both feet visible. Empty paper.",
    },
    "location": {
        "establishing": "A wide establishing view of {name}. No people. Most of the picture is empty paper. One large solid black shape anchors the composition.",
        "reverse": "{name} seen from the opposite direction. The same objects and the same placement of the black mass. No people.",
        "night": "{name} at night. The sky or the window is a solid black field, with one small pool of paper-white light. No people.",
        "detail": "A close insert of one telling detail of {name}. No people.",
    },
    "prop": {
        "insert": "{name}, a single object centered on empty paper, as an insert shot. No hands, no people.",
        "alt": "{name} from a different angle, still alone on empty paper. No hands, no people.",
    },
}


class LibraryError(Exception):
    pass


# --- specs -------------------------------------------------------------------


def parse_scalar(value: str):
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        return [item.strip() for item in value[1:-1].split(",") if item.strip()]
    return value


def parse_spec(path: Path) -> dict:
    text = path.read_text()
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not match:
        raise LibraryError(f"{rel(path)} has no frontmatter block")
    head, body = match.groups()
    spec: dict = {}
    current_map: dict | None = None
    for line in head.splitlines():
        if not line.strip():
            continue
        if line.startswith("  ") and current_map is not None:
            key, _, value = line.strip().partition(":")
            current_map[key.strip()] = value.strip()
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.split("#", 1)[0] if not value.strip().startswith("[") else value
        if value.strip():
            spec[key] = parse_scalar(value)
            current_map = None
        else:
            current_map = {}
            spec[key] = current_map
    fields = {"Identity": "identity", "Required marks": "required", "Forbidden marks": "forbidden"}
    for line in body.splitlines():
        label, _, value = line.partition(":")
        if label.strip() in fields:
            spec[fields[label.strip()]] = value.strip()
    for key in ("required", "forbidden"):
        spec[key] = [item.strip() for item in spec.get(key, "").split(";") if item.strip()]
    spec.setdefault("identity", "")
    spec.setdefault("plates", [])
    if isinstance(spec["plates"], str):
        spec["plates"] = [spec["plates"]]
    spec["_path"] = path
    spec["_dir"] = path.parent
    return spec


def set_spec_field(path: Path, key: str, value: str) -> None:
    text = path.read_text()
    pattern = re.compile(rf"^{re.escape(key)}:.*$", re.M)
    if pattern.search(text):
        text = pattern.sub(f"{key}: {value}", text, count=1)
    else:
        text = text.replace("\n---\n", f"\n{key}: {value}\n---\n", 1)
    path.write_text(text)


def library_specs() -> dict[str, dict]:
    specs: dict[str, dict] = {}
    for kind, folder in KIND_DIRS.items():
        base = VB / folder
        if kind == "style":
            candidates = [base / "spec.md"]
        else:
            candidates = sorted(base.glob("*/spec.md"))
        for path in candidates:
            if not path.exists():
                continue
            spec = parse_spec(path)
            if spec.get("kind") != kind:
                raise LibraryError(f"{rel(path)} says kind {spec.get('kind')!r} but lives in {folder}/")
            if kind != "style" and spec.get("id") != path.parent.name:
                raise LibraryError(f"{rel(path)} id {spec.get('id')!r} does not match its folder name")
            if spec["id"] in specs:
                raise LibraryError(f"duplicate id {spec['id']!r}")
            specs[spec["id"]] = spec
    return specs


def draft_spec(entity_id: str) -> dict | None:
    path = DRAFTS / entity_id / "spec.md"
    return parse_spec(path) if path.exists() else None


def find_spec(entity_id: str) -> tuple[dict, bool]:
    draft = draft_spec(entity_id)
    if draft:
        return draft, True
    specs = library_specs()
    if entity_id in specs:
        return specs[entity_id], False
    raise LibraryError(f"no spec for {entity_id!r} in the library or in _drafts/")


def plate_path(spec: dict, plate: str) -> Path:
    return spec["_dir"] / f"{plate}.png"


def anchor_name(spec: dict) -> str:
    return Path(spec.get("anchor") or f"{ANCHORS[spec['kind']]}.png").stem


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


# --- marks -------------------------------------------------------------------


def norm_mark(mark: str) -> str:
    cleaned = mark.lower().translate(str.maketrans("", "", string.punctuation))
    return " ".join(cleaned.split())


def mark_collisions(specs: list[dict]) -> list[str]:
    owners: dict[str, str] = {}
    errors = []
    for spec in specs:
        if spec.get("kind") != "character":
            continue
        for mark in spec["required"]:
            key = norm_mark(mark)
            if key in owners and owners[key] != spec["id"]:
                errors.append(f"mark {mark!r} is required by both {owners[key]} and {spec['id']}")
            owners.setdefault(key, spec["id"])
    return errors


# --- registry ----------------------------------------------------------------


def shot_files() -> list[Path]:
    return sorted((ROOT / "story").glob("**/shot-prompts.json"))


def scan_usage(path_to_entity: dict[str, str]) -> dict[str, set[str]]:
    used: dict[str, set[str]] = {}
    for path in shot_files():
        try:
            shots = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        for shot in shots if isinstance(shots, list) else []:
            match = re.match(r"e(\d{2})", str(shot.get("id", "")).lower())
            if not match:
                continue
            episode = f"E{match.group(1)}"
            ids = set()
            if shot.get("lead"):
                ids.add("lead")
            for ref in shot.get("references", []) or []:
                owner = path_to_entity.get(ref.get("path", ""))
                if owner:
                    ids.add(owner)
            for entity in shot.get("entities", []) or []:
                if entity.get("id"):
                    ids.add(entity["id"])
            for entity_id in ids:
                used.setdefault(entity_id, set()).add(episode)
    return used


def build_registry(specs: dict[str, dict]) -> dict:
    path_to_entity = {}
    for spec in specs.values():
        for plate in spec["plates"]:
            path_to_entity[rel(plate_path(spec, plate))] = spec["id"]
    used = scan_usage(path_to_entity)
    entities = {}
    for entity_id in sorted(specs, key=lambda key: (list(KIND_DIRS).index(specs[key]["kind"]), key)):
        spec = specs[entity_id]
        entry = {
            "kind": spec["kind"],
            "name": spec.get("name", entity_id),
            "status": spec.get("status", "approved"),
            "dir": rel(spec["_dir"]),
            "anchor": rel(plate_path(spec, anchor_name(spec))),
            "plates": {plate: rel(plate_path(spec, plate)) for plate in spec["plates"]},
            "identity": spec["identity"],
            "required": spec["required"],
            "forbidden": spec["forbidden"],
        }
        for key in ("wearer", "wardrobe", "plate_notes", "introduced_in"):
            if spec.get(key):
                entry[key] = spec[key]
        entry["used_in"] = sorted(used.get(entity_id, set()))
        entities[entity_id] = entry
    return {
        "version": 2,
        "generated_by": "python3 scripts/library.py registry",
        "model": MODEL,
        "style_boards": STYLE_BOARDS,
        "entities": entities,
    }


def build_marks(specs: dict[str, dict]) -> str:
    lines = [
        "# Identity marks",
        "",
        "Generated by `python3 scripts/library.py registry` from each `spec.md`. Edit the specs, not this file.",
        "",
        "A character's required marks belong to that character alone. Before you add a character, pick two or three marks that do not appear here. Silhouette and hair come first. Ornament comes second.",
        "",
    ]
    titles = {"character": "Characters", "wardrobe": "Wardrobe", "location": "Locations", "prop": "Props"}
    for kind, title in titles.items():
        rows = [spec for spec in specs.values() if spec["kind"] == kind]
        if not rows:
            continue
        lines += [f"## {title}", "", "| Id | Owns | Never |", "| --- | --- | --- |"]
        for spec in sorted(rows, key=lambda item: item["id"]):
            owns = "; ".join(spec["required"]) or "-"
            never = "; ".join(spec["forbidden"]) or "-"
            label = spec["id"] if kind != "wardrobe" else f"{spec['id']} (worn by {spec.get('wearer', '?')})"
            lines.append(f"| {label} | {owns} | {never} |")
        lines.append("")
    return "\n".join(lines)


def registry_outputs() -> tuple[str, str]:
    specs = library_specs()
    registry = json.dumps(build_registry(specs), indent=2, ensure_ascii=False) + "\n"
    return registry, build_marks(specs)


def page_src(path: str) -> str:
    prefix = "visual-bible/"
    if path.startswith(prefix):
        return path[len(prefix):]
    return "../" + path


def render_card(entity_id: str, entity: dict) -> str:
    anchor_file = Path(entity["anchor"]).name
    notes = entity.get("plate_notes") or {}
    figures = []
    for plate, path in entity["plates"].items():
        caption = f"{entity_id} · {plate}"
        if plate in notes:
            caption = f"{caption} — {notes[plate]}"
        label = plate + (" · anchor" if Path(path).name == anchor_file else "")
        figures.append(
            "<figure>"
            f'<button type="button" data-caption="{html.escape(caption, quote=True)}" aria-label="{html.escape(caption, quote=True)}">'
            f'<img src="{html.escape(page_src(path), quote=True)}" alt="{html.escape(caption, quote=True)}">'
            "</button>"
            f"<figcaption>{html.escape(label)}</figcaption>"
            "</figure>"
        )
    required = "".join(f"<li>{html.escape(mark)}</li>" for mark in entity.get("required") or []) or "<li>None</li>"
    forbidden = "".join(f"<li>{html.escape(mark)}</li>" for mark in entity.get("forbidden") or []) or "<li>None</li>"
    used = ", ".join(entity.get("used_in") or []) or "no shot file yet"
    meta = [entity["kind"], f"introduced in {entity.get('introduced_in', '—')}", f"used in {used}"]
    if entity.get("wearer"):
        meta.append(f"worn by {entity['wearer']}")
    if entity.get("wardrobe"):
        meta.append("wardrobe " + ", ".join(entity["wardrobe"]))
    if entity.get("status") != "approved":
        meta.append(entity["status"])
    blob = " ".join(
        [
            entity_id,
            entity.get("name", ""),
            entity.get("identity", ""),
            *entity.get("required", []),
            *entity.get("forbidden", []),
            *entity["plates"],
            *notes.values(),
            *meta,
        ]
    ).lower()
    return (
        f'<article data-search="{html.escape(blob, quote=True)}">'
        "<div class=\"copy\">"
        f"<h3>{html.escape(entity.get('name', entity_id))} <code>{html.escape(entity_id)}</code></h3>"
        f"<p class=\"meta\">{html.escape(' · '.join(meta))}</p>"
        f"<p>{html.escape(entity.get('identity', ''))}</p>"
        "<dl>"
        "<dt>Must show</dt>"
        f"<dd><ul>{required}</ul></dd>"
        "<dt>Never</dt>"
        f"<dd><ul>{forbidden}</ul></dd>"
        "</dl>"
        "</div>"
        f'<div class="plates">{"".join(figures)}</div>'
        "</article>"
    )


def build_index(registry: dict) -> str:
    entities = registry["entities"]
    plate_count = sum(len(entity["plates"]) for entity in entities.values())
    titles = {
        "character": "Characters",
        "wardrobe": "Wardrobe",
        "location": "Locations",
        "prop": "Props",
        "style": "Style",
    }
    nav = "".join(f'<a href="#{kind}">{html.escape(title)}</a>' for kind, title in titles.items())
    nav += '<a href="#boards">Style boards</a>'
    sections = []
    for kind, title in titles.items():
        rows = [(entity_id, entity) for entity_id, entity in entities.items() if entity["kind"] == kind]
        if not rows:
            continue
        cards = "\n".join(render_card(entity_id, entity) for entity_id, entity in rows)
        sections.append(f'<section id="{kind}">\n<h2>{html.escape(title)}</h2>\n{cards}\n</section>')
    boards = []
    for name, path in registry.get("style_boards", {}).items():
        boards.append(
            "<figure>"
            f'<button type="button" data-caption="{html.escape(name, quote=True)}" aria-label="{html.escape(name, quote=True)}">'
            f'<img src="{html.escape(page_src(path), quote=True)}" alt="{html.escape(name, quote=True)}">'
            "</button>"
            f"<figcaption>{html.escape(name)}</figcaption>"
            "</figure>"
        )
    sections.append(
        '<section id="boards">\n<h2>Style boards</h2>\n'
        "<p>Style input only. These subjects are not part of the library.</p>\n"
        f'<div class="plates">{"".join(boards)}</div>\n</section>'
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Visual bible</title>
<style>
  :root {{ --paper: #f3efe6; --ink: #1c1a17; --rule: #d9d2c5; --muted: #5e584f; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--paper); color: var(--ink); font: 16px/1.45 Georgia, "Iowan Old Style", serif; }}
  .site {{ position: sticky; top: 0; z-index: 2; background: rgba(243, 239, 230, 0.96); border-bottom: 1px solid var(--rule); padding: 16px 24px 12px; }}
  h1 {{ font-size: 1.4rem; margin: 0; font-weight: 600; }}
  .lede, .meta {{ color: var(--muted); }}
  .lede {{ margin: 4px 0 10px; }}
  nav {{ display: flex; flex-wrap: wrap; gap: 14px; }}
  nav a {{ color: var(--ink); }}
  #q {{ margin-top: 10px; width: min(420px, 100%); font: inherit; padding: 6px 8px; border: 1px solid var(--rule); background: #fffdf8; }}
  main {{ padding: 8px 24px 64px; }}
  section {{ margin-top: 28px; }}
  h2 {{ font-size: 1.15rem; border-bottom: 1px solid var(--rule); padding-bottom: 6px; }}
  article {{ display: grid; grid-template-columns: minmax(220px, 320px) 1fr; gap: 8px 28px; padding: 22px 0; border-bottom: 1px solid var(--rule); }}
  h3 {{ margin: 0; font-size: 1.05rem; }}
  code {{ font-family: ui-monospace, monospace; font-size: 0.85em; color: var(--muted); }}
  .meta {{ margin: 4px 0; font-family: ui-monospace, monospace; font-size: 0.78rem; }}
  .plates {{ display: flex; flex-wrap: wrap; gap: 14px; align-items: flex-end; }}
  figure {{ margin: 0; }}
  button {{ display: block; padding: 0; border: 0; background: transparent; cursor: zoom-in; }}
  img {{ display: block; max-height: 280px; max-width: min(280px, 70vw); height: auto; background: #f7f4ee; }}
  figcaption {{ margin-top: 4px; font-family: ui-monospace, monospace; font-size: 0.75rem; color: var(--muted); }}
  dl {{ margin: 10px 0 0; }}
  dt {{ margin-top: 8px; font-size: 0.75rem; letter-spacing: 0.04em; text-transform: uppercase; color: var(--muted); }}
  dd {{ margin: 2px 0 0; }}
  li {{ margin: 2px 0; }}
  dialog {{ border: 0; padding: 16px 16px 20px; background: #f7f4ee; max-width: 96vw; max-height: 96vh; }}
  dialog::backdrop {{ background: rgba(28, 26, 23, 0.72); }}
  dialog img {{ max-height: calc(96vh - 88px); max-width: 92vw; }}
  dialog p {{ margin: 8px 0 0; font-family: ui-monospace, monospace; }}
  dialog form {{ display: flex; justify-content: flex-end; }}
  dialog form button {{ cursor: pointer; font: inherit; padding: 4px 8px; }}
  @media (max-width: 800px) {{ article {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<header class="site">
  <h1>Visual bible</h1>
  <p class="lede">{len(entities)} entities, {plate_count} plates. Click a plate to enlarge it.</p>
  <nav>{nav}</nav>
  <input id="q" type="search" placeholder="Filter by name, mark, or plate" aria-label="Filter">
</header>
<main>
{"".join(sections)}
</main>
<dialog id="viewer">
  <form method="dialog"><button>Close</button></form>
  <img alt="">
  <p></p>
</dialog>
<script>
  const viewer = document.querySelector("#viewer");
  const viewerImg = viewer.querySelector("img");
  const viewerCap = viewer.querySelector("p");
  document.querySelector("main").addEventListener("click", (event) => {{
    const button = event.target.closest("button[data-caption]");
    if (!button) return;
    const img = button.querySelector("img");
    viewerImg.src = img.src;
    viewerImg.alt = img.alt;
    viewerCap.textContent = button.dataset.caption;
    viewer.showModal();
  }});
  const query = document.querySelector("#q");
  query.addEventListener("input", () => {{
    const needle = query.value.trim().toLowerCase();
    document.querySelectorAll("article").forEach((article) => {{
      article.hidden = Boolean(needle) && !article.dataset.search.includes(needle);
    }});
  }});
</script>
</body>
</html>
"""


def write_registry() -> None:
    registry, marks = registry_outputs()
    REGISTRY_PATH.write_text(registry)
    MARKS_PATH.write_text(marks)
    INDEX_PATH.write_text(build_index(json.loads(registry)))
    print(f"wrote {rel(REGISTRY_PATH)}, {rel(MARKS_PATH)}, and {rel(INDEX_PATH)}")


# --- generation --------------------------------------------------------------


def load_env() -> None:
    if os.environ.get("GEMINI_API_KEY") or not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text().splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip())


def image_part(path: Path) -> dict:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return {"inline_data": {"mime_type": mime, "data": base64.b64encode(path.read_bytes()).decode("ascii")}}


def identity_block(spec: dict, label: str) -> str:
    lines = [f"{label}: {spec.get('name', spec['id'])}."]
    if spec["identity"]:
        lines.append(f"Identity: {spec['identity']}")
    if spec["required"]:
        lines.append("Must show: " + "; ".join(spec["required"]) + ".")
    if spec["forbidden"]:
        lines.append("Never show: " + "; ".join(spec["forbidden"]) + ".")
    return "\n".join(lines)


def style_anchors(spec: dict, specs: dict[str, dict], count: int = 2) -> list[Path]:
    kind = spec["kind"]
    paths = []
    for other in specs.values():
        if other["id"] == spec["id"] or other["kind"] != kind or other.get("status") != "approved":
            continue
        if kind == "character" and other["id"] == "lead":
            continue
        anchor = plate_path(other, anchor_name(other))
        if anchor.exists():
            paths.append(anchor)
        if len(paths) >= count:
            break
    return paths


def build_request(spec: dict, plate: str, specs: dict[str, dict]) -> list[dict]:
    kind = spec["kind"]
    templates = PLATE_TEMPLATES.get(kind)
    if not templates:
        raise LibraryError(f"{kind} plates are not generated by this tool")
    if plate not in templates:
        raise LibraryError(f"{kind} has no {plate!r} template. Use one of: {', '.join(templates)}")
    wearer = None
    if kind == "wardrobe":
        wearer_id = spec.get("wearer")
        if not wearer_id or wearer_id not in specs:
            raise LibraryError(f"{spec['id']} needs a wearer that is an approved character")
        wearer = specs[wearer_id]

    subject = templates[plate].format(
        name=spec.get("name", spec["id"]),
        wearer=wearer.get("name", wearer["id"]) if wearer else "",
    )
    text = [STYLE_LOCK, f"SUBJECT: {subject} Square frame. No text.", identity_block(spec, kind.title())]
    if wearer:
        text.append(identity_block(wearer, "Wearer"))
    parts: list[dict] = [{"text": "\n\n".join(text)}]

    for board in KIND_BOARDS[kind]:
        parts.append(image_part(ROOT / STYLE_BOARDS[board]))
    for path in style_anchors(spec, specs):
        parts.append(image_part(path))
        parts.append({"text": f"The image above is a style anchor only: a different {kind}. Match its ink, line weight, and use of empty paper. Do not copy its subject, and do not copy its spirals, curls, or dots."})
    if wearer:
        parts.append(image_part(plate_path(wearer, anchor_name(wearer))))
        parts.append({"text": f"The image above is the canonical {wearer.get('name', wearer['id'])}. Keep that face and those marks exactly."})

    anchor = anchor_name(spec)
    if plate != anchor:
        anchor_path = plate_path(spec, anchor)
        if not anchor_path.exists():
            library = library_specs().get(spec["id"])
            anchor_path = plate_path(library, anchor) if library else anchor_path
        if not anchor_path.exists():
            raise LibraryError(f"{spec['id']} has no anchor yet. Run anchor and pick first.")
        parts.append(image_part(anchor_path))
        parts.append({"text": f"The image above is the canonical {spec.get('name', spec['id'])}. Keep every mark identical. Change only the view described in SUBJECT. Do not reuse the same crop."})
    return parts


def generate(parts: list[dict], out: Path) -> str:
    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {"aspectRatio": "1:1", "imageSize": "1K"},
        },
    }
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]},
        method="POST",
    )
    last = "unknown error"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')[:300]}"
            if exc.code not in {429, 500, 503} or attempt == 3:
                return last
        except Exception as exc:  # noqa: BLE001 — network failures are retried, then reported
            last = str(exc)
            if attempt == 3:
                return last
        time.sleep(8 * (attempt + 1))
    else:
        return last
    for candidate in payload.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(base64.b64decode(inline["data"]))
                return f"wrote {rel(out)}"
    return "no image in response"


def run_jobs(jobs: list[tuple[list[dict], Path]], dry_run: bool) -> int:
    if dry_run:
        for parts, out in jobs:
            images = sum(1 for part in parts if "inline_data" in part)
            print(f"--- {rel(out)} ({images} images attached)\n{parts[0]['text']}\n")
        return 0
    load_env()
    if not os.environ.get("GEMINI_API_KEY"):
        raise LibraryError("GEMINI_API_KEY is missing")
    failures = 0
    with ThreadPoolExecutor(max_workers=3) as pool:
        for (parts, out), message in zip(jobs, pool.map(lambda job: generate(*job), jobs)):
            print(f"{rel(out)}: {message}", flush=True)
            failures += not message.startswith("wrote ")
    return 1 if failures else 0


# --- commands ----------------------------------------------------------------


def cmd_new(args) -> int:
    kind, entity_id = args.kind, args.id
    if kind not in ANCHORS:
        raise LibraryError(f"kind must be one of: {', '.join(ANCHORS)}")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", entity_id):
        raise LibraryError("id must be lowercase letters, digits, and hyphens")
    if entity_id in library_specs() or (DRAFTS / entity_id).exists():
        raise LibraryError(f"{entity_id!r} already exists")
    lines = [
        "---",
        f"id: {entity_id}",
        f"name: {entity_id}",
        f"kind: {kind}",
        "status: draft",
    ]
    if kind == "wardrobe":
        lines.append("wearer: TODO-character-id")
    lines += [
        f"anchor: {ANCHORS[kind]}.png",
        f"plates: [{', '.join(DEFAULT_PLATES[kind])}]",
        f"introduced_in: {args.episode or 'TODO'}",
        "---",
        "Identity: TODO one or two sentences: age, build, posture, everyday clothes.",
        "Required marks: TODO mark one; TODO mark two",
        "Forbidden marks: the lead's spiral earring; teardrop pendant; black vest",
        "",
    ]
    path = DRAFTS / entity_id / "spec.md"
    path.parent.mkdir(parents=True)
    path.write_text("\n".join(lines))
    print(f"wrote {rel(path)}. Fill in the TODO fields, then run: library.py anchor {entity_id}")
    return 0


def require_ready(spec: dict) -> None:
    text = spec["_path"].read_text()
    if "TODO" in text:
        raise LibraryError(f"{rel(spec['_path'])} still has TODO fields")
    specs = library_specs()
    others = [other for other in specs.values() if other["id"] != spec["id"]]
    errors = mark_collisions(others + [spec])
    if errors:
        raise LibraryError("\n".join(errors))


def cmd_anchor(args) -> int:
    spec, is_draft = find_spec(args.id)
    if not is_draft:
        raise LibraryError(f"{args.id} is already in the library. Its anchor is locked.")
    require_ready(spec)
    specs = library_specs()
    anchor = anchor_name(spec)
    parts = build_request(spec, anchor, specs)
    letters = string.ascii_lowercase[: max(1, min(args.candidates, 6))]
    jobs = [(parts, spec["_dir"] / f"{anchor}-{letter}.png") for letter in letters]
    code = run_jobs(jobs, args.dry_run)
    if not args.dry_run:
        print(f"Review the candidates, then run: library.py pick {args.id} <{'|'.join(letters)}>")
    return code


def cmd_pick(args) -> int:
    spec, is_draft = find_spec(args.id)
    if not is_draft:
        raise LibraryError(f"{args.id} is not a draft")
    anchor = anchor_name(spec)
    chosen = spec["_dir"] / f"{anchor}-{args.letter}.png"
    if not chosen.exists():
        raise LibraryError(f"{rel(chosen)} does not exist")
    rejected = spec["_dir"] / "rejected"
    for other in spec["_dir"].glob(f"{anchor}-?.png"):
        if other != chosen:
            rejected.mkdir(exist_ok=True)
            other.rename(rejected / other.name)
    chosen.rename(spec["_dir"] / f"{anchor}.png")
    print(f"{rel(spec['_dir'] / f'{anchor}.png')} is the anchor. Next: library.py pack {args.id}")
    return 0


def cmd_pack(args) -> int:
    draft = draft_spec(args.id)
    specs = library_specs()
    if draft:
        spec, out_dir = draft, draft["_dir"]
        require_ready(spec)
    elif args.id in specs:
        spec, out_dir = specs[args.id], DRAFTS / args.id
    else:
        raise LibraryError(f"no spec for {args.id!r}")
    anchor = anchor_name(spec)
    wanted = [item.strip() for item in args.plates.split(",")] if args.plates else spec["plates"]
    jobs = []
    for plate in wanted:
        if plate == anchor:
            continue
        out = out_dir / f"{plate}.png"
        if out.exists() and not args.force:
            print(f"skip {rel(out)}")
            continue
        if not draft and plate_path(spec, plate).exists() and not args.force:
            print(f"skip {plate}: already in the library (use --force to redraw into _drafts/)")
            continue
        jobs.append((build_request(spec, plate, specs), out))
    if not jobs:
        print("nothing to generate")
        return 0
    code = run_jobs(jobs, args.dry_run)
    if not args.dry_run:
        print(f"Review the plates in {rel(out_dir)}, then run: library.py promote {args.id}")
    return code


def cmd_promote(args) -> int:
    draft_dir = DRAFTS / args.id
    if not draft_dir.exists():
        raise LibraryError(f"no draft for {args.id!r}")
    specs = library_specs()
    draft = draft_spec(args.id)
    if draft:
        require_ready(draft)
        missing = [plate for plate in draft["plates"] if not plate_path(draft, plate).exists()]
        if missing:
            raise LibraryError(f"{args.id} is missing plates: {', '.join(missing)}")
        target = VB / KIND_DIRS[draft["kind"]] / args.id
        if target.exists():
            raise LibraryError(f"{rel(target)} already exists")
        target.mkdir(parents=True)
        shutil.copy2(draft["_path"], target / "spec.md")
        for plate in draft["plates"]:
            shutil.copy2(plate_path(draft, plate), target / f"{plate}.png")
        set_spec_field(target / "spec.md", "status", "approved")
    elif args.id in specs:
        spec = specs[args.id]
        new = sorted(path.stem for path in draft_dir.glob("*.png"))
        if not new:
            raise LibraryError(f"{rel(draft_dir)} has no plates to promote")
        for name in new:
            shutil.copy2(draft_dir / f"{name}.png", plate_path(spec, name))
        plates = spec["plates"] + [name for name in new if name not in spec["plates"]]
        set_spec_field(spec["_path"], "plates", f"[{', '.join(plates)}]")
    else:
        raise LibraryError(f"{rel(draft_dir)} has no spec.md and {args.id!r} is not in the library")
    shutil.rmtree(draft_dir)
    print(f"promoted {args.id}")
    write_registry()
    return 0


def cmd_registry(_args) -> int:
    write_registry()
    return 0


def cmd_check(_args) -> int:
    errors: list[str] = []
    try:
        specs = library_specs()
    except LibraryError as exc:
        print(f"FAIL {exc}")
        return 1

    for spec in specs.values():
        where = rel(spec["_path"])
        if spec.get("status") not in {"approved", "retired"}:
            errors.append(f"{where}: library entities must be approved or retired, not {spec.get('status')!r}")
        anchor = anchor_name(spec)
        if anchor not in spec["plates"]:
            errors.append(f"{where}: the anchor {anchor} is not listed in plates")
        for plate in spec["plates"]:
            if not plate_path(spec, plate).exists():
                errors.append(f"{where}: plate {plate}.png is missing")
        if spec["kind"] != "style" and not spec["required"]:
            errors.append(f"{where}: no required marks")
        if spec["kind"] == "wardrobe" and spec.get("wearer") not in specs:
            errors.append(f"{where}: wearer {spec.get('wearer')!r} is not a library character")
        for wardrobe in spec.get("wardrobe", []) or []:
            if wardrobe not in specs:
                errors.append(f"{where}: wardrobe {wardrobe!r} is not in the library")
    errors += mark_collisions(list(specs.values()))

    known = {}
    for spec in specs.values():
        for plate in spec["plates"]:
            known[rel(plate_path(spec, plate))] = spec
    for path in shot_files():
        where = rel(path)
        try:
            shots = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            errors.append(f"{where}: invalid JSON ({exc})")
            continue
        for shot in shots:
            shot_id = shot.get("id", "?")
            for ref in shot.get("references", []) or []:
                ref_path = ref.get("path", "")
                if "/_drafts/" in ref_path:
                    errors.append(f"{where} {shot_id}: references a draft {ref_path}")
                elif ref_path not in known:
                    errors.append(f"{where} {shot_id}: {ref_path} is not a library plate")
                elif known[ref_path].get("status") == "retired":
                    errors.append(f"{where} {shot_id}: {ref_path} belongs to a retired entity")
            for entity in shot.get("entities", []) or []:
                entity_id = entity.get("id")
                spec = specs.get(entity_id)
                if not spec or spec.get("status") != "approved":
                    errors.append(f"{where} {shot_id}: entity {entity_id!r} is not an approved library entity")
                    continue
                plate = entity.get("plate") or anchor_name(spec)
                if plate not in spec["plates"]:
                    errors.append(f"{where} {shot_id}: {entity_id} has no plate {plate!r}")

    registry, marks = registry_outputs()
    if not REGISTRY_PATH.exists() or REGISTRY_PATH.read_text() != registry:
        errors.append(f"{rel(REGISTRY_PATH)} is out of date. Run: library.py registry")
    if not MARKS_PATH.exists() or MARKS_PATH.read_text() != marks:
        errors.append(f"{rel(MARKS_PATH)} is out of date. Run: library.py registry")
    index = build_index(json.loads(registry))
    if not INDEX_PATH.exists() or INDEX_PATH.read_text() != index:
        errors.append(f"{rel(INDEX_PATH)} is out of date. Run: library.py registry")

    for error in errors:
        print(f"FAIL {error}")
    plates = sum(len(spec["plates"]) for spec in specs.values())
    print(f"{len(specs)} entities, {plates} plates, {len(shot_files())} shot files. {len(errors)} problem(s).")
    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="write a spec template into _drafts/")
    new.add_argument("kind", choices=list(ANCHORS))
    new.add_argument("id")
    new.add_argument("--episode", help="episode that introduces it, like E04")
    new.set_defaults(func=cmd_new)

    anchor = sub.add_parser("anchor", help="generate anchor candidates")
    anchor.add_argument("id")
    anchor.add_argument("--candidates", type=int, default=3)
    anchor.add_argument("--dry-run", action="store_true", help="print the prompt without calling the API")
    anchor.set_defaults(func=cmd_anchor)

    pick = sub.add_parser("pick", help="make one candidate the anchor")
    pick.add_argument("id")
    pick.add_argument("letter")
    pick.set_defaults(func=cmd_pick)

    pack = sub.add_parser("pack", help="generate plates from the anchor")
    pack.add_argument("id")
    pack.add_argument("--plates", help="comma-separated plate names; defaults to the spec's plates")
    pack.add_argument("--force", action="store_true", help="redraw plates that already exist")
    pack.add_argument("--dry-run", action="store_true", help="print the prompts without calling the API")
    pack.set_defaults(func=cmd_pack)

    promote = sub.add_parser("promote", help="move a reviewed draft into the library")
    promote.add_argument("id")
    promote.set_defaults(func=cmd_promote)

    sub.add_parser("registry", help="rebuild registry.json and marks.md").set_defaults(func=cmd_registry)
    sub.add_parser("check", help="validate the library and shot references").set_defaults(func=cmd_check)

    args = parser.parse_args()
    try:
        return args.func(args)
    except LibraryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
