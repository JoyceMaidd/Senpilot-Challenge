"""zip_tool: compress the downloaded documents into a ZIP (or several, if they will not fit in one email)."""
from __future__ import annotations

import logging
import os
import zipfile
from typing import Optional

from .models import DownloadedFile, DownloadResult, ZipResult

log = logging.getLogger(__name__)

# AgentMail rejects a send whose base64 payload passes ~6 MB (measured: 4.3 MB of raw attachment
# sends, 5.5 MB fails). Stay under that with room for the message body.
MAX_ATTACHMENT_BYTES = 4_200_000


def _write_zip(files: list[DownloadedFile], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                zf.write(f.local_path, arcname=os.path.basename(f.local_path))
    except Exception:
        if os.path.exists(path):
            os.remove(path)
        raise


def _pack(files: list[DownloadedFile], limit: int) -> tuple[list[list[DownloadedFile]], list[DownloadedFile]]:
    """Greedy first-fit-in-order packing by raw size. Returns (groups, files that exceed the limit alone)."""
    groups: list[list[DownloadedFile]] = []
    sizes: list[int] = []
    too_large: list[DownloadedFile] = []
    for f in files:
        size = os.path.getsize(f.local_path)
        if size > limit:
            too_large.append(f)
            continue
        for i, used in enumerate(sizes):
            if used + size <= limit:
                groups[i].append(f)
                sizes[i] += size
                break
        else:
            groups.append([f])
            sizes.append(size)
    return groups, too_large


def make_zip(result: DownloadResult, out_dir: str, *, max_bytes: Optional[int] = MAX_ATTACHMENT_BYTES) -> ZipResult:
    """ZIP the successful downloads. No files -> no ZIP (zip_file=None, not an error).

    If the ZIP would be larger than `max_bytes`, the files are packed into several ZIPs
    (`..._part1.zip`, ...) that each fit; files that are too big on their own are reported
    in `too_large` and left out. Pass max_bytes=None to always make a single ZIP.
    """
    out = ZipResult(
        matter_number=result.matter_number,
        document_type=result.document_type,
        failed_downloads=result.failed_downloads,
    )
    if not result.downloaded_files:
        return out

    base = f"{result.matter_number}_{result.document_type.replace(' ', '_')}"
    single = os.path.join(out_dir, f"{base}.zip")
    try:
        _write_zip(result.downloaded_files, single)
        if max_bytes is None or os.path.getsize(single) <= max_bytes:
            out.zip_file = single
            return out

        os.remove(single)
        groups, out.too_large = _pack(result.downloaded_files, max_bytes)
        paths = []
        for i, group in enumerate(groups, 1):
            path = os.path.join(out_dir, f"{base}_part{i}.zip")
            _write_zip(group, path)
            if os.path.getsize(path) > max_bytes:  # compression can (rarely) grow already-compressed data
                log.warning("%s is %d bytes after zipping; sending anyway", path, os.path.getsize(path))
            paths.append(path)
        if len(paths) == 1:  # everything that fit is in one ZIP; no "part" naming needed for the user
            out.zip_file = paths[0]
        elif paths:
            out.zip_file, out.zip_parts = paths[0], paths
    except Exception as e:
        log.error("ZIP creation failed: %s", e)
        out.zip_file, out.zip_parts, out.too_large = None, [], []
        out.error_code = "ZIP_CREATION_FAILED"
    return out
