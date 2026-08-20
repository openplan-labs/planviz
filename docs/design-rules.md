# Design rules

The binding document is
[`brand/figures.md`](https://github.com/openplan-labs/branding/blob/main/brand/figures.md)
in the branding repository. This page is the subset `planviz` *enforces* — what
you get without asking, what you have to opt out of, and what the library
refuses to do — plus the line of code where each rule lives.

Rules the library cannot enforce (say what machine your benchmark ran on; cite
the paper) still apply. They are just not something a plotting function can
check.

## The legend is the palette

| Set | Token | Mark | Where |
| :--- | :--- | :--- | :--- |
| Unvisited | `faint` | dot, r 1.5 | `MARKS["unvisited"]` |
| Expanded | `expanded` | filled dot, r 2.5 | `MARKS["expanded"]` |
| Frontier | `frontier` | hollow ring, r 3, stroke 1.5 | `MARKS["frontier"]` |
| Path | `path` | connected stroke, w 2.5 | `MARKS["path"]` |
| Start | `path` | hollow ring, r 3.5 | `MARKS["start"]` |
| Goal | `path` | filled disc, r 3.5 | `MARKS["goal"]` |
| Obstacle | `line` | filled cell | `draw_grid` |

`planviz.MARKS` is that table as matplotlib keyword sets, so a figure this
library does not draw can still use the same marks:

```python
ax.plot(col, row, markeredgecolor=tokens.path, **planviz.MARKS["start"])
```

**The three semantic values are reserved words.** `path`, `frontier` and
`expanded` mean "the solution", "the open list" and "the closed list". A chart
that needs a second and third series takes `AGENT_RAMP`, and
[`series_colors`](api.md) never reaches for the reserved trio. If something
warm appears in a figure and it is not the answer, it is a bug.

## Shape carries the meaning, colour reinforces it

Every figure separates its sets on at least two channels:

- `draw_search` — filled dot / hollow ring / connected stroke. The path is the
  only *continuous* element, which is what survives greyscale printing.
- `draw_paths` — start is a hollow ring, goal a filled disc. No arrowheads.
- `phase_breakdown` — a hatch per band, assigned by position from
  `PHASE_HATCHES`. Four cool blues in a stack read identically in greyscale
  and to a colour-blind reader; `cuda-planning` shipped exactly that bug with
  its host-to-device and device-to-host bands before this rule was written.
- `plan_timeline` — waiting is hatched, parked-on-goal is faded. Both are
  drawn; neither is a gap.
- `tokens.marker(i)` — past eight agents the hue wraps but the marker does not.

## No gridlines under a grid map

`draw_grid` draws no lattice. The cells *are* the grid, and a lattice under an
occupancy map doubles the line count for zero information. `lattice=True` is
there for a small teaching figure where the cell boundaries are the point.

Charts do get a grid — y-axis only, `line` at 0.6 px, always behind the data
(`axes.axisbelow`).

## One idea per figure

`draw_search` draws expansion *and* result at full strength, which is right for
a legend plate and for the last frame of an animation. For a figure about
expansion order alone, pass `path=None`. For a comparison, use `search_panels`
and give each panel one idea.

## Multi-agent figures

Three rules, all enforced in `draw_paths` and `animate_paths`:

1. **Colour by stable index, never by iteration order.** `tokens.agent(i)` is
   indexed by position in the mapping you passed, so a re-render with fewer
   agents keeps everyone's colour.
2. **Past eight agents, stop colouring individually.** `CROWD = 8`; above it
   the figure switches to one colour at 0.55 opacity and captions itself
   "drawn by density, not by colour".
3. **When one agent is the subject, it takes `path` and the rest take
   `faint`.** That is what `highlight=` does.

## Plots are arguments

- **One loud line.** `highlight=` gives the series being argued for the `path`
  accent; everything else takes the agent ramp as a supporting neutral. A chart
  where every series is loud makes no argument.
- **Spread, not just the middle.** `scaling_curve` and `throughput_curve` draw
  the median over seeds with a min–max band, because a median alone hides a
  solver that is fast four times in five and pathological on the fifth.
- **Log scales say so.** Every log axis gets `(log)` appended to its label.
  Planner runtimes span four orders of magnitude and a silent log axis is a way
  to be misleading by accident.
- **Timeouts and gaps are different marks.** `scaling_curve(timeouts=...)`
  draws a hollow triangle at the cap; `success_heatmap` writes an em dash in a
  cell nothing reported. Neither is drawn as a zero, and neither is
  extrapolated.
- **Sequential data uses one hue.** `tokens.sequential()` runs `expanded` →
  `path`, warm meaning expensive. Never a rainbow, and never a diverging map
  for a quantity with no meaningful midpoint.
- **Axes are hairlines.** `line` at 1 px, labels in `body`, ticks in `muted`,
  no top or right spine, no chartjunk, no 3-D, no gradient fills.

## Animations

**The frontier moves, the expanded set accumulates, the path appears once at
the end and stays.** `animate_search` never clears the closed list: the
accumulated closed list is the cost of the search, and erasing it hides the
thing the figure is arguing about.

`save_animation` defaults to **12 fps and 800 px wide** for a GIF —
`GIF_FPS` and `GIF_WIDTH_PX` — and derives the DPI from the target width so
the cap holds whatever figure size produced the animation. They are read in a
GitHub README on a train.

`animate_search(frames=N)` resamples the expansion order, so a 20-node search
and a 200,000-node search produce clips of the same length.

## Accessibility, and the two binding consequences

From
[`brand/palette.md`](https://github.com/openplan-labs/branding/blob/main/brand/palette.md):

**`path` on light is exactly at the 4.5:1 threshold.** It has no headroom.
`planviz` never tints the ground under it — an axes face is always `bg_raised`,
never a wash — and never lightens it for emphasis.

**`expanded` is not a text colour on light.** 3.60:1 is fine for a 3 px node
marker and not fine for a label. Every label this library writes is `muted`,
`body` or `heading`; the only place `expanded` appears as text is nowhere.

`success_heatmap` switches its cell annotations between `bg_raised` and
`heading` at the point the ramp crosses into dark territory, so the number
stays readable at both ends.

## What the library will not do

- Draw a legend box where the marks already carry the mapping. `draw_search`
  has `legend=True` because it *is* the legend plate; every other figure
  prefers a direct label at the end of a line.
- Colour a figure by hue alone.
- Fade the expanded set out of an animation.
- Emit a rainbow colormap.
- Save or show a figure on your behalf.
