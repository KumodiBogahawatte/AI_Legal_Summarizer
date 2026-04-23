"""
Resolve Google Drive links for NLR/SLR corpus PDFs (hosted deployments without local PDFs).

Expected artifact (generate with backend/scripts/list_gdrive_pdfs_recursive.py):
  data/corpus_google_drive_map.json

Legacy flat file still supported:
  data/gdrive_pdf_urls_recursive.json   # { "relative/path.pdf": "https://..." }
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config import DATA_DIR

_data_dir = Path(DATA_DIR)
_PREFERRED = _data_dir / "corpus_google_drive_map.json"
_LEGACY = _data_dir / "gdrive_pdf_urls_recursive.json"

_maps: Optional[Tuple[Dict[str, str], Dict[str, Dict[str, Any]]]] = None


def corpus_drive_map_paths() -> Tuple[Path, Path]:
    """Preferred and legacy map paths under DATA_DIR."""
    return _PREFERRED, _LEGACY


def corpus_drive_map_present() -> bool:
    """True if at least one Drive corpus map file exists (for Related Cases fallback)."""
    return _PREFERRED.is_file() or _LEGACY.is_file()


def _file_id_from_drive_url(url: str) -> Optional[str]:
    if not url or not isinstance(url, str):
        return None
    m = re.search(r"/file/d/([A-Za-z0-9_-]+)", url)
    if m:
        return m.group(1)
    m = re.search(r"[?&]id=([A-Za-z0-9_-]+)", url)
    if m:
        return m.group(1)
    return None


def _meta_from_url_string(url: str) -> Dict[str, Any]:
    fid = _file_id_from_drive_url(url)
    if not fid:
        return {"view_url": url, "download_url": url}
    return {
        "file_id": fid,
        "view_url": f"https://drive.google.com/file/d/{fid}/view",
        "download_url": f"https://drive.google.com/uc?export=download&id={fid}",
    }


def iter_drive_corpus_pdf_entries(max_entries: int = 25000) -> List[Dict[str, Any]]:
    """
    Flat list of corpus PDFs known to the Drive map (by_rel_path + by_file_name), deduped by basename.

    Each item: ``file_name``, ``rel_path`` (may equal file_name if only from by_file_name),
    ``drive_meta`` (file_id, view_url, download_url).
    Used when ``combined_legal_cases.json`` is absent: Related Cases can still rank by filename
    overlap against the uploaded judgment.
    """
    by_rel, by_name = _load_maps()
    out: List[Dict[str, Any]] = []
    seen_lower: set[str] = set()

    def push(file_name: str, rel_path: str, meta: Dict[str, Any]) -> None:
        kl = file_name.strip().lower()
        if not kl.endswith(".pdf") or kl in seen_lower:
            return
        seen_lower.add(kl)
        dm = dict(meta) if meta else {}
        if not dm.get("file_id") and dm.get("view_url"):
            fid = _file_id_from_drive_url(dm["view_url"])
            if fid:
                dm.setdefault("file_id", fid)
        out.append(
            {
                "file_name": file_name,
                "rel_path": rel_path,
                "drive_meta": dm,
            }
        )

    for rel, u in by_rel.items():
        rel_n = _norm_rel(rel)
        if not rel_n.lower().endswith(".pdf"):
            continue
        base = rel_n.split("/")[-1]
        kl = base.lower()
        row = dict(by_name.get(kl, {}))
        if not row and isinstance(u, str) and u:
            row = _meta_from_url_string(u)
        elif isinstance(u, str) and u and not row.get("view_url"):
            row = {**row, **_meta_from_url_string(u)}
        push(base, rel_n, row)
        if len(out) >= max_entries:
            return out

    for kl, meta in by_name.items():
        if not kl.endswith(".pdf") or kl in seen_lower:
            continue
        row = dict(meta) if isinstance(meta, dict) else {}
        # Display name: map keys are lowercased basenames
        file_name = row.get("file_name") or kl
        if not str(file_name).lower().endswith(".pdf"):
            file_name = kl if kl.endswith(".pdf") else f"{kl}.pdf"
        push(str(file_name), str(file_name), row)
        if len(out) >= max_entries:
            break

    return out


def _norm_rel(s: str) -> str:
    return (s or "").strip().replace("\\", "/")


def _load_maps() -> Tuple[Dict[str, str], Dict[str, Dict[str, Any]]]:
    global _maps
    if _maps is not None:
        return _maps

    by_rel: Dict[str, str] = {}
    by_name: Dict[str, Dict[str, Any]] = {}

    if _PREFERRED.is_file():
        with open(_PREFERRED, encoding="utf-8") as f:
            data = json.load(f)
        for k, v in (data.get("by_rel_path") or {}).items():
            key = _norm_rel(k)
            if isinstance(v, str) and v:
                by_rel[key] = v
            elif isinstance(v, dict):
                url = v.get("view_url") or v.get("download_url") or ""
                if url:
                    by_rel[key] = url
        for k, v in (data.get("by_file_name") or {}).items():
            if isinstance(v, dict) and k:
                by_name[k.strip().lower()] = v

    if _LEGACY.is_file():
        with open(_LEGACY, encoding="utf-8") as f:
            leg = json.load(f)
        if isinstance(leg, dict) and leg:
            sample = next(iter(leg.values()), None)
            if isinstance(sample, str):
                for k, v in leg.items():
                    if isinstance(v, str) and v:
                        by_rel.setdefault(_norm_rel(k), v)

    _maps = (by_rel, by_name)
    return _maps


def _finalize_drive_row(row: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(row)
    fid = out.get("file_id") or out.get("id")
    if fid and not out.get("view_url"):
        out["view_url"] = f"https://drive.google.com/file/d/{fid}/view"
    if fid and not out.get("download_url"):
        out["download_url"] = f"https://drive.google.com/uc?export=download&id={fid}"
    return out


def drive_meta_for_basename(file_name: str) -> Optional[Dict[str, Any]]:
    """Return drive file_id and URLs for a corpus PDF basename (e.g. Judgment.pdf)."""
    base = (file_name or "").strip().replace("\\", "/").split("/")[-1].lower()
    if not base:
        return None
    _, by_name = _load_maps()
    row = by_name.get(base)
    if not row:
        return None
    return _finalize_drive_row(row)


def drive_meta_resolve(file_name: str) -> Optional[Dict[str, Any]]:
    """
    Like ``drive_meta_for_basename`` but tries keys used on Drive (underscores, ``x_v_y.pdf``)
    when the display name uses spaces (``X v. Y.pdf``).
    """
    m = drive_meta_for_basename(file_name)
    if m:
        return m
    base = (file_name or "").strip().replace("\\", "/").split("/")[-1].lower()
    if not base or not base.endswith(".pdf"):
        return None
    stem = base[:-4]
    variants = [
        stem.replace(" ", "_") + ".pdf",
        re.sub(r"\s+", "_", base),
        re.sub(r"\s+v\.?\s+", "_v_", stem) + ".pdf",
        re.sub(r"\s+", "-", stem) + ".pdf",
        re.sub(r"[^a-z0-9]+", "_", stem).strip("_") + ".pdf",
    ]
    _, by_name = _load_maps()
    for v in variants:
        if v in by_name:
            return _finalize_drive_row(by_name[v])
    return None


def resolve_drive_pdf_url(path_or_basename: str) -> Optional[str]:
    """
    Resolve a single URL to open the PDF (prefers view in browser).
    Accepts full relative path from Drive listing or basename only.
    """
    meta = drive_meta_resolve(path_or_basename)
    if meta:
        u = meta.get("view_url") or meta.get("download_url")
        if u:
            return u

    key = _norm_rel(path_or_basename)
    by_rel, by_name = _load_maps()
    if key in by_rel and by_rel[key]:
        return by_rel[key]

    base = key.split("/")[-1].lower()
    if base in by_name:
        m = by_name[base]
        return m.get("view_url") or m.get("download_url")

    for rk, url in by_rel.items():
        if rk.lower().endswith("/" + base) or rk.split("/")[-1].lower() == base:
            return url
    return None
