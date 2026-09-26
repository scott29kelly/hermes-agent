# Attribution

This skill is ported from a third-party MIT-licensed project.

## dream-loop (Anshu Chimala)

- Source: https://github.com/achimala/dream-loop
- Upstream commit: `9bddb901f7d071cfefdd21e264267c757177a9df`
- License: MIT
- Copyright: © 2026 Anshu Chimala

### What was ported

- `references/pro-mode/workflow.md`, `references/plus-mode/workflow.md`,
  `references/pro-mode/assets-3d.md`, `references/plus-mode/assets-3d.md`,
  `references/fal.md` — verbatim, except the two `assets-3d.md` files now link
  to `../fal.md` (upstream linked `fal.md`, which does not resolve from the
  mode subdirectories).
- `scripts/fal-batch.mjs`, `scripts/preview-server.py` — verbatim.

### What changed

- `SKILL.md` was rewritten to the Hermes skill authoring standards
  (frontmatter, section order, ≤60-char description) and maps the upstream
  generic wording onto Hermes tools (`image_generate`, `vision_analyze`,
  `delegate_task`, `terminal`).
- Workflow selection: upstream chooses Plus vs. Pro from the user's ChatGPT
  subscription tier, which does not apply to Hermes. The port defaults to Pro
  and uses Plus when asked or when `delegation.model` is stronger than the
  orchestrating model.

### What was NOT ported

- `README.md` and `assets/vesper-preview.gif` (7 MB demo animation).
- `scripts/fal-batch.test.mjs` — its contracts are exercised from
  `tests/skills/test_dream_loop_skill.py` in the Hermes repo instead, so no
  test file ships inside the installed skill.

### License

```
MIT License

Copyright (c) 2026 Anshu Chimala

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
