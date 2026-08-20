"""Style application, and the promise that it does not leak.

The leak matters more than it looks: ``planviz`` is meant to be depended on by
solver libraries, and a plotting helper that permanently repaints a caller's
notebook is a bug report waiting to happen.
"""

from __future__ import annotations

import subprocess
import sys

import matplotlib.pyplot as plt
import pytest

import planviz
from tests.conftest import GRID


def test_importing_planviz_changes_no_matplotlib_state():
    """A fresh interpreter's rcParams must survive ``import planviz``."""
    script = (
        "import matplotlib; matplotlib.use('Agg');"
        "import matplotlib.pyplot as plt;"
        "before = {k: repr(v) for k, v in plt.rcParams.items()};"
        "import planviz;"
        "after = {k: repr(v) for k, v in plt.rcParams.items()};"
        "changed = [k for k in before if before[k] != after[k]];"
        "print(changed)"
    )
    out = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    assert out.stdout.strip() == "[]", f"import side effects: {out.stdout}"


def test_style_context_restores_rcparams():
    before = plt.rcParams["axes.facecolor"]
    with planviz.style_context(dark=True) as tokens:
        assert plt.rcParams["axes.facecolor"] == tokens.bg_raised
        assert plt.rcParams["figure.facecolor"] == tokens.bg
    assert plt.rcParams["axes.facecolor"] == before


def test_drawing_a_figure_does_not_leak_style():
    """The autouse fixture would catch this, but say it explicitly."""
    before = dict(plt.rcParams)
    planviz.draw_grid(GRID, dark=True)
    assert repr(plt.rcParams["axes.facecolor"]) == repr(before["axes.facecolor"])


def test_use_style_applies_globally_and_is_reversible():
    original = dict(plt.rcParams)
    try:
        tokens = planviz.use_style(dark=False)
        assert tokens.mode == "light"
        assert plt.rcParams["axes.facecolor"] == tokens.bg_raised
        assert plt.rcParams["legend.frameon"] is False
        dark = planviz.use_style(dark=True)
        assert plt.rcParams["figure.facecolor"] == dark.bg
    finally:
        plt.rcParams.update(original)


def test_the_stylesheet_ships_inside_the_package():
    assert planviz.STYLE_PATH.is_file()
    assert planviz.STYLE_PATH.parent.name == "styles"
    text = planviz.STYLE_PATH.read_text()
    assert "axes.prop_cycle" in text


@pytest.mark.parametrize("dark", [False, True])
def test_a_saved_figure_keeps_its_ground_after_the_context_closes(dark, tmp_path):
    """The figure carries its own colours, not a borrowed rcParam."""
    from PIL import Image

    tokens = planviz.tokens.get(dark)
    ax = planviz.draw_grid(GRID, dark=dark)
    path = planviz.save(ax, tmp_path / "grid.png", dpi=50)
    corner = Image.open(path).convert("RGB").getpixel((1, 1))
    expected = tuple(int(tokens.bg[i : i + 2], 16) for i in (1, 3, 5))
    assert corner == expected
