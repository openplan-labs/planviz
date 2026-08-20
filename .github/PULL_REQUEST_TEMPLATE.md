# What this changes

<!-- One or two sentences. Link the issue if there is one. -->

## Checklist

- [ ] `ruff check .` and `pytest` pass locally
- [ ] New or changed figure functions take `dark=` and `ax=`, return what they
      drew, and save nothing
- [ ] Public functions carry a docstring with an `Example:` block (pytest runs
      it)
- [ ] Sets in any new figure are separated by more than hue
- [ ] `python examples/gallery.py` re-run and `docs/assets/gallery` committed,
      if any figure changed
- [ ] `docs/gallery.md` updated for a new figure type
- [ ] `CHANGELOG.md` updated

## Does this change how existing figures look?

<!-- Downstream repositories commit their rendered figures, so a visual change
     shows up in their diffs. If yes, say which figures and why — and note it
     as a minor version bump, not a patch. -->
