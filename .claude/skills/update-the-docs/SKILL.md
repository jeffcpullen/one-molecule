---
name: update-the-docs
description: Refresh the Diataxis documentation under design/docs/ from changes in the design/data/ corpus. Detects which design sources changed since docs were last synced (via git), maps them to the pages that own them through documentation-plan.yml, dispatches the om-docs-maintainer agent per affected page, reconciles cross-links and consistency, then gates on your review before committing. Use on "update the docs", "sync docs from design", or after editing design sources. Optional arg scopes the run: "all", a page name, or a design file.
argument-hint: "[all | <page> | <design-file>]"
user-invocable: true
metadata:
  author: local
  version: 1.2.0
---

# update-the-docs

Sync `design/docs/` from changes in `design/data/`.

Drive an **incremental** refresh of `design/docs/` from the `design/data/` corpus. The design is the
source of truth and `design/docs/` is its user-altitude Diataxis projection. The heavy per-page writing
is delegated to the **`om-docs-maintainer`** agent. This skill is the orchestration and change detection
around it.

Repo root is the one-molecule checkout you are running in. All of `design/` is git-tracked and all
working material lives in the gitignored repo-root `internal/`.
**`design/data/` is read-only source. Never edit it here.**

## Steps

1. **Read the plan and build the reverse map.** Read `design/data/documentation-plan.yml`. Its tables map
   design docs onto Diataxis quadrants. Resolve each owning doc to its source: a doc `<doc>` is read as
   `design/data/<doc>.yml`, and a subfolder doc is read directly at its `.md`. Combine that with the
   fixed quadrant to file map to get **design doc to page**:
   - Explanation rows map to `design/docs/explanation.md`
   - Reference rows map to `design/docs/reference.md`
   - How-to rows map to `design/docs/migrating.md`
   - Tutorial rows map to `design/docs/getting-started.md`
   - `design/docs/the-pattern.md` is the **human-owned authoring surface**. Update it only if the user
     explicitly asks. Otherwise it is only a cross-link target.

2. **Detect what changed since docs were last synced (git).** `design/docs/` only changes when this skill
   runs, so the last commit touching it is the last sync point. Find it and diff the design sources
   against it:
   - Baseline: `git -C <root> log -1 --format=%H -- design/docs` gives the last sync commit.
   - Changed owning docs are the design sources that changed **since** that commit, committed or not:
     `git -C <root> diff --name-only <baseline> -- 'design/data/*.yml'` **plus** the uncommitted
     working-tree changes from `git -C <root> status --porcelain -- 'design/data/*.yml'`. A changed
     `design/data/<doc>.yml` maps to the owning doc `<doc>`.
   - Map the changed docs to pages via step 1. Those pages are in scope.
   - **The arg overrides the diff.** `all` forces every page. A page name scopes to that page. A design
     filename scopes to the page or pages that own it.
   - **No baseline** (docs never committed) means a full first pass. Tell the user and offer to scope
     down.
   - If nothing changed and there is no arg, say so and stop. Do not churn the docs.

3. **Dispatch per affected page.** For each in-scope page, launch an `om-docs-maintainer` agent with the
   page path, the owning design docs that changed, and a one-line note on *what* changed. Independent
   pages run in parallel, as multiple Agent calls in one message. Each agent reconciles surgically,
   grounds every claim, holds the voice and honesty rules, and returns a structured report without
   pasting contents.

4. **Reconciliation pass.** This is the fix for parallel authoring. After the page agents land, do a
   single sweep across the changed set: cross-links resolve (each page to its siblings and to
   `the-pattern.md`, no dead anchors), no quadrant duplication, tells scrub clean, prose agrees with the
   in-page code and YAML, line width sane. Fix small drift here rather than re-dispatching.

5. **Run the repo gates.** `python3 tools/build.py --check` and `pre-commit run --all-files` from the
   repo root. Read the output. Green gates are the evidence, not an assertion that the pages look right.

6. **Gate before commit (non-negotiable).** Open the changed docs for the user and show a short per-page
   summary of what changed and why. **Wait for an explicit go.** Do not commit or push on your own. On
   the go, commit the design changes and the docs together, with a message describing the design to docs
   sync, and push in the same turn. The combined commit becomes the next run's baseline.

## Guardrails

- Never edit `design/data/`, `design/structure/`, `spec/`, or `design/docs/the-pattern.md`, the last
  unless the user explicitly asks.
- Reconcile, do not blindly regenerate. Preserve human edits already in a page.
- Honesty holds end to end. Proposed is not shipped. A stub gets shape only, never invented specifics.
- Keep design rationale out of `design/docs/`. The pages restate the user-facing slice, not the thread
  on why an alternative lost. The status of a design item lives in its owning design doc.
