"""Search progress, the radial wavefront, and plan timelines.

These are the pictures a single-agent planner needs — ``jupyddl``'s
``--plot``, ``--tree`` and ``--plan-plot`` in library form:

* :func:`search_progress` / :func:`search_panels` — how ``f``, ``g``, ``h``,
  the open-list size and the node counters moved as the search ran.
* :func:`radial_wavefront` — the search tree in polar coordinates: radius is
  depth, so a breadth-first flood is a disc and a greedy dive is a spoke.
* :func:`plan_timeline` — the returned plan as a Gantt, with waiting drawn as
  its own mark rather than as an absence.

None of them import a planner. A trace is a mapping of named series; a plan is
a sequence of steps; a tree is a flat sequence of ``(node, parent, depth)``
records where a parent may be a node that was never itself expanded.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

from . import _common
from .style import style_context
from .tokens import Tokens

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

__all__ = [
    "search_progress",
    "search_panels",
    "radial_wavefront",
    "plan_timeline",
    "Step",
    "timeline_from_paths",
]


# ---------------------------------------------------------------------------
# Search progress
# ---------------------------------------------------------------------------


def _draw_series(
    ax,
    series: Mapping[str, Sequence[float]],
    tokens: Tokens,
    *,
    x: Sequence[float] | None,
    highlight: str | None,
    fill: bool,
    end_labels: bool,
) -> None:
    names = list(series)
    colors = _common.series_colors(names, tokens, highlight)
    for name in names:
        ys = list(series[name])
        xs = list(x) if x is not None else list(range(1, len(ys) + 1))
        if not ys:
            continue
        color = colors[name]
        ax.plot(xs[: len(ys)], ys, color=color, linewidth=2.0, label=name)
        if fill:
            ax.fill_between(xs[: len(ys)], 0, ys, color=color, alpha=0.12, lw=0)
        if end_labels:
            # A direct label at the end of the line beats a legend box: the
            # reader's eye is already there.
            ax.annotate(
                name,
                (xs[len(ys) - 1], ys[-1]),
                textcoords="offset points",
                xytext=(8, 0),
                fontsize=9,
                color=tokens.muted,
                va="center",
                annotation_clip=False,
            )


def search_progress(
    series: Mapping[str, Sequence[float]],
    *,
    x: Sequence[float] | None = None,
    ax: Axes | None = None,
    dark: bool = False,
    highlight: str | None = None,
    marks: Sequence[float] | None = None,
    fill: bool = False,
    log_y: bool = False,
    end_labels: bool = True,
    legend: bool = False,
    xlabel: str = "nodes expanded",
    ylabel: str | None = None,
    title: str | None = None,
    figsize: tuple[float, float] | None = None,
) -> Axes:
    """Plot one line per named series against search progress.

    Use it for ``f``/``g``/``h`` over expansions, for the open-list size, for
    the cost of each expanded node, or for one line per planner. Colours come
    from the agent ramp; ``highlight`` promotes one series to ``path``, which
    is how the brand says a comparison should make its argument — one loud
    line, the rest supporting.

    Args:
        series: ``{name: values}``. Series may differ in length.
        x: shared x values; defaults to ``1..n``.
        ax: draw into this axes instead of creating one.
        dark: use the dark scheme.
        highlight: the series being argued for; it takes the ``path`` accent.
        marks: x positions to draw as dashed vertical rules — an IDA\\* bound
            restart, a replanning event, a timeout.
        fill: shade under each line. Sensible for a single frontier-size
            series, noisy for several.
        log_y: log-scale the y axis. It is labelled, because a silent log axis
            is a way to be misleading by accident.
        end_labels: annotate each line at its end instead of in a legend.
        legend: draw a legend box as well.
        xlabel: x axis label.
        ylabel: y axis label.
        title: axes title.
        figsize: figure size when creating the axes.

    Returns:
        The :class:`~matplotlib.axes.Axes` drawn on.

    Example:
        >>> import matplotlib; matplotlib.use("Agg")
        >>> import planviz
        >>> ax = planviz.search_progress(
        ...     {"f": [4, 4, 5, 5, 6], "g": [0, 1, 2, 3, 4], "h": [4, 3, 3, 2, 2]},
        ...     ylabel="cost",
        ... )
        >>> len(ax.lines)
        3
    """
    with style_context(dark) as tokens:
        _, ax = _common.axes(ax, tokens, figsize or (6.4, 4.0))
        _draw_series(
            ax, series, tokens, x=x, highlight=highlight, fill=fill,
            end_labels=end_labels,
        )
        for mark in marks or ():
            ax.axvline(
                mark, color=tokens.faint, linewidth=1.0, linestyle=(0, (4, 3)),
                zorder=0,
            )
        if log_y:
            ax.set_yscale("log")
            if ylabel and "log" not in ylabel:
                ylabel = f"{ylabel} (log)"
        _common.finish(ax, tokens, title=title, xlabel=xlabel, ylabel=ylabel)
        if legend:
            _common.legend(ax, tokens, loc="best")
        ax.margins(x=0.12 if end_labels else 0.02)
    return ax


def search_panels(
    panels: Mapping[str, Mapping[str, Sequence[float]]],
    *,
    x: Sequence[float] | None = None,
    dark: bool = False,
    ncols: int = 2,
    highlight: str | None = None,
    marks: Sequence[float] | None = None,
    fill: Sequence[str] = (),
    log_y: Sequence[str] = (),
    xlabel: str = "nodes expanded",
    ylabels: Mapping[str, str] | None = None,
    suptitle: str | None = None,
    figsize: tuple[float, float] | None = None,
) -> Figure:
    """Lay several :func:`search_progress` panels on one figure.

    One idea per panel, one figure per search. The panels share a colour
    assignment, so a series named the same way in two panels is the same
    colour in both.

    Args:
        panels: ``{panel title: {series name: values}}``, in draw order.
        x: shared x values for every panel.
        dark: use the dark scheme.
        ncols: panels per row.
        highlight: series promoted to the ``path`` accent in every panel.
        marks: x positions drawn as dashed rules in every panel.
        fill: titles of the panels to shade under.
        log_y: titles of the panels to log-scale.
        xlabel: x axis label, applied to the bottom row.
        ylabels: ``{panel title: y label}``.
        suptitle: figure title.
        figsize: figure size; derived from the panel count when omitted.

    Returns:
        The :class:`~matplotlib.figure.Figure`.

    Example:
        >>> import matplotlib; matplotlib.use("Agg")
        >>> import planviz
        >>> fig = planviz.search_panels({
        ...     "f, g and h": {"f": [4, 5, 6], "g": [0, 1, 2], "h": [4, 4, 4]},
        ...     "open list": {"|open|": [1, 4, 7]},
        ... })
        >>> len(fig.axes)
        2
    """
    import matplotlib.pyplot as plt

    titles = list(panels)
    if not titles:
        raise ValueError("search_panels needs at least one panel")
    ncols = max(1, min(ncols, len(titles)))
    nrows = (len(titles) + ncols - 1) // ncols

    with style_context(dark) as tokens:
        figure, axes = plt.subplots(
            nrows,
            ncols,
            figsize=figsize or (5.6 * ncols, 3.4 * nrows),
            squeeze=False,
        )
        figure.set_facecolor(tokens.bg)
        for index, title in enumerate(titles):
            ax = axes[index // ncols][index % ncols]
            ax.set_facecolor(tokens.bg_raised)
            _draw_series(
                ax,
                panels[title],
                tokens,
                x=x,
                highlight=highlight,
                fill=title in fill,
                end_labels=len(panels[title]) > 1,
            )
            for mark in marks or ():
                ax.axvline(
                    mark, color=tokens.faint, linewidth=1.0,
                    linestyle=(0, (4, 3)), zorder=0,
                )
            ylabel = (ylabels or {}).get(title)
            if title in log_y:
                ax.set_yscale("log")
                ylabel = f"{ylabel} (log)" if ylabel else "log scale"
            bottom = index // ncols == nrows - 1
            _common.finish(
                ax,
                tokens,
                title=title,
                xlabel=xlabel if bottom else "",
                ylabel=ylabel,
            )
            if len(panels[title]) == 1:
                _common.legend(ax, tokens, loc="best")
            ax.margins(x=0.1)
        for index in range(len(titles), nrows * ncols):
            axes[index // ncols][index % ncols].axis("off")
        if suptitle:
            figure.suptitle(
                suptitle, color=tokens.heading, fontsize=13, fontweight="semibold"
            )
        figure.tight_layout(rect=(0, 0, 1, 0.96 if suptitle else 1))
    return figure


# ---------------------------------------------------------------------------
# Radial wavefront
# ---------------------------------------------------------------------------


def _tree_records(nodes: Iterable) -> list[tuple[int, int, int, float]]:
    """Coerce tree records to ``(node, parent, depth, value)`` tuples."""
    out = []
    for index, record in enumerate(nodes):
        if hasattr(record, "depth") and not isinstance(record, (tuple, list)):
            node = int(getattr(record, "node", index))
            parent = int(getattr(record, "parent", -1))
            depth = int(record.depth)
            value = getattr(record, "value", None)
            if value is None:
                value = getattr(record, "h", math.nan)
        elif isinstance(record, Mapping):
            node = int(record.get("node", index))
            parent = int(record.get("parent", -1))
            depth = int(record["depth"])
            value = record.get("value", record.get("h", math.nan))
        else:
            fields = list(record)
            if len(fields) == 3:
                node, parent, depth = fields
                value = math.nan
            elif len(fields) == 4:
                node, parent, depth, value = fields
            else:
                raise ValueError(
                    "tree records are (node, parent, depth[, value]) tuples, "
                    f"got {len(fields)} fields"
                )
            node, parent, depth = int(node), int(parent), int(depth)
        out.append((node, parent, depth, float(value)))
    return out


def radial_wavefront(
    nodes: Iterable,
    *,
    frontier: Iterable[int] | None = None,
    goal: int | None = None,
    max_nodes: int = 4000,
    edges: bool = True,
    ax: Axes | None = None,
    dark: bool = False,
    value_label: str = "heuristic",
    title: str | None = None,
    figsize: tuple[float, float] | None = None,
) -> Axes:
    """Draw the search tree in polar coordinates — depth is radius.

    Nodes at the same depth are spread evenly around their ring, so the shape
    of the figure *is* the shape of the search: a uniform-cost flood fills a
    disc, a greedy best-first dive is a single spoke, and an A\\* with a good
    heuristic is a wedge aimed at the goal.

    Colour along the ``expanded`` → ``path`` ramp encodes ``value`` (the
    heuristic by default), warm meaning expensive. Nodes still on the open
    list take the frontier's hollow ring, so the legend still reads.

    Args:
        nodes: flat records of expanded nodes, in expansion order. Each is a
            ``(node, parent, depth)`` or ``(node, parent, depth, value)``
            tuple, a mapping with those keys, or an object with those
            attributes (``h`` is accepted for ``value``). ``parent`` is ``-1``
            at the root, and may name a node that was never expanded.
        frontier: ids of nodes still on the open list.
        goal: id of the goal node, marked with a filled disc.
        max_nodes: cap; beyond a few thousand rings the ink stops resolving.
        edges: draw parent→child edges. Turn them off for a dense search.
        ax: a **polar** axes to draw into; one is created when omitted.
        dark: use the dark scheme.
        value_label: colourbar label.
        title: axes title.
        figsize: figure size when creating the axes.

    Returns:
        The polar :class:`~matplotlib.axes.Axes` drawn on.

    Example:
        >>> import matplotlib; matplotlib.use("Agg")
        >>> import planviz
        >>> ax = planviz.radial_wavefront(
        ...     [(0, -1, 0, 3.0), (1, 0, 1, 2.0), (2, 0, 1, 2.5), (3, 1, 2, 1.0)],
        ...     goal=3,
        ... )
        >>> ax.name
        'polar'
    """
    records = _tree_records(nodes)[:max_nodes]
    if not records:
        raise ValueError("radial_wavefront needs at least one expanded node")

    with style_context(dark) as tokens:
        figure, ax = _common.axes(ax, tokens, figsize or (6.6, 6.2), polar=True)

        by_depth: dict[int, list[tuple[int, int, int, float]]] = {}
        for record in records:
            by_depth.setdefault(record[2], []).append(record)
        angle: dict[int, float] = {}
        radius: dict[int, int] = {}
        # Ring by ring, outwards, ordering each ring by its parents' angles.
        # Spreading a ring in expansion order instead draws every edge as a
        # chord across the disc, which hides the branching the figure is about.
        for depth in sorted(by_depth):
            group = sorted(by_depth[depth], key=lambda r: angle.get(r[1], 0.0))
            for slot, (node, _parent, _depth, _value) in enumerate(group):
                angle[node] = 2 * math.pi * (slot + 0.5) / len(group)
                radius[node] = depth

        if edges:
            for node, parent, _depth, _value in records:
                if parent < 0 or parent not in angle:
                    continue
                ax.plot(
                    [angle[parent], angle[node]],
                    [radius[parent], radius[node]],
                    color=tokens.line,
                    linewidth=0.6,
                    alpha=0.8,
                    zorder=2,
                )

        values = np.array([record[3] for record in records], dtype=float)
        finite = values[np.isfinite(values)]
        cmap = tokens.sequential()
        if finite.size and finite.max() > finite.min():
            norm = (values - finite.min()) / (finite.max() - finite.min())
        else:
            norm = np.full(values.shape, 0.5)
        norm = np.nan_to_num(norm, nan=0.5)
        scatter = ax.scatter(
            [angle[record[0]] for record in records],
            [radius[record[0]] for record in records],
            s=22,
            c=[cmap(v) for v in norm],
            edgecolors=tokens.bg_raised,
            linewidths=0.5,
            zorder=4,
        )
        scatter.set_label("expanded")

        if frontier:
            ids = [node for node in frontier if node in angle]
            if ids:
                ax.plot(
                    [angle[node] for node in ids],
                    [radius[node] for node in ids],
                    markeredgecolor=tokens.frontier,
                    marker="o",
                    markersize=6.0,
                    markerfacecolor="none",
                    markeredgewidth=1.5,
                    linestyle="none",
                    zorder=5,
                    label="frontier",
                )
        if goal is not None and goal in angle:
            ax.plot(
                angle[goal], radius[goal], marker="*", markersize=15,
                color=tokens.path, markeredgecolor=tokens.bg_raised,
                markeredgewidth=0.8, linestyle="none", zorder=6, label="goal",
            )

        ax.set_facecolor(tokens.bg_raised)
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.grid(True, color=tokens.line, linewidth=0.6, alpha=0.9)
        ax.spines["polar"].set_color(tokens.line)
        ax.spines["polar"].set_linewidth(1.0)
        ax.set_ylim(0, max(radius.values()) + 0.6)
        if title:
            ax.set_title(title, color=tokens.heading, fontweight="semibold", pad=16)
        _common.caption(
            ax,
            tokens,
            f"radius = depth · colour = {value_label} "
            f"({len(records)} nodes, {len(by_depth)} depths)",
            y=-0.06,
        )
        if frontier or goal is not None:
            _common.legend(ax, tokens, loc="upper right", bbox_to_anchor=(1.14, 1.10))
    return ax


# ---------------------------------------------------------------------------
# Plan timeline
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Step:
    """One segment of a plan timeline.

    Args:
        label: what to write on (or beside) the bar.
        start: when the step begins, in whatever unit the axis is in.
        duration: how long it lasts. Unit-duration steps give a staircase.
        row: the lane this step belongs to — an agent name, an object, or
            ``None`` for "a lane of its own".
        kind: ``"action"``, ``"wait"`` (hatched — a wait is a decision, not a
            gap) or ``"idle"`` (faint — parked, having finished).

    Example:
        >>> from planviz import Step
        >>> Step("move(a, b)", 0.0, 2.5, row="robot1").kind
        'action'
    """

    label: str
    start: float = 0.0
    duration: float = 1.0
    row: str | int | None = None
    kind: str = "action"


_KINDS = ("action", "wait", "idle")


def _steps(plan: Iterable) -> list[Step]:
    """Coerce a plan into :class:`Step` objects, filling in defaults."""
    out: list[Step] = []
    for index, item in enumerate(plan):
        if isinstance(item, Step):
            step = item
        elif isinstance(item, str):
            step = Step(item, float(index), 1.0)
        elif isinstance(item, Mapping):
            step = Step(
                str(item["label"]),
                float(item.get("start", index)),
                float(item.get("duration", 1.0)),
                item.get("row"),
                str(item.get("kind", "action")),
            )
        else:
            fields = list(item)
            if len(fields) == 3:
                step = Step(str(fields[0]), float(fields[1]), float(fields[2]))
            elif len(fields) == 4:
                step = Step(
                    str(fields[0]), float(fields[1]), float(fields[2]), fields[3]
                )
            elif len(fields) == 5:
                step = Step(
                    str(fields[0]),
                    float(fields[1]),
                    float(fields[2]),
                    fields[3],
                    str(fields[4]),
                )
            else:
                raise ValueError(
                    "plan steps are (label, start, duration[, row[, kind]]) "
                    f"tuples, got {len(fields)} fields"
                )
        if step.kind not in _KINDS:
            raise ValueError(f"kind must be one of {_KINDS}, got {step.kind!r}")
        out.append(step)
    if not out:
        raise ValueError("plan_timeline needs at least one step")
    return out


def plan_timeline(
    plan: Iterable,
    *,
    ax: Axes | None = None,
    dark: bool = False,
    highlight: str | int | None = None,
    max_steps: int = 60,
    annotate: bool = True,
    xlabel: str = "time",
    title: str | None = None,
    figsize: tuple[float, float] | None = None,
) -> Axes:
    """Draw a plan as a timeline — one bar per step, one lane per actor.

    Two shapes fall out of the same function. Give every step its own lane
    (the default for a plain list of action names) and you get a sequential
    plan read top to bottom. Give steps a ``row`` and you get a Gantt: one
    lane per agent, per resource, or per object.

    Waiting is drawn hatched rather than left blank, because waiting is where
    coordination cost shows up and an empty gap reads as "nothing happened".

    Args:
        plan: :class:`Step` objects, ``(label, start, duration[, row[, kind]])``
            tuples, mappings with those keys, or bare action names — which are
            taken as unit-duration steps in sequence.
        ax: draw into this axes instead of creating one.
        dark: use the dark scheme.
        highlight: the lane this figure is about; it takes the ``path`` accent
            and the others drop back.
        max_steps: truncate longer plans, with a note saying so.
        annotate: write each step's label on its bar when it has its own lane.
        xlabel: x axis label.
        title: axes title.
        figsize: figure size; derived from the lane count when omitted.

    Returns:
        The :class:`~matplotlib.axes.Axes` drawn on.

    Example:
        >>> import matplotlib; matplotlib.use("Agg")
        >>> import planviz
        >>> ax = planviz.plan_timeline(["pick(a)", "move(a, b)", "drop(a)"])
        >>> len(ax.patches)
        3
        >>> gantt = planviz.plan_timeline([
        ...     planviz.Step("move", 0, 2, row="r1"),
        ...     planviz.Step("wait", 2, 1, row="r1", kind="wait"),
        ...     planviz.Step("move", 0, 3, row="r2"),
        ... ])
        >>> len(gantt.get_yticks())
        2
    """
    from matplotlib.patches import Rectangle

    steps = _steps(plan)
    truncated = len(steps) > max_steps
    shown = steps[:max_steps]
    per_step_lanes = all(step.row is None for step in shown)

    lanes: list[Any] = []
    lane_of: dict[int, int] = {}
    for index, step in enumerate(shown):
        key = index if step.row is None else step.row
        if key not in lanes:
            lanes.append(key)
        lane_of[index] = lanes.index(key)

    with style_context(dark) as tokens:
        height = max(2.6, 0.34 * len(lanes) + 1.4)
        _, ax = _common.axes(ax, tokens, figsize or (8.4, height))

        if per_step_lanes:
            # A progression: the sequential ramp reads as "later is warmer".
            cmap = tokens.sequential()
            colors = [
                cmap(0.25 + 0.6 * i / max(1, len(shown) - 1))
                for i in range(len(shown))
            ]
            lane_color = {i: colors[i] for i in range(len(shown))}
        else:
            ramp = _common.series_colors(
                [str(lane) for lane in lanes],
                tokens,
                str(highlight) if highlight is not None else None,
            )
            if highlight is not None:
                ramp = {
                    name: (tokens.path if name == str(highlight) else tokens.faint)
                    for name in ramp
                }
            lane_color = {i: ramp[str(lane)] for i, lane in enumerate(lanes)}

        for index, step in enumerate(shown):
            lane = lane_of[index]
            color = lane_color[lane if not per_step_lanes else index]
            waiting = step.kind == "wait"
            idle = step.kind == "idle"
            ax.add_patch(
                Rectangle(
                    (step.start, lane - 0.3),
                    max(step.duration, 1e-9),
                    0.6,
                    facecolor=tokens.bg_raised if waiting else color,
                    edgecolor=color,
                    linewidth=1.1 if waiting else 0.0,
                    hatch="///" if waiting else None,
                    alpha=0.28 if idle else 1.0,
                    zorder=3,
                )
            )
            if annotate and per_step_lanes:
                ax.annotate(
                    step.label,
                    (step.start + step.duration, lane),
                    textcoords="offset points",
                    xytext=(6, 0),
                    va="center",
                    fontsize=8.5,
                    color=tokens.body,
                    family="monospace",
                    annotation_clip=False,
                )

        span = max(step.start + step.duration for step in shown)
        ax.set_xlim(0, span * (1.45 if (annotate and per_step_lanes) else 1.04))
        ax.set_ylim(len(lanes) - 0.4, -0.7)  # first lane on top
        ax.set_yticks(range(len(lanes)))
        if per_step_lanes:
            ax.set_yticklabels([str(i + 1) for i in range(len(lanes))], fontsize=8.5)
            ylabel: str | None = "step"
        else:
            ax.set_yticklabels([str(lane) for lane in lanes], fontsize=9)
            ylabel = None
        _common.finish(
            ax, tokens, title=title, xlabel=xlabel, ylabel=ylabel, grid_axis="x"
        )
        notes = []
        if any(step.kind == "wait" for step in shown):
            notes.append("hatched = waiting")
        if truncated:
            notes.append(f"first {max_steps} of {len(steps)} steps")
        if notes:
            _common.caption(ax, tokens, "  ·  ".join(notes), y=1.02)
    return ax


def timeline_from_paths(paths: Any, *, wait_label: str = "wait") -> list[Step]:
    """Turn multi-agent grid paths into :class:`Step` objects for a timeline.

    Contiguous runs of movement become ``"action"`` steps, runs where an agent
    stayed in place become ``"wait"`` steps, and the tail an agent spends
    parked on its goal after arriving becomes an ``"idle"`` step. That last
    distinction matters: a short path in a long plan is not a gap in the
    figure, it is an agent that finished early.

    Args:
        paths: ``{name: [(row, col), ...]}`` or a sequence of paths.
        wait_label: label written on wait segments.

    Returns:
        A list of :class:`Step`, ready for :func:`plan_timeline`.

    Example:
        >>> import planviz
        >>> steps = planviz.timeline_from_paths(
        ...     {"a": [(0, 0), (0, 1), (0, 1), (0, 2)], "b": [(1, 0), (1, 1)]}
        ... )
        >>> for step in steps:
        ...     if step.row == "a":
        ...         print(step.kind, step.start, step.duration)
        action 0.0 1.0
        wait 1.0 1.0
        action 2.0 1.0
    """
    routes = _common.as_paths(paths)
    horizon = max(len(path) for path in routes.values()) - 1
    steps: list[Step] = []
    for name, path in routes.items():
        start = 0
        while start < len(path) - 1:
            waiting = path[start] == path[start + 1]
            end = start + 1
            while (
                end < len(path) - 1
                and (path[end] == path[end + 1]) == waiting
            ):
                end += 1
            steps.append(
                Step(
                    wait_label if waiting else "move",
                    float(start),
                    float(end - start),
                    name,
                    "wait" if waiting else "action",
                )
            )
            start = end
        arrival = len(path) - 1
        if arrival < horizon:
            steps.append(
                Step("parked", float(arrival), float(horizon - arrival), name, "idle")
            )
    return steps
