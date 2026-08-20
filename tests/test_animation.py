"""Animations build, resample, and write a readable GIF in both schemes."""

from __future__ import annotations

import pytest
from matplotlib.animation import FuncAnimation

import planviz
from tests.conftest import EXPANDED, FRONTIER, GRID, PATH, PATHS


def test_animate_paths(dark):
    animation = planviz.animate_paths(PATHS, GRID, dark=dark, title="plan")
    assert isinstance(animation, FuncAnimation)
    assert sum(1 for _ in animation.new_frame_seq()) > 0


def test_animate_search_resamples_to_a_fixed_length():
    """A 9-node search and a 900-node search must give clips of one length."""
    long_search = [(row % 6, col % 6) for row in range(30) for col in range(30)]
    short = planviz.animate_search(EXPANDED, shape=(6, 6), frames=6)
    long = planviz.animate_search(long_search, shape=(6, 6), frames=6)
    assert sum(1 for _ in short.new_frame_seq()) == sum(
        1 for _ in long.new_frame_seq()
    )


def test_animate_search_reveals_the_path_last(dark):
    animation = planviz.animate_search(
        EXPANDED,
        frontiers=[FRONTIER] * len(EXPANDED),
        path=PATH,
        grid=GRID,
        start=PATH[0],
        goal=PATH[-1],
        dark=dark,
        frames=5,
    )
    tokens = planviz.tokens.get(dark)
    path_line = next(
        line for line in animation._fig.axes[0].lines
        if line.get_color() == tokens.path and line.get_linewidth() == 2.5
    )
    animation._func(0)
    assert len(path_line.get_xdata()) == 0, "the path must not appear in frame 0"
    animation._func(4)
    assert len(path_line.get_xdata()) == len(PATH)


def test_save_animation_writes_a_capped_gif(tmp_path, dark):
    pytest.importorskip("PIL")
    from PIL import Image

    animation = planviz.animate_search(EXPANDED, path=PATH, grid=GRID,
                                       dark=dark, frames=4)
    out = planviz.save_animation(animation, tmp_path / "search.gif")
    assert out.stat().st_size > 1000
    with Image.open(out) as image:
        assert image.width <= planviz.animate.GIF_WIDTH_PX + 8
        assert image.n_frames > 1


def test_to_jshtml_embeds_a_player():
    animation = planviz.animate_search(EXPANDED, shape=(6, 6), frames=3)
    html = planviz.to_jshtml(animation)
    assert html.lstrip().startswith("<")
    assert "animation" in html.lower()
