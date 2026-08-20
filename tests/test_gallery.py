"""The gallery script runs end to end and writes non-empty images.

This is the closest thing to an integration test the library has: it renders
every figure from the synthetic instances in ``examples/data.py``, which is
also what produces the images committed under ``docs/assets/gallery``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
EXAMPLES = REPO / "examples"
GALLERY = REPO / "docs" / "assets" / "gallery"

sys.path.insert(0, str(EXAMPLES))


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    import gallery

    out = tmp_path_factory.mktemp("gallery")
    return out, gallery.render(out, animations=False, progress=lambda _: None)


def test_every_figure_renders_in_both_schemes(rendered):
    _, written = rendered
    assert len(written) >= 24
    assert sum(1 for path in written if path.name.endswith("-dark.png")) == (
        len(written) // 2
    )


def test_no_rendered_image_is_empty(rendered):
    _, written = rendered
    empty = [path.name for path in written if path.stat().st_size < 2000]
    assert not empty, f"suspiciously small images: {empty}"


def test_the_committed_gallery_matches_the_script(rendered):
    """The docs must not reference an image the script no longer produces."""
    out, written = rendered
    expected = {path.name for path in written}
    committed = {
        path.name for path in GALLERY.glob("*.png")
    } if GALLERY.is_dir() else set()
    missing = expected - committed
    assert not missing, (
        f"run `python examples/gallery.py` and commit: {sorted(missing)}"
    )


def test_the_committed_animations_exist():
    if not GALLERY.is_dir():
        pytest.skip("gallery not rendered in this checkout")
    for name in (
        "search-animation.gif",
        "search-animation-dark.gif",
        "paths-animation.gif",
        "paths-animation-dark.gif",
    ):
        path = GALLERY / name
        assert path.is_file() and path.stat().st_size > 10_000, name


def test_synthetic_astar_finds_a_path():
    import data

    grid = data.maze(21, 21)
    result = data.astar(grid, (1, 1), (19, 19))
    assert result["path"][0] == (1, 1)
    assert result["path"][-1] == (19, 19)
    assert len(result["expanded"]) == len(result["frontiers"])
    assert len(result["tree"]) == len(result["expanded"])
