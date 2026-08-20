# Migration

`planviz` was extracted from code that already exists in three repositories.
This page maps each of their functions onto a `planviz` call so the follow-up
work is mechanical rather than a redesign.

None of those repositories are changed by this package — releases are in
flight in all three. Nothing here is urgent; it is a plan.

The shape of every migration is the same:

1. Add `planviz>=0.1` to the `viz`/`benchmark` extra.
2. Delete the local theme module. Its palette is now `planviz.tokens`, and its
   `apply(...)` is `planviz.style_context(dark=...)`.
3. Replace each figure function body with a `planviz` call plus an **adapter**
   — a three-line function that turns the local problem type into an array or
   a mapping. The adapter is the only code that survives, and it belongs in
   the consuming repository, not here.
4. Keep the local wrapper's signature. Callers, tests and CLIs keep working.

## pymapf

Source: `pymapf/viz/` — `theme.py`, `plots.py`, `charts.py`, `animate.py`,
`live.py`.

### The adapters

Two, and they are the whole integration:

```python
# pymapf/viz/_adapt.py
import numpy as np

def occupancy(grid) -> np.ndarray:
    """GridMap -> a 2-D bool array, True where blocked."""
    return np.array(
        [[not grid.is_free((r, c)) for c in range(grid.width)]
         for r in range(grid.height)],
        dtype=bool,
    )

def routes(solution) -> dict:
    """Solution -> {agent name: [(row, col), ...]}."""
    return dict(solution.paths)
```

`solution.paths` is already `{name: [(row, col), ...]}`, so `routes` is an
alias kept for symmetry; `occupancy` is the real one.

### Static figures — `pymapf/viz/plots.py`

| pymapf | planviz | Notes |
| :--- | :--- | :--- |
| `plot_grid(source, ax, theme, title)` | `draw_grid(occupancy(grid), ax=, dark=, title=)` | Drop the lattice: `draw_grid` follows the brand and omits it. Pass `lattice=True` only for the small teaching figures. |
| `plot_scenario(scenario)` | `draw_grid(...)` + `MARKS["start"]` / `MARKS["goal"]` | No single call: a scenario is starts and goals with no routes yet. Six lines, below. |
| `plot_solution(solution, source)` | `draw_paths(solution.paths, occupancy(grid), ax=, dark=, title=)` | Rails, the panel-coloured underlay, start rings and goal discs, and the eight-agent density rule are all built in. The metrics sub-label moves to `ax.set_xlabel(...)` in the wrapper. |
| `plot_congestion(solution, source)` | `draw_heatmap(counts, occupancy(grid), label="agent-timesteps")` | `counts` is `solution.congestion()` densified to a 2-D array. `draw_heatmap` masks obstacles and uses the brand's single-hue ramp — the local `sequential_colormap` goes away. |
| `plot_timeline(solution)` | `plan_timeline(timeline_from_paths(solution.paths), xlabel="timestep")` | Exact replacement, including the hatched waits. `timeline_from_paths` additionally marks the parked-on-goal tail as `idle`, which the pymapf version drew as a 15%-alpha rectangle. |
| `compare_solutions(dict, source)` | `plt.subplots(...)` + `draw_paths(..., ax=axes[i])` | `planviz` has no panel-grid helper on purpose; the layout is the caller's. Ten lines in the wrapper. |
| `plot_spacetime(solution, source)` | **no equivalent** | The 3-D space-time cube stays in pymapf. It is the one figure in the repository that is genuinely pymapf-shaped. |
| `save(figure_or_ax, path, dpi)` | `planviz.save(figure_or_ax, path, dpi=)` | Same signature; returns a `Path` rather than a `str`. |

`plot_scenario`, in full:

```python
def plot_scenario(scenario, ax=None, dark=False, title=None):
    with planviz.style_context(dark) as t:
        ax = planviz.draw_grid(occupancy(scenario.grid), ax=ax, dark=dark)
        for index, agent in enumerate(scenario.agents):
            color = t.agent(index)
            ax.plot(agent.start[1], agent.start[0],
                    markeredgecolor=color, **planviz.MARKS["start"])
            ax.plot(agent.goal[1], agent.goal[0],
                    color=color, **planviz.MARKS["goal"])
    return ax
```

### Animations — `pymapf/viz/animate.py`

| pymapf | planviz |
| :--- | :--- |
| `animate_solution(solution, source, substeps=, trail=, hold_frames=)` | `animate_paths(solution.paths, occupancy(grid), substeps=, trail=, hold=)` — same easing, same trails, same goal rings |
| `save(animation, path, fps=20, dpi=120)` | `save_animation(animation, path, fps=12)` — note the **default drops to 12 fps**, which is the brand's README cap; pass `fps=20` to keep the old behaviour |
| `to_jshtml(animation)` | `planviz.to_jshtml(animation)` |
| `animate_search(trace, source)` | **partial.** `planviz.animate_search` animates a low-level grid search (accumulating closed list, moving frontier). pymapf's animates *CBS's high-level tree* — a map panel plus a cost chart, with conflict marks. Keep it locally; it can be composed from `draw_paths(ax=...)` and `search_progress(ax=...)` if it is ever rewritten. |

### Charts — `pymapf/viz/charts.py`

| pymapf | planviz | Notes |
| :--- | :--- | :--- |
| `plot_scaling(report, y=, x=, log_y=)` | `scaling_curve(series, log_y=, xlabel=, ylabel=)` | Build `series` as `{algorithm: {x: [values across instances]}}` instead of calling `aggregate(report, ...)`; `scaling_curve` does the median and adds the min–max band pymapf never had. |
| `plot_cost_curve(traces)` | `search_progress({label: trace.cost_curve()}, xlabel="expanded node", ylabel="sum of costs")` | Direct replacement, including the end-of-line direct labels. |
| `plot_success_rate(report)` | **partial** — `success_heatmap` covers a two-axis sweep, not one bar per algorithm. Either keep the local `barh`, styled from `planviz.tokens`, or reshape it into a one-row heatmap. |
| `plot_cost_comparison(report)` | **no equivalent** — grouped bars per scenario. Keep locally, styled from `planviz.tokens`. Tracked as a 0.2 candidate. |
| `dashboard(scaling, comparison)` | `plt.subplots(2, 2)` + four `planviz` calls with `ax=` | The one place a dashboard belongs is the repository that knows what belongs on it. |

### Theme — `pymapf/viz/theme.py`

Delete the file. It is a *different palette* from Frontier (`#2a78d6` blue,
`#eb6834` orange, a `#1a1a19` dark surface), so this is the one part of the
migration that visibly changes existing figures. That is the point of the
extraction.

| pymapf | planviz |
| :--- | :--- |
| `theme.apply("dark")` | `planviz.use_style(dark=True)`, or `style_context` inside a figure function |
| `theme.DARK` / `LIGHT` / `get_theme` | `planviz.tokens.DARK` / `LIGHT` / `tokens.get(dark)` |
| `Theme.agent_color(i)` / `agent_marker(i)` | `Tokens.agent(i)` / `Tokens.marker(i)` |
| `Theme.color_map(names)` | `Tokens.agent_colors(names)` |
| `theme.sequential_colormap(theme)` | `Tokens.sequential()` |
| `theme.STATUS` (`good`/`warning`/`serious`/`critical`) | **no equivalent, deliberately.** Frontier has one accent, and it means "the solution". A failed run is drawn as a *mark* — a hatched bar, an em dash, a hollow timeout triangle — not as a red. Where pymapf currently prints "failed" in `STATUS["critical"]`, use `tokens.muted` text plus the hatched bar. |

### Live views — `pymapf/viz/live.py`

`LiveSolveView` and `LiveConsoleView` are solver observers with a `on_expand`
callback, not figures. They stay in pymapf. Their colours can come from
`planviz.tokens` so the live view matches the saved figure.

## cuda-planning

Source: `cuplan/benchmark/figures.py` (898 lines). This is the largest
reduction: roughly 300 of those lines are palette, style resolution and
aggregation that `planviz` now owns.

### Delete outright

| Lines | What | Replacement |
| :--- | :--- | :--- |
| 32–49 | The `LIGHT` / `DARK` / `AGENT_RAMP` dicts, copied by hand from `tokens.json` | `planviz.tokens.LIGHT` / `DARK` / `AGENT_RAMP` |
| 51–54, 74–109 | `_MPLSTYLE_URL` and `_use_style(dark)` — which hunts for `tokens/frontier.mplstyle` in the CWD, then in a sibling checkout, then falls back to fetching it over HTTP | `with planviz.style_context(dark) as tokens:` — the stylesheet is inside the wheel, so the three-way fallback and the network call both go away |
| 125–167 | `_line_stats` and `_plot_series` — median, min–max band, timeout marks | `planviz.scaling_curve` |
| 169–179 | `_log_axes` | the `log_x` / `log_y` / `x_base` arguments |
| 549–569 | `_PHASE_COLORS` and `_PHASE_HATCH` | `phase_breakdown(accent=..., neutral=[...])` and `planviz.PHASE_HATCHES` |
| 603–636 | `_stacked_panel` | `phase_breakdown` |
| 470–481 | `_throughput_stats` | `throughput_curve` |
| 685–695 | `_speedup` | still needed — it pairs runs by `(n_agents, seed)` before dividing, which is data preparation, not drawing. Keep it; feed its output to `crossover_plot`. |

### Figure by figure

| cuplan | planviz |
| :--- | :--- |
| `_fig_family_scaling` | `plt.subplots(1, len(sizes), sharey=True)` + `scaling_curve(series, timeouts=, cap=, highlight="cuplan-cuda", log_x=True, ax=axes[i])` |
| `_fig_family_density` | same, one panel per density |
| `_fig_bfs_scaling`, `_fig_sim_scaling`, `_fig_headline` | `scaling_curve` |
| `_fig_success` | `success_heatmap(matrix, x_labels=agents, y_labels=densities, ax=axes[row][col])` — the em-dash for unmeasured cells and the contrast-switching annotations are built in |
| `_fig_phases`, `_fig_prioritized_phases` | `phase_breakdown(medians, order=["kernel", "h2d", "d2h", "host"], accent="kernel", neutral=["host"], ax=)` — the totals above the bars and the `1.14` headroom come with it |
| `_fig_throughput` | `throughput_curve(series, highlight="cuplan-cuda", ax=axes[i])` per panel |
| `_fig_crossover` | `crossover_plot(ratios, highlight=..., ax=axes[i])` — the parity `axhline` in `faint` is drawn for you |
| `_fig_quality` | **no equivalent** — the parity scatter (cost/makespan against pymapf, plus the CPU-vs-CUDA identity check). Keep locally, styled from `planviz.tokens`. Tracked as a 0.2 candidate. |
| `_note_lost` | keep. It is a data-provenance annotation ("this arm was lost to a device fault"), not a figure primitive, and only `cuplan` knows when it applies. |
| `_series_colors` (mapping `cuplan-cuda` to the path accent) | `highlight="cuplan-cuda"` |
| `render_all(data, out_dirs)` | unchanged in shape — still loops `for dark in (False, True)` and writes `<name>{-dark}.png`; the body just calls `planviz` |

The data shape is already right: `_line_stats` groups `SweepRecord`s by
`n_agents` and takes the median of `runtime` over seeds, which is exactly
`{solver: {n_agents: [runtime, ...]}}` — `scaling_curve`'s input.

```python
def series(records, solver):
    out = defaultdict(list)
    for r in records:
        if r.solver == solver and r.status == "solved":
            out[r.n_agents].append(r.runtime)
    return dict(out)

def timeouts(records, solver):
    return sorted({r.n_agents for r in records
                   if r.solver == solver and r.status == "timeout"})
```

## PythonPDDL (jupyddl)

Source: `jupyddl/viz/` — `plots.py` (914 lines), `theme.py`, `live.py`; plus
`jupyddl/benchmark.py:plot_summary`.

jupyddl's trace objects were the model for `planviz`'s search API, so several
calls need no adapter at all.

| jupyddl | planviz |
| :--- | :--- |
| `viz.theme.palette(dark)` | `planviz.tokens.get(dark)` |
| `viz.theme.rc_params(dark)` | `planviz.style_context(dark)` |
| `viz.theme.series_color(i, dark)` | `tokens.get(dark).agent(i)` |
| `viz.theme.sequential(fraction, dark)` | `tokens.get(dark).sequential()(fraction)` |
| `viz.theme.sequential_cmap(dark)` | `tokens.get(dark).sequential()` |

### `plot_search_tree(trace, path, dark, max_nodes=4000)` — `--tree`

**One call, no adapter.** `radial_wavefront` reads `.node`, `.parent`,
`.depth` and `.h` off objects, which is exactly what `SearchEvent` carries:

```python
def plot_search_tree(trace, path=None, dark=False, max_nodes=4000, title=None):
    goal = next((e.node for e in trace.of_kind("goal")), None)
    ax = planviz.radial_wavefront(
        trace.expansions, goal=goal, max_nodes=max_nodes,
        dark=dark, title=title or trace.label,
    )
    return _finish(ax.figure, path)
```

You also get two things the local version did not have: nodes in a ring are
ordered by their parent's angle, so edges stop crossing the disc as chords;
and the frontier can be drawn with the brand's hollow ring by passing
`frontier=[ids still on the open list]`.

### `plot_search_progress(trace, path, dark)` — `--plot`

`search_panels`, one dict per panel. The four panels map directly:

```python
events = trace.expansions
planviz.search_panels(
    {
        "f, g and h": {k: trace.series(k) for k in ("f", "g", "h")},
        "open list": {"|open|": trace.series("open_size")},
        "depth": {"depth": trace.series("depth")},
        "nodes": {
            "expanded": trace.series("expanded"),
            "generated": trace.series("generated"),
        },
    },
    marks=[at for at, _threshold in trace.bounds()],   # IDA* restarts
    fill=["open list"],
    log_y=["nodes"],
    dark=dark,
    suptitle=f"{trace.label} — {trace.task_name}",
)
```

`marks` replaces the hand-drawn `axvline` dashes; `fill` replaces the
`fill_between(alpha=0.12)`.

!!! note "`stride` is still not accounted for"
    `TraceRecorder` halves its sampling rate past `max_events`, so on a large
    search the x axis is the *recorded* expansion index, not the expansion
    count. `planviz` cannot know that. Pass
    `x=[i * trace.stride for i in range(len(events))]` and the axis becomes
    honest — a free fix worth making during the migration.

### `plot_plan_timeline(trace, path, dark, max_steps=40)` — `--plan-plot`

`trace.plan` is a `list[str]`, which is the bare form `plan_timeline` accepts:

```python
planviz.plan_timeline(trace.plan, max_steps=max_steps, dark=dark, xlabel="step")
```

The figure changes shape slightly and for the better: the local version drew
bar *length* as the cumulative step index, which encodes position twice; the
`planviz` one draws a real staircase of `(start, duration)` segments.

To get a *temporal* plan — the thing the function is named after —
`TraceRecorder.on_finish` has to stop flattening the plan to
`[op.name for op in plan]`. `Operator` already carries `.duration`, and
`Task.makespan(plan)` already replays the clock, so:

```python
# in TraceRecorder.on_finish
self.trace.plan = [(op.base_name, start, op.duration) for op, start in schedule]
```

feeds `plan_timeline` unchanged and produces a genuine Gantt. Add `row=` to
those tuples and it becomes one lane per object.

### The rest

| jupyddl | planviz |
| :--- | :--- |
| `plot_planner_comparison(traces)` panel D (h against normalized progress) | `search_progress({t.label: [e.h for e in t.expansions]}, x=percent_axis)` |
| `plot_planner_comparison` panels A–C (bar charts) | **no equivalent** — grouped/rounded bars. Keep locally, styled from `planviz.tokens`. |
| `plot_benchmark_dashboard(rows)` heatmap | `success_heatmap(matrix, x_labels=instances, y_labels=configs, percent=False)` for coverage; for the `log10(expanded)` grid, `draw_heatmap` is grid-shaped and does not fit — keep the local `imshow`, using `tokens.sequential()`. |
| `benchmark.plot_summary(rows, path, metric)` | delete. It is un-themed (`color="#4C72B0"`, a seaborn blue that appears nowhere in the brand), ignores `--dark`, and returns `None` instead of a figure. Fold it into the dashboard. |
| `rounded_bars(...)` | drop. Rounded bar corners are not in `brand/figures.md`, and the helper carries a hardcoded `surface="#fcfcfb"` default that duplicates a palette value. |
| `viz.live.animate_search(trace, path, fps, seconds)` | **no equivalent** — it animates chart panels, not a grid. Keep locally. Its frame-resampling trick (`cuts = [...]`) is the same one `planviz.animate_search(frames=N)` uses. |
| `LiveSearchPlot` | stays local — it is a `SearchObserver`. While you are there: `self._elapsed.append(len(self._steps))` makes the "milliseconds" axis of the live throughput panel actually the expansion count. `animate_search` gets it right with `e.elapsed * 1000`. |
| `web/charts.js` | out of scope — a separate SVG/canvas implementation for the Pyodide build, which cannot ship matplotlib. It duplicates the hex values from `theme.py` and has only six series slots against the brand's eight. If it is kept, generate its palette from `tokens.json` the way `scripts/sync_tokens.py` does, rather than by hand. |

## openplan-bench

New code, so there is nothing to migrate — build the cross-repository
comparison charts on `scaling_curve`, `success_heatmap` and `crossover_plot`
from the start, with `highlight=` naming whichever implementation the page is
arguing for.

## Known gaps

Three figures in the existing repositories have no `planviz` equivalent in
0.1.0. All three are honest gaps rather than oversights, and all three are
candidates for 0.2:

| Gap | Wanted by | Shape |
| :--- | :--- | :--- |
| Grouped bars | `pymapf.plot_cost_comparison`, `jupyddl.plot_planner_comparison` | one group per scenario, one bar per algorithm, failures hatched |
| Parity scatter | `cuplan._fig_quality` | two solvers on one instance set, with the `y = x` diagonal |
| 3-D space-time cube | `pymapf.plot_spacetime` | the map on the floor, time up the vertical axis |

Until then, keep those functions where they are and style them from
`planviz.tokens` — a local figure drawn in the brand's values is still on
brand.
