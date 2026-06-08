from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

SymlinkResult = Literal["created", "ok", "replaced"]


def ensure_symlink(link: Path, target: Path) -> SymlinkResult:
    """Create or update a relative symlink at ``link`` pointing at ``target``.

    Returns ``"created"`` if newly made, ``"ok"`` if already correct, or
    ``"replaced"`` if an existing symlink was repointed. Raises ``FileExistsError``
    if ``link`` exists as a real file or directory (we never overwrite user data).
    """
    rel = Path(os.path.relpath(target, start=link.parent))

    if link.is_symlink():
        current = Path(os.readlink(link))
        if current == rel:
            return "ok"
        link.unlink()
        link.symlink_to(rel)
        return "replaced"

    if link.exists():
        raise FileExistsError(
            f"{link} already exists as a real file or directory; refusing to overwrite. "
            f"Move or remove it manually, then re-run `mh init`."
        )

    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(rel)
    return "created"
