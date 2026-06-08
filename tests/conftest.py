from __future__ import annotations

from pathlib import Path

import pytest


def make_file(path: Path, content: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def make_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def project(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def helpers():
    return type("Helpers", (), {"make_file": staticmethod(make_file), "make_dir": staticmethod(make_dir)})
