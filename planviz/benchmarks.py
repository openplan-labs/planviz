"""Benchmark charts: scaling, coverage, where the time goes, and crossovers.

A benchmark plot is an argument, so the ink goes into the comparison. Three
rules from ``brand/figures.md`` are built in rather than left to the caller:

* **One loud line.** ``highlight`` gives the series being argued for the
  ``path`` accent; everything else takes the agent ramp as a supporting
  neutral. A chart where every series is loud makes no argument.
* **Spread, not just the middle.** Curves draw the median over seeds with a
  min–max band, because a median alone hides a bimodal solver.
* **Log axes say so.** Planner runtimes span four orders of magnitude, and a
  silent log axis is a way to be misleading by accident, so ``(log)`` is
  appended to the label.

Every function takes plain mappings — no benchmark harness type is imported —
and returns the axes or figure without saving it.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import numpy as np

from . import _common
from .style import style_context
from .tokens import Tokens

__all__ = [
    "scaling_curve",
    "success_heatmap",
    "phase_breakdown",
    "throughput_curve",
    "crossover_plot",
    "PHASE_HATCHES",
]

#: Hatch patterns, in assignment order. Colour alone separates four cool
#: blues badly in greyscale and for a colour-blind reader — cuda-planning
#: learned this when its H2D and D2H bands read identically — so a stacked
#: chart gets hatching as its second channel.
PHASE_HATCHES: tuple[str, ...] = ("", "///", "...", "\\\\\\", "xxx", "---", "+++")


def _samples(entry: Any, x: Sequence[float] | None):
    """Return ``(xs, median, low, high)`` for one series.

    Accepts ``{x: [samples over seeds]}``, ``{x: value}``, or a bare sequence
    of values paired with ``x``.
    """
    if hasattr(entry, "items"):
        xs = sorted(entry, key=float)
        median, low, high = [], [], []
        for key in xs:
            values = entry[key]
            if np.isscalar(values):
                values = [values]
            values = [float(v) for v in values if v is not None and v == v]
            if not values:
                continue
            median.append(statistics.median(values))
            low.append(min(values))
            high.append(max(values))
        xs = [float(key) for key in xs][: len(median)]
        return xs, median, low, high
    values = [float(v) for v in entry]
    xs = [float(v) for v in (x if x is not None else range(1, len(values) + 1))]
    return xs[: len(values)], values, values, values


def _log_axes(
    ax,
    tokens: Tokens,
    *,
    log_x: bool,
    log_y: bool,
    x_base: int,
    xlabel: str,
    ylabel: str,
    title: str | None,
):
    from matplotlib.ticker import FixedLocator, NullFormatter, ScalarFormatter

    if log_x:
        ax.set_xscale("log", base=x_base)
        ax.xaxis.set_major_formatter(ScalarFormatter())
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.xaxis.set_minor_locator(FixedLocator([]))
        if "log" not in xlabel:
            xlabel = f"{xlabel} (log)"
    if log_y:
        ax.set_yscale("log")
        if "log" not in ylabel:
            ylabel = f"{ylabel} (log)"
    return _common.finish(ax, tokens, title=title, xlabel=xlabel, ylabel=ylabel)


def scaling_curve(
    series: Mapping[str, Any],
    *,
    x: Sequence[float] | None = None,
    ax=None,
    dark: bool = False,
    highlight: str | None = None,
    band: bool = True,
    timeouts: Mapping[str, Sequence[float]] | None = None,
    cap: float | None = None,
    log_x: bool = False,
    log_y: bool = True,
    x_base: int = 2,
    marker: str = "o",
    legend: bool = True,
    xlabel: str = "agents",
    ylabel: str = "wall time (s)",
    title: str | None = None,
    figsize: tuple[float, float] | None = None,
):
    """Plot cost against problem size — one line per backend or planner.

    Each line is the **median over seeds** with a min–max band, which is the
    honest summary of a stochastic benchmark: a median alone hides a solver
    that is fast four times in five and pathological on the fifth.

    Runs that hit the time limit are drawn as their own mark — a hollow
    triangle at the cap — rather than extrapolated or silently dropped. A
    missing point and a timeout are different results and the figure should
    say which one it is.

    Args:
        series: ``{name: {x: [samples over seeds]}}``. A scalar per ``x``, or
            a bare sequence paired with ``x``, also works — with no band.
        x: shared x values, when ``series`` holds bare sequences.
        ax: draw into this axes instead of creating one.
        dark: use the dark scheme.
        highlight: the series being argued for; it takes the ``path`` accent.
        band: draw the min–max band.
        timeouts: ``{name: [x values that timed out]}``.
        cap: the time limit, where timeout marks are drawn. Defaults to the
            largest median in the figure.
        log_x: log-scale x (base ``x_base``) — usual for a doubling sweep.
        log_y: log-scale y.
        x_base: base of the x log scale.
        marker: marker on each measured point.
        legend: draw a legend.
        xlabel: x axis label.
        ylabel: y axis label.
        title: axes title.
        figsize: figure size when creating the axes.

    Returns:
        The :class:`~matplotlib.axes.Axes` drawn on.

    Example:
        >>> import matplotlib; matplotlib.use("Agg")
        >>> import planviz
        >>> ax = planviz.scaling_curve(
        ...     {
        ...         "cpu": {8: [0.4, 0.5], 16: [1.6, 1.9]},
        ...         "cuda": {8: [0.2, 0.2], 16: [0.3, 0.4]},
        ...     },
        ...     highlight="cuda",
        ...     timeouts={"cpu": [32]},
        ...     cap=10.0,
        ... )
        >>> ax.get_ylabel()
        'wall time (s) (log)'
    """
    names = list(series)
    with style_context(dark) as tokens:
        _, ax = _common.axes(ax, tokens, figsize or (6.8, 4.2))
        colors = _common.series_colors(names, tokens, highlight)
        peak = 0.0
        for name in names:
            xs, median, low, high = _samples(series[name], x)
            if not xs:
                continue
            peak = max(peak, max(median))
            ax.plot(
                xs, median, marker=marker, color=colors[name], linewidth=2.0,
                markersize=6, markeredgecolor=tokens.bg_raised,
                markeredgewidth=1.0, label=name, zorder=4,
            )
            spread = any(h > lo for lo, h in zip(low, high, strict=True))
            if band and len(xs) > 1 and spread:
                ax.fill_between(
                    xs, low, high, color=colors[name], alpha=0.15, lw=0, zorder=2
                )
        ceiling = cap if cap is not None else (peak or None)
        for name, xs in (timeouts or {}).items():
            points = [float(value) for value in xs]
            if not points or ceiling is None:
                continue
            ax.plot(
                points, [ceiling] * len(points), marker="^", markerfacecolor="none",
                markeredgecolor=colors.get(name, tokens.faint), linestyle="none",
                markersize=8, markeredgewidth=1.4, zorder=5,
                label=f"{name} (timeout)",
            )
        _log_axes(
            ax, tokens, log_x=log_x, log_y=log_y, x_base=x_base,
            xlabel=xlabel, ylabel=ylabel, title=title,
        )
        if legend:
            _common.legend(ax, tokens, loc="best")
    return ax


def success_heatmap(
    matrix: Any,
    *,
    x_labels: Sequence[str] | None = None,
    y_labels: Sequence[str] | None = None,
    ax=None,
    dark: bool = False,
    annotate: bool = True,
    vmin: float = 0.0,
    vmax: float = 1.0,
    missing: str = "—",
    percent: bool = True,
    xlabel: str = "agents",
    ylabel: str = "obstacle density",
    title: str | None = None,
    figsize: tuple[float, float] | None = None,
):
    """Draw coverage over a two-axis sweep — how often the solver succeeded.

    The ramp runs ``path`` (warm, nothing solved) to ``expanded`` (cool, all
    solved), which agrees with the rest of the system: warm is expensive.

    Cells with nothing to report are drawn as an em dash, not as zero. "No
    seed reported here" and "every seed failed here" are different claims, and
    a heatmap that conflates them is wrong in the direction that flatters the
    solver.

    Args:
        matrix: 2-D array-like of rates in ``[0, 1]``; ``None`` or ``NaN``
            marks a cell that was not measured.
        x_labels: column tick labels.
        y_labels: row tick labels.
        ax: draw into this axes instead of creating one.
        dark: use the dark scheme.
        annotate: write the rate in each cell.
        vmin: value mapped to the warm end.
        vmax: value mapped to the cool end.
        missing: text drawn in unmeasured cells.
        percent: format annotations as percentages.
        xlabel: x axis label.
        ylabel: y axis label.
        title: axes title.
        figsize: figure size when creating the axes.

    Returns:
        The :class:`~matplotlib.axes.Axes` drawn on.

    Example:
        >>> import matplotlib; matplotlib.use("Agg")
        >>> import planviz
        >>> ax = planviz.success_heatmap(
        ...     [[1.0, 1.0, 0.66], [1.0, 0.33, None]],
        ...     x_labels=["8", "16", "32"], y_labels=["5%", "15%"],
        ... )
        >>> ax.get_xlabel()
        'agents'
    """
    from matplotlib.colors import LinearSegmentedColormap

    values = np.array(
        [[np.nan if cell is None else float(cell) for cell in row] for row in matrix],
        dtype=float,
    )
    rows, cols = values.shape

    with style_context(dark) as tokens:
        _, ax = _common.axes(
            ax,
            tokens,
            figsize or (max(4.0, 0.7 * cols + 1.6), max(2.6, 0.6 * rows + 1.6)),
        )
        cmap = LinearSegmentedColormap.from_list(
            "coverage", [tokens.path, tokens.expanded], N=256
        )
        ax.imshow(
            np.ma.masked_invalid(values),
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            aspect="auto",
            interpolation="nearest",
        )
        if annotate:
            for row in range(rows):
                for col in range(cols):
                    value = values[row, col]
                    if np.isnan(value):
                        ax.text(
                            col, row, missing, ha="center", va="center",
                            fontsize=8.5, color=tokens.faint,
                        )
                    else:
                        text = f"{value:.0%}" if percent else f"{value:g}"
                        ax.text(
                            col, row, text, ha="center", va="center", fontsize=8.5,
                            color=tokens.bg_raised if value < 0.7 else tokens.heading,
                        )
        ax.set_xticks(range(cols))
        ax.set_xticklabels(
            list(x_labels) if x_labels else [str(i) for i in range(cols)]
        )
        ax.set_yticks(range(rows))
        ax.set_yticklabels(
            list(y_labels) if y_labels else [str(i) for i in range(rows)]
        )
        _common.finish(
            ax, tokens, title=title, xlabel=xlabel, ylabel=ylabel, grid_axis=None
        )
    return ax


def phase_breakdown(
    phases: Mapping[Any, Mapping[str, float]],
    *,
    order: Sequence[str] | None = None,
    accent: str | None = None,
    neutral: Iterable[str] = (),
    ax=None,
    dark: bool = False,
    normalize: bool = True,
    totals: bool = True,
    total_format: str = "{:.2f}s",
    legend: bool = True,
    xlabel: str = "batch size",
    ylabel: str | None = None,
    title: str | None = None,
    figsize: tuple[float, float] | None = None,
):
    """Stack where the wall time went, one bar per configuration.

    Bands are separated by **hatch as well as hue**. Four cool blues in a
    stack read identically in greyscale and to a colour-blind reader — this is
    the failure cuda-planning hit with its host-to-device and device-to-host
    bands — so the second channel is not optional here.

    Args:
        phases: ``{column label: {phase: seconds}}``, in column order.
        order: phases bottom to top; defaults to first-seen order.
        accent: the phase the figure is about — the useful work. It takes the
            ``path`` accent, so overhead is visibly everything else.
        neutral: phases drawn in ``faint`` — idle host time, unaccounted time.
        ax: draw into this axes instead of creating one.
        dark: use the dark scheme.
        normalize: stack fractions of each column's total rather than seconds.
        totals: write each column's absolute total above its bar. Keep this
            on with ``normalize``, or the figure loses its units.
        total_format: format string for those totals.
        legend: draw a legend below the axes.
        xlabel: x axis label.
        ylabel: y axis label; derived from ``normalize`` when omitted.
        title: axes title.
        figsize: figure size when creating the axes.

    Returns:
        The :class:`~matplotlib.axes.Axes` drawn on.

    Example:
        >>> import matplotlib; matplotlib.use("Agg")
        >>> import planviz
        >>> ax = planviz.phase_breakdown(
        ...     {
        ...         "64": {"kernel": 0.4, "h2d": 0.1, "d2h": 0.1, "host": 0.2},
        ...         "128": {"kernel": 1.1, "h2d": 0.2, "d2h": 0.2, "host": 0.3},
        ...     },
        ...     accent="kernel", neutral=["host"],
        ... )
        >>> ax.get_ylabel()
        'fraction of wall time'
    """
    columns = list(phases)
    if not columns:
        raise ValueError("phase_breakdown needs at least one column")
    seen: list[str] = []
    for column in columns:
        for phase in phases[column]:
            if phase not in seen:
                seen.append(phase)
    bands = list(order) if order else seen
    neutral = set(neutral)

    with style_context(dark) as tokens:
        _, ax = _common.axes(
            ax, tokens, figsize or (max(5.2, 1.1 * len(columns) + 2.4), 4.2)
        )
        ramp = [
            name for name in bands if name != accent and name not in neutral
        ]
        colors = {}
        for name in bands:
            if name == accent:
                colors[name] = tokens.path
            elif name in neutral:
                colors[name] = tokens.faint
            else:
                colors[name] = tokens.agent(ramp.index(name))

        positions = np.arange(len(columns))
        bottom = np.zeros(len(columns))
        for index, phase in enumerate(bands):
            heights = np.array(
                [
                    (
                        phases[column].get(phase, 0.0)
                        / max(sum(phases[column].values()), 1e-12)
                        if normalize
                        else phases[column].get(phase, 0.0)
                    )
                    for column in columns
                ]
            )
            ax.bar(
                positions,
                heights,
                bottom=bottom,
                width=0.62,
                label=phase,
                color=colors[phase],
                hatch=PHASE_HATCHES[index % len(PHASE_HATCHES)],
                edgecolor=tokens.bg_raised,
                linewidth=0.6,
                zorder=3,
            )
            bottom += heights
        if totals:
            for index, column in enumerate(columns):
                ax.annotate(
                    total_format.format(sum(phases[column].values())),
                    (positions[index], bottom[index]),
                    textcoords="offset points",
                    xytext=(0, 5),
                    ha="center",
                    fontsize=8.5,
                    color=tokens.muted,
                )
        ax.set_xticks(positions)
        ax.set_xticklabels([str(column) for column in columns])
        ax.set_ylim(0, float(bottom.max()) * 1.14)
        if ylabel is None:
            ylabel = "fraction of wall time" if normalize else "seconds"
        _common.finish(ax, tokens, title=title, xlabel=xlabel, ylabel=ylabel)
        if legend:
            _common.legend(
                ax,
                tokens,
                loc="upper center",
                bbox_to_anchor=(0.5, -0.16),
                ncol=min(len(bands), 4),
            )
    return ax


def throughput_curve(
    series: Mapping[str, Any],
    *,
    x: Sequence[float] | None = None,
    ax=None,
    dark: bool = False,
    highlight: str | None = None,
    band: bool = True,
    log_x: bool = True,
    log_y: bool = True,
    x_base: int = 2,
    legend: bool = True,
    xlabel: str = "batch size",
    ylabel: str = "items / s",
    title: str | None = None,
    note: str | None = "a rising line means the device is not yet saturated",
    figsize: tuple[float, float] | None = None,
):
    """Plot throughput against batch size — the saturation picture.

    Same data shape as :func:`scaling_curve`, different question. Wall time
    always rises with the batch; throughput is what says whether the device is
    working harder or just working longer, and a line that is still climbing
    at the right edge means the sweep stopped before saturation.

    Args:
        series: ``{name: {batch size: [samples]}}``.
        x: shared x values, when ``series`` holds bare sequences.
        ax: draw into this axes instead of creating one.
        dark: use the dark scheme.
        highlight: the series being argued for; it takes the ``path`` accent.
        band: draw the min–max band.
        log_x: log-scale x (base ``x_base``).
        log_y: log-scale y.
        x_base: base of the x log scale.
        legend: draw a legend.
        xlabel: x axis label.
        ylabel: y axis label.
        title: axes title.
        note: caption under the axes; pass ``None`` to drop it.
        figsize: figure size when creating the axes.

    Returns:
        The :class:`~matplotlib.axes.Axes` drawn on.

    Example:
        >>> import matplotlib; matplotlib.use("Agg")
        >>> import planviz
        >>> ax = planviz.throughput_curve(
        ...     {"cuda": {64: [1.2e5], 128: [2.1e5], 256: [2.4e5]}},
        ...     highlight="cuda",
        ... )
        >>> ax.get_xlabel()
        'batch size (log)'
    """
    ax = scaling_curve(
        series,
        x=x,
        ax=ax,
        dark=dark,
        highlight=highlight,
        band=band,
        log_x=log_x,
        log_y=log_y,
        x_base=x_base,
        legend=legend,
        xlabel=xlabel,
        ylabel=ylabel,
        title=title,
        figsize=figsize or (6.8, 4.2),
    )
    if note:
        with style_context(dark) as tokens:
            _common.caption(ax, tokens, note)
    return ax


def crossover_plot(
    ratios: Mapping[str, Any],
    *,
    x: Sequence[float] | None = None,
    ax=None,
    dark: bool = False,
    highlight: str | None = None,
    baseline: float = 1.0,
    baseline_label: str = "parity",
    log_x: bool = True,
    log_y: bool = True,
    x_base: int = 2,
    legend: bool = True,
    xlabel: str = "agents",
    ylabel: str = "baseline time ÷ candidate time",
    title: str | None = None,
    figsize: tuple[float, float] | None = None,
):
    """Plot speedup ratios and the size at which the ranking flips.

    A crossover chart is the only honest way to answer "is the GPU faster?" —
    the answer is a size, not a number. The parity line is drawn in ``faint``
    because it is a reference, not a result; above it the denominator wins.

    Ratios must come from instances **both** sides solved. Averaging a fast
    solver's successes against a slow solver's timeouts produces a speedup
    number that means nothing.

    Args:
        ratios: ``{name: {x: [ratio samples]}}`` or ``{name: {x: ratio}}``.
        x: shared x values, when ``ratios`` holds bare sequences.
        ax: draw into this axes instead of creating one.
        dark: use the dark scheme.
        highlight: the series being argued for; it takes the ``path`` accent.
        baseline: y value of the parity rule.
        baseline_label: label annotated on that rule.
        log_x: log-scale x (base ``x_base``).
        log_y: log-scale y — a ratio axis should be symmetric about parity,
            and only a log axis is.
        x_base: base of the x log scale.
        legend: draw a legend.
        xlabel: x axis label.
        ylabel: y axis label.
        title: axes title.
        figsize: figure size when creating the axes.

    Returns:
        The :class:`~matplotlib.axes.Axes` drawn on.

    Example:
        >>> import matplotlib; matplotlib.use("Agg")
        >>> import planviz
        >>> ax = planviz.crossover_plot(
        ...     {"prioritized": {8: [0.6], 16: [1.4], 32: [3.1]}},
        ...     highlight="prioritized",
        ... )
        >>> len(ax.lines) >= 2
        True
    """
    with style_context(dark) as tokens:
        _, ax = _common.axes(ax, tokens, figsize or (6.8, 4.2))
        ax.axhline(baseline, color=tokens.faint, linewidth=1.0, zorder=1)
        ax = scaling_curve(
            ratios,
            x=x,
            ax=ax,
            dark=dark,
            highlight=highlight,
            band=True,
            log_x=log_x,
            log_y=log_y,
            x_base=x_base,
            legend=legend,
            xlabel=xlabel,
            ylabel=ylabel,
            title=title,
        )
        if baseline_label:
            ax.annotate(
                baseline_label,
                xy=(1.0, baseline),
                xycoords=("axes fraction", "data"),
                textcoords="offset points",
                xytext=(-4, 4),
                ha="right",
                fontsize=8.5,
                color=tokens.muted,
            )
    return ax
