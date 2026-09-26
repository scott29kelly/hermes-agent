---
title: "Dream Loop — Build visuals until a screenshot matches a target image"
sidebar_label: "Dream Loop"
description: "Build visuals until a screenshot matches a target image"
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Dream Loop

Build visuals until a screenshot matches a target image.

## Skill metadata

| | |
|---|---|
| Source | Optional — install with `hermes skills install official/creative/dream-loop` |
| Path | `optional-skills/creative/dream-loop` |
| Version | `1.0.0` |
| Author | Anshu Chimala (@achimala) + Hermes Agent |
| License | MIT |
| Platforms | linux, macos, windows |
| Tags | `creative`, `3d`, `game-dev`, `threejs`, `webgl`, `image-generation`, `visual-fidelity`, `fal` |
| Related skills | [`p5js`](/docs/user-guide/skills/bundled/creative/creative-p5js), [`claude-design`](/docs/user-guide/skills/bundled/creative/creative-claude-design) |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Hermes loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Dream Loop Skill

Dream Loop builds a game, app, or 3D scene to a very high level of graphical
fidelity by closing a loop: generate a "dream" target screenshot with image
generation, build toward it, compare a live screenshot against the target
(ideally with an independent judge subagent), and iterate until they match.
It is a process skill, not a framework — it does not ship a renderer or an
engine, only the workflow plus two small helpers (a screenshot-capturing
preview server and a Fal image-to-3D batch client).

## When to Use

- The user says "dream loop" or asks for something built to match a target
  image as closely as possible.
- The user asks for a game, graphics demo, or app where visual quality is the
  headline requirement (e.g. "make it look like a real in-engine screenshot").
- An existing visual product needs a large fidelity upgrade toward a refined
  target rather than incremental tweaks.

Do **not** use it for ordinary UI work with no visual target, for static
image generation alone, or when the user wants a quick rough prototype.

## Prerequisites

- **Image generation** — the `image_gen` toolset (`image_generate`). Image
  editing (passing `image_url`) is needed to refine an existing product's
  screenshot and to extract per-asset source images; the tool description
  says whether the active model supports it. If image generation is not
  available and the user did not supply a target image, stop and ask for one
  (or for an image backend to be configured via `hermes tools`).
- **Vision** — `vision_analyze` to read screenshots and the target.
- **Subagents** — `delegate_task` (strongly preferred for the judge / worker
  roles; children inherit the parent's toolsets, so enable `vision` and
  `image_gen` before starting).
- **Node 18+** for `scripts/fal-batch.mjs`, **Python 3** for
  `scripts/preview-server.py`.
- **Optional:** `FAL_KEY` (or `FAL_API_KEY`) for image-to-3D assets — the
  same credential Hermes' FAL image backend uses, configured through
  `hermes tools`. Blender
  (Pro workflow only) for custom modeling via its Python scripting interface.

## How to Run

1. Pick the workflow (see Procedure step 1) and read **only** that workflow's
   file with `read_file`:
   - Pro: `references/pro-mode/workflow.md`
   - Plus: `references/plus-mode/workflow.md`
2. For browser-rendered work, serve the project with the capture server so
   the page can POST canvas frames:

   ```bash
   python3 SKILL_DIR/scripts/preview-server.py --directory <project> --port 4172
   ```

   Run it with `terminal(background=true)`. The page posts a PNG (e.g.
   `canvas.toBlob(b => fetch('/__capture', {method: 'POST', body: b}))`, with
   `preserveDrawingBuffer: true` on WebGL renderers) and the server writes
   `.dream-loop/captures/latest.png` in the project.
3. For image-to-3D assets, follow `references/fal.md` and drive
   `scripts/fal-batch.mjs` from `terminal`.

`SKILL_DIR` is this skill's installed directory (the directory holding this
SKILL.md).

## Quick Reference

| Thing | Where |
|---|---|
| Working folder (gitignored) | `<project>/.dream-loop/` |
| Target image | `.dream-loop/target.png` |
| Latest capture | `.dream-loop/captures/latest.png` |
| Fal job file | `.dream-loop/fal-jobs.json` |
| Pro loop + judge rubric + exit criteria | `references/pro-mode/workflow.md` |
| Plus loop (orchestrate worker subagents) | `references/plus-mode/workflow.md` |
| Asset sourcing ladder | `references/<mode>/assets-3d.md` |
| Fal recipes + recovery rules | `references/fal.md` |

Hermes tool mapping for the upstream instructions:

| Upstream wording | Hermes tool |
|---|---|
| "image generation tool" | `image_generate` (`image_url` = baseline to edit) |
| "subagent with a fresh context" | `delegate_task` (children always start fresh) |
| "look at / compare screenshots" | `vision_analyze` on each image path |
| "capture a screenshot" | preview server capture, or `browser_navigate` + `browser_vision` |
| "use the shell" | `terminal` |

## Procedure

1. **Choose the workflow.** If the user named Plus or Pro, use it. Otherwise
   default to **Pro** (you build, a fresh judge subagent scores). Use **Plus**
   (you orchestrate, worker subagents build) when the user asks for it or when
   `delegation.model` in `config.yaml` is pinned to a stronger model than the
   one you are running on. Never read both workflow files — they are not
   inter-compatible.
2. **Set up the workspace.** Create `.dream-loop/` in the project and add it
   to `.gitignore`.
3. **Lock the target image.** If the user supplied one, copy it to
   `.dream-loop/target.png`. Otherwise:
   - Fresh project → `image_generate` a new image.
   - Existing product → capture its current screenshot first, then call
     `image_generate` with that screenshot as `image_url` and the user's
     direction as the prompt, so the target refines rather than diverges.
   - Prompt for a *real in-engine / in-app screenshot* at the product's
     camera. Never say "concept art", "cinematic", "painting", or "photo" —
     the target is matched down to the pixel.
   - Save the result to `.dream-loop/target.png` (copy from the path the tool
     returns).
4. **Start the clock** if the user gave a time budget; check it between
   rounds. Never trade visual fidelity for the deadline — beautiful partial
   progress beats ugly completeness. With no budget, warn the user that the
   loop can consume a lot of tokens, then run to an exit criterion.
5. **Run the loop** exactly as the chosen workflow file describes. For every
   judge or worker `delegate_task`, pass the absolute paths of
   `.dream-loop/target.png` and the latest capture in `context`, plus the
   workflow's verbatim prompt/rubric — the child has no other context.
6. **Source 3D assets** by walking the chosen mode's `assets-3d.md` ladder top
   to bottom. Do not jump to procedural geometry to save time.
7. **Exit** per the workflow's criteria and show the user the final capture
   next to the target.

## Pitfalls

- **Reading both workflow files.** They conflict; pick one.
- **"Concept art" prompts.** Produce an unmatchable, painterly target.
- **Target drift on existing products.** Always edit from a baseline
  screenshot; text-only generation invents a different product.
- **Blank WebGL captures.** Without `preserveDrawingBuffer: true` (or capturing
  right after a render call), `toBlob` returns an empty frame.
- **Rotated or mis-scaled GLBs.** Image-to-3D output often lands in the wrong
  orientation or scale — fix it when integrating, and check the capture.
- **Duplicate paid Fal jobs.** Never clear `request_id` / queue URLs to
  "retry"; follow the recovery table in `references/fal.md`.
- **Procedural fallback out of convenience.** Only when the asset ladder
  genuinely leaves no better option.
- **Judge context leakage.** Give each judge a fresh `delegate_task` call with
  only the images, the previous verdict, and the rubric — never your own
  opinions of the scene.

## Verification

- `.dream-loop/target.png` exists and was locked before the loop started.
- The final `.dream-loop/captures/latest.png` came from the running product
  (not a composited or generated image).
- The last judge verdict meets the workflow's exit criterion (Pro: score ≥ 8
  with acceptable FPS), or the Plus loop completed its round count.
- `node SKILL_DIR/scripts/fal-batch.mjs check .dream-loop/fal-jobs.json`
  reports no `invalid-image` or `missing-request-id` rows, and every model the
  scene loads is `downloaded`.
- `.dream-loop/` is listed in the project's `.gitignore`.
