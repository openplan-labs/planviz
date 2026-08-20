"""API-shape checks that hold for every figure function at once.

They exist so a new figure cannot be added that quietly breaks the contract the
README states: takes ``ax=``, takes ``dark=``, returns the drawn object, and
never writes a file.
"""

from __future__ import annotations

import inspect

import matplotlib.pyplot as plt
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure

import planviz
from tests.conftest import EXPANDED, FRONTIER, GRID, PATH, PATHS, PHASES, SERIES, TREE

#: Every figure function, with a call that draws it on synthetic data.
CALLS = {
    "draw_grid": lambda **kw: planviz.draw_grid(GRID, **kw),
    "draw_paths": lambda **kw: planviz.draw_paths(PATHS, GRID, **kw),
    "draw_search": lambda **kw: planviz.draw_search(
        expanded=EXPANDED, frontier=FRONTIER, path=PATH, grid=GRID, **kw
    ),
    "search_progress": lambda **kw: planviz.search_progress(
        {"f": [1, 2, 3], "g": [0, 1, 2]}, **kw
    ),
    "radial_wavefront": lambda **kw: planviz.radial_wavefront(TREE, **kw),
    "plan_timeline": lambda **kw: planviz.plan_timeline(["a", "b", "c"], **kw),
    "scaling_curve": lambda **kw: planviz.scaling_curve(SERIES, **kw),
    "success_heatmap": lambda **kw: planviz.success_heatmap(
        [[1.0, 0.5], [0.25, None]], **kw
    ),
    "phase_breakdown": lambda **kw: planviz.phase_breakdown(PHASES, **kw),
    "throughput_curve": lambda **kw: planviz.throughput_curve(SERIES, **kw),
    "crossover_plot": lambda **kw: planviz.crossover_plot(SERIES, **kw),
}

#: Figure functions that own their whole figure rather than one axes.
FIGURE_LEVEL = {"search_panels"}

PUBLIC_FIGURES = sorted(CALLS) + sorted(FIGURE_LEVEL)


def test_every_public_figure_function_is_covered():
    """No public figure function may escape the contract tests below."""
    documented = {
        name
        for name in planviz.__all__
        if name.startswith(("draw_", "animate_"))
        or name
        in {
            "search_progress",
            "search_panels",
            "radial_wavefront",
            "plan_timeline",
            "scaling_curve",
            "success_heatmap",
            "phase_breakdown",
            "throughput_curve",
            "crossover_plot",
        }
    }
    covered = set(PUBLIC_FIGURES) | {"animate_paths", "animate_search"}
    assert documented == covered, f"uncovered: {sorted(documented - covered)}"


@pytest.mark.parametrize("name", sorted(CALLS))
def test_figure_functions_accept_a_caller_supplied_axes(name):
    polar = name == "radial_wavefront"
    figure = plt.figure()
    ax = figure.add_subplot(111, polar=polar)
    drawn = CALLS[name](ax=ax)
    assert drawn is ax, f"{name} must draw into the axes it was given"


@pytest.mark.parametrize("name", PUBLIC_FIGURES)
def test_figure_functions_take_dark_and_ax(name):
    signature = inspect.signature(getattr(planviz, name))
    assert "dark" in signature.parameters, f"{name} has no dark= parameter"
    assert signature.parameters["dark"].default is False
    if name not in FIGURE_LEVEL:
        assert "ax" in signature.parameters, f"{name} has no ax= parameter"
        assert signature.parameters["ax"].default is None


@pytest.mark.parametrize("name", sorted(CALLS))
def test_figure_functions_return_axes(name):
    assert isinstance(CALLS[name](), Axes)


def test_figure_level_functions_return_a_figure():
    figure = planviz.search_panels({"one": {"a": [1, 2, 3]}})
    assert isinstance(figure, Figure)


@pytest.mark.parametrize("name", sorted(CALLS))
def test_figure_functions_write_nothing(name, tmp_path, monkeypatch):
    """A figure function must never save or show; ``planviz.save`` does that."""
    monkeypatch.chdir(tmp_path)
    called = []
    monkeypatch.setattr(plt, "show", lambda *a, **k: called.append("show"))
    monkeypatch.setattr(Figure, "savefig", lambda *a, **k: called.append("savefig"))
    CALLS[name]()
    assert called == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("name", sorted(planviz.__all__))
def test_every_exported_name_resolves(name):
    assert getattr(planviz, name, None) is not None


@pytest.mark.parametrize("name", PUBLIC_FIGURES)
def test_every_figure_function_documents_an_example(name):
    doc = inspect.getdoc(getattr(planviz, name)) or ""
    assert ">>>" in doc, f"{name} has no docstring example"
    assert doc.splitlines()[0].endswith("."), f"{name} summary is not a sentence"


def test_version_is_a_release_number():
    parts = planviz.__version__.split(".")
    assert len(parts) == 3 and all(part.isdigit() for part in parts)
