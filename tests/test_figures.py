"""Every figure function renders on synthetic data, in light and in dark.

The assertions are deliberately shallow — a rendering library's most common
failure is an exception, not a wrong pixel — but they are not vacuous: each
figure is drawn into a caller-supplied axes as well as a fresh one, and then
actually rasterized to a file, which is where a bad colour string or an
unparsable hatch shows up.
"""

from __future__ import annotations

from matplotlib.axes import Axes
from matplotlib.figure import Figure

import planviz
from tests.conftest import (
    EXPANDED,
    FRONTIER,
    GRID,
    PATH,
    PATHS,
    PHASES,
    SERIES,
    TREE,
)


def _rendered(drawn, tmp_path, name):
    """Save ``drawn`` and assert the file is non-empty."""
    path = planviz.save(drawn, tmp_path / f"{name}.png")
    assert path.stat().st_size > 1000, f"{name} rendered an empty file"
    return path


def test_draw_grid(dark, tmp_path):
    ax = planviz.draw_grid(GRID, dark=dark, title="grid", lattice=True)
    assert isinstance(ax, Axes)
    assert ax.get_xlim() == (-0.5, 5.5)
    assert ax.get_ylim() == (5.5, -0.5)  # row 0 at the top
    _rendered(ax, tmp_path, f"grid-{dark}")


def test_draw_grid_from_shape_only(dark):
    ax = planviz.draw_grid(shape=(4, 7), dark=dark)
    assert ax.get_xlim() == (-0.5, 6.5)


def test_draw_heatmap_masks_obstacles(dark, tmp_path):
    values = [[float(r * c) for c in range(6)] for r in range(6)]
    ax = planviz.draw_heatmap(values, GRID, dark=dark, label="visits")
    assert len(ax.images) == 1
    assert ax.images[0].get_array().mask.any(), "blocked cells must be masked"
    _rendered(ax, tmp_path, f"heatmap-{dark}")


def test_draw_paths(dark, tmp_path):
    ax = planviz.draw_paths(PATHS, GRID, dark=dark, title="paths")
    assert isinstance(ax, Axes)
    _rendered(ax, tmp_path, f"paths-{dark}")


def test_draw_paths_accepts_a_bare_sequence(dark):
    ax = planviz.draw_paths(list(PATHS.values()), GRID, dark=dark)
    assert len(ax.lines) > 0


def test_draw_paths_highlight_uses_the_path_accent(dark):
    tokens = planviz.tokens.get(dark)
    ax = planviz.draw_paths(PATHS, GRID, dark=dark, highlight="beta")
    colors = {line.get_color() for line in ax.lines}
    assert tokens.path in colors
    assert tokens.faint in colors


def test_draw_paths_switches_to_density_past_eight_agents(dark):
    crowd = {str(i): [(i % 6, 0), (i % 6, 1)] for i in range(12)}
    ax = planviz.draw_paths(crowd, GRID, dark=dark)
    tokens = planviz.tokens.get(dark)
    strokes = [line for line in ax.lines if line.get_alpha() == 0.55]
    assert strokes and {line.get_color() for line in strokes} == {tokens.expanded}


def test_draw_search(dark, tmp_path):
    ax = planviz.draw_search(
        expanded=EXPANDED,
        frontier=FRONTIER,
        path=PATH,
        grid=GRID,
        dark=dark,
        title="search",
    )
    assert isinstance(ax, Axes)
    labels = {text.get_text() for text in ax.get_legend().get_texts()}
    assert {"expanded", "frontier", "path"} <= labels
    _rendered(ax, tmp_path, f"search-{dark}")


def test_draw_search_without_a_path_is_the_expansion_only_figure(dark):
    ax = planviz.draw_search(expanded=EXPANDED, frontier=FRONTIER, shape=(6, 6),
                             dark=dark, legend=False)
    assert ax.get_legend() is None


def test_search_progress(dark, tmp_path):
    ax = planviz.search_progress(
        {"f": [4, 4, 5, 6], "g": [0, 1, 2, 3], "h": [4, 3, 3, 3]},
        dark=dark,
        marks=[2],
        ylabel="cost",
        title="progress",
    )
    assert isinstance(ax, Axes)
    assert len(ax.lines) == 3 + 1  # three series plus the mark
    _rendered(ax, tmp_path, f"progress-{dark}")


def test_search_progress_log_label_says_so(dark):
    ax = planviz.search_progress({"n": [1, 10, 100]}, dark=dark, log_y=True,
                                 ylabel="nodes")
    assert ax.get_ylabel() == "nodes (log)"


def test_search_panels(dark, tmp_path):
    figure = planviz.search_panels(
        {
            "f, g and h": {"f": [4, 5, 6], "g": [0, 1, 2], "h": [4, 4, 4]},
            "open list": {"|open|": [1, 4, 7]},
        },
        dark=dark,
        fill=["open list"],
        suptitle="A* progress",
    )
    assert isinstance(figure, Figure)
    assert len(figure.axes) == 2
    _rendered(figure, tmp_path, f"panels-{dark}")


def test_radial_wavefront(dark, tmp_path):
    ax = planviz.radial_wavefront(TREE, frontier=[4], goal=5, dark=dark)
    assert ax.name == "polar"
    _rendered(ax, tmp_path, f"wavefront-{dark}")


def test_radial_wavefront_accepts_mappings_and_objects(dark):
    from types import SimpleNamespace

    as_dicts = [
        {"node": n, "parent": p, "depth": d, "h": v} for n, p, d, v in TREE
    ]
    as_objects = [
        SimpleNamespace(node=n, parent=p, depth=d, h=v) for n, p, d, v in TREE
    ]
    for records in (as_dicts, as_objects, [row[:3] for row in TREE]):
        assert planviz.radial_wavefront(records, dark=dark).name == "polar"


def test_plan_timeline_from_action_names(dark, tmp_path):
    ax = planviz.plan_timeline(
        ["pick-up(a)", "stack(a, b)", "pick-up(c)"], dark=dark, xlabel="step"
    )
    assert len(ax.patches) == 3
    _rendered(ax, tmp_path, f"plan-{dark}")


def test_plan_timeline_gantt_with_rows_and_waits(dark, tmp_path):
    steps = planviz.timeline_from_paths(PATHS)
    assert any(step.kind == "wait" for step in steps)
    assert any(step.kind == "idle" for step in steps)
    ax = planviz.plan_timeline(steps, dark=dark, highlight="alpha")
    assert len(ax.get_yticks()) == len(PATHS)
    _rendered(ax, tmp_path, f"gantt-{dark}")


def test_plan_timeline_truncates_long_plans(dark):
    ax = planviz.plan_timeline([f"op{i}" for i in range(200)], dark=dark,
                               max_steps=10)
    assert len(ax.patches) == 10


def test_scaling_curve(dark, tmp_path):
    ax = planviz.scaling_curve(
        SERIES,
        highlight="candidate",
        timeouts={"reference": [32]},
        cap=5.0,
        log_x=True,
        dark=dark,
    )
    assert ax.get_yscale() == "log"
    assert ax.get_xlabel() == "agents (log)"
    _rendered(ax, tmp_path, f"scaling-{dark}")


def test_scaling_curve_accepts_bare_sequences(dark):
    ax = planviz.scaling_curve(
        {"one": [1.0, 2.0, 4.0]}, x=[1, 2, 3], dark=dark, log_y=False
    )
    assert ax.get_yscale() == "linear"


def test_success_heatmap(dark, tmp_path):
    ax = planviz.success_heatmap(
        [[1.0, 1.0, 0.66], [1.0, 0.33, None]],
        x_labels=["8", "16", "32"],
        y_labels=["5%", "15%"],
        dark=dark,
    )
    texts = {text.get_text() for text in ax.texts}
    assert "—" in texts, "an unmeasured cell must not read as zero"
    _rendered(ax, tmp_path, f"success-{dark}")


def test_phase_breakdown_uses_hatch_as_a_second_channel(dark, tmp_path):
    ax = planviz.phase_breakdown(
        PHASES, accent="kernel", neutral=["host"], dark=dark
    )
    hatches = {patch.get_hatch() for patch in ax.patches}
    assert len(hatches) >= 4, "stacked bands must differ by more than hue"
    _rendered(ax, tmp_path, f"phases-{dark}")


def test_phase_breakdown_absolute(dark):
    ax = planviz.phase_breakdown(PHASES, dark=dark, normalize=False)
    assert ax.get_ylabel() == "seconds"


def test_throughput_curve(dark, tmp_path):
    ax = planviz.throughput_curve(
        {"cuda": {64: [1.2e5], 128: [2.1e5], 256: [2.4e5]}},
        highlight="cuda",
        dark=dark,
    )
    assert ax.get_xscale() == "log"
    _rendered(ax, tmp_path, f"throughput-{dark}")


def test_crossover_plot_draws_the_parity_rule(dark, tmp_path):
    ax = planviz.crossover_plot(
        {"prioritized": {8: [0.6], 16: [1.4], 32: [3.1]}},
        highlight="prioritized",
        dark=dark,
    )
    tokens = planviz.tokens.get(dark)
    assert any(line.get_color() == tokens.faint for line in ax.lines)
    _rendered(ax, tmp_path, f"crossover-{dark}")
