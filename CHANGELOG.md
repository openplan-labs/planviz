# Changelog

All notable changes to this project are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-08-21

Initial release. Extracts the figure code duplicated across
[pymapf](https://github.com/openplan-labs/pymapf)'s `viz` package and
[cuda-planning](https://github.com/openplan-labs/cuda-planning)'s benchmark
charts into one installable library, and adds the search-progress figures
[PythonPDDL](https://github.com/openplan-labs/PythonPDDL) needs.

### Added

- `planviz.tokens` — the Frontier palette, vendored. `LIGHT`, `DARK`,
  `AGENT_RAMP`, `Tokens.agent(i)`, `Tokens.marker(i)`,
  `Tokens.sequential()`. Generated from `openplan-labs/branding` by
  `scripts/sync_tokens.py`, with a CI job that fails on drift.
- `planviz.use_style(dark=False)` and `planviz.style_context(dark=False)` —
  the vendored `frontier.mplstyle` plus a dark overlay. Importing `planviz`
  applies neither.
- **Grids and agents**: `draw_grid`, `draw_paths`, `draw_search`,
  `draw_heatmap`, `animate_paths`, `animate_search`. `planviz.MARKS` exposes
  the brand's legend as matplotlib keyword sets.
- **Search progress**: `search_progress`, `search_panels`,
  `radial_wavefront`, `plan_timeline`, `timeline_from_paths`, `Step`.
- **Benchmarks**: `scaling_curve` (median with a min–max band and explicit
  timeout marks), `success_heatmap`, `phase_breakdown` (stacked, separated by
  hatch as well as hue), `throughput_curve`, `crossover_plot`.
- **Output**: `save`, `save_animation` (GIFs capped at 12 fps and 800 px
  wide), `to_jshtml`.
- `examples/gallery.py` — renders one example of every figure, in both
  schemes, from seeded synthetic data. The committed gallery is what the
  README and docs show, and a test fails if the script stops producing it.
- [Migration guide](https://openplan-labs.github.io/planviz/migration/)
  mapping each existing `pymapf`, `cuplan` and `jupyddl` figure function onto
  a `planviz` call.

### Not included

Deliberate gaps, named so nobody looks for them:

- **Grouped bars** (`pymapf.plot_cost_comparison`,
  `jupyddl.plot_planner_comparison`) and a **parity scatter**
  (`cuplan._fig_quality`). Both are 0.2 candidates.
- **A 3-D space-time cube** (`pymapf.plot_spacetime`).
- **Live views.** `LiveSolveView` and `LiveSearchPlot` are solver observers,
  not figures, and belong with the solver they observe.
- **Solver adapters.** There is no `plot_solution(Solution)`; callers pass
  arrays and mappings, which is what lets one library serve four repositories.
- **A `STATUS` colour set.** Frontier has one accent and it means "the
  solution". A failed run is drawn as a mark — a hatched bar, an em dash, a
  hollow timeout triangle — not as a red.

[0.1.0]: https://github.com/openplan-labs/planviz/releases/tag/v0.1.0
