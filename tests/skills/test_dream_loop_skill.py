"""Tests for the dream-loop optional skill.

Exercises the two bundled helpers for real (stdlib + pytest, no network):

- ``scripts/preview-server.py`` is imported and served on an ephemeral port.
- ``scripts/fal-batch.mjs`` is driven through Node with an injected ``fetch``
  mock, porting the upstream ``fal-batch.test.mjs`` contracts: no duplicate
  paid submissions, uncertain submissions never auto-retried, credentials never
  forwarded to the download host, offline ``check`` catches bad plans.
"""

import base64
import importlib.util
import json
import os
import re
import shutil
import subprocess
import threading
import urllib.error
import urllib.request
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

SKILL_DIR = (
    Path(__file__).resolve().parents[2] / "optional-skills" / "creative" / "dream-loop"
)
FAL_BATCH = SKILL_DIR / "scripts" / "fal-batch.mjs"
PREVIEW_SERVER = SKILL_DIR / "scripts" / "preview-server.py"

TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a5XcAAAAASUVORK5CYII="
)

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


# ---------------------------------------------------------------------------
# Skill layout
# ---------------------------------------------------------------------------


def _markdown_files():
    return [SKILL_DIR / "SKILL.md", *sorted((SKILL_DIR / "references").rglob("*.md"))]


@pytest.mark.parametrize("md", _markdown_files(), ids=lambda p: str(p.relative_to(SKILL_DIR)))
def test_relative_links_resolve(md):
    text = md.read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)#\s]+)\)", text):
        if re.match(r"[a-z]+://", target):
            continue
        assert (md.parent / target).exists(), f"{md.name}: broken link {target}"


def test_skill_md_paths_exist():
    """Every skill-relative path the SKILL.md tells the agent to open exists."""
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    paths = set(re.findall(r"`((?:references|scripts)/[\w./-]+\.(?:md|mjs|py))`", text))
    assert paths, "SKILL.md should reference its bundled files"
    for rel in paths:
        if "<mode>" in rel:
            continue
        assert (SKILL_DIR / rel).is_file(), f"SKILL.md references missing {rel}"


# ---------------------------------------------------------------------------
# preview-server.py
# ---------------------------------------------------------------------------


@pytest.fixture
def preview_server(tmp_path):
    spec = importlib.util.spec_from_file_location("dream_loop_preview_server", PREVIEW_SERVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(module.Handler, directory=str(tmp_path))
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", tmp_path
    finally:
        server.shutdown()
        server.server_close()


def _post(url, body):
    req = urllib.request.Request(url, data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as err:
        return err.code, b""


def test_preview_server_saves_png_capture(preview_server):
    base, root = preview_server
    status, body = _post(base + "/__capture", TINY_PNG)
    assert status == 200
    payload = json.loads(body)
    latest = root / ".dream-loop" / "captures" / "latest.png"
    assert Path(payload["latest"]) == latest
    assert latest.read_bytes() == TINY_PNG
    assert Path(payload["path"]).read_bytes() == TINY_PNG


def test_preview_server_rejects_non_png_and_other_paths(preview_server):
    base, root = preview_server
    assert _post(base + "/__capture", b"not a png at all")[0] == 400
    assert _post(base + "/elsewhere", TINY_PNG)[0] == 404
    assert not (root / ".dream-loop" / "captures" / "latest.png").exists()


def test_preview_server_serves_project_files(preview_server):
    base, root = preview_server
    (root / "index.html").write_text("<canvas></canvas>", encoding="utf-8")
    with urllib.request.urlopen(base + "/index.html", timeout=10) as resp:
        assert resp.read() == b"<canvas></canvas>"


# ---------------------------------------------------------------------------
# fal-batch.mjs
# ---------------------------------------------------------------------------


def _fixture(tmp_path, count=1, endpoint="test/model/variant", **job_extra):
    (tmp_path / "input.png").write_bytes(TINY_PNG)
    jobs = tmp_path / "jobs.json"
    jobs.write_text(
        json.dumps(
            {
                "jobs": [
                    {
                        "id": f"asset-{i}",
                        "endpoint": endpoint,
                        "image": "input.png",
                        "output": f"models/{i}.glb",
                        **job_extra,
                    }
                    for i in range(count)
                ]
            }
        ),
        encoding="utf-8",
    )
    return jobs


def _node_env():
    env = {k: v for k, v in os.environ.items() if k not in ("FAL_KEY", "FAL_API_KEY")}
    return env


# Shared prelude: imports runBatch and provides JSON/GLB response helpers.
_HARNESS = """
import {{ runBatch }} from {module};
const jobs = {jobs};
const json = data => new Response(JSON.stringify(data), {{ headers: {{ 'Content-Type': 'application/json' }} }});
function glb() {{
  const raw = JSON.stringify({{ asset: {{ version: '2.0' }} }});
  const body = Buffer.from(raw.padEnd(Math.ceil(raw.length / 4) * 4, ' '));
  const b = Buffer.alloc(20 + body.length);
  b.write('glTF'); b.writeUInt32LE(2, 4); b.writeUInt32LE(b.length, 8);
  b.writeUInt32LE(body.length, 12); b.write('JSON', 16); body.copy(b, 20);
  return b;
}}
const out = {{}};
{body}
console.log(JSON.stringify(out));
"""


def _run_node(tmp_path, jobs, body):
    script = _HARNESS.format(
        module=json.dumps(FAL_BATCH.as_uri()), jobs=json.dumps(str(jobs)), body=body
    )
    driver = tmp_path / "driver.mjs"
    driver.write_text(script, encoding="utf-8")
    proc = subprocess.run(
        ["node", str(driver)], capture_output=True, text=True, timeout=60, env=_node_env()
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout.strip().splitlines()[-1])


@needs_node
def test_fal_batch_submits_once_and_collects_without_leaking_credentials(tmp_path):
    jobs = _fixture(tmp_path, count=2)
    out = _run_node(
        tmp_path,
        jobs,
        """
let posts = 0, downloadHeaders = [];
const fetchFn = async (url, options) => {
  if (options.method === 'POST') {
    const i = posts++;
    if (!/^data:image\\/png;base64,.+/.test(JSON.parse(options.body).image_url)) throw new Error('bad image_url');
    return json({ request_id: `r${i}`, status: 'IN_QUEUE',
      status_url: `https://queue.fal.run/returned/r${i}/status`,
      response_url: `https://queue.fal.run/returned/r${i}/result` });
  }
  if (url.endsWith('/status')) return json({ status: 'COMPLETED' });
  if (url.endsWith('/result')) return json({ model_mesh: { url: 'https://files.example/model.glb' } });
  downloadHeaders.push(options.headers ?? null);
  return new Response(glb());
};
const config = { key: 'test-only-key', fetchFn };
await runBatch('submit', jobs, config);
await runBatch('submit', jobs, config);
out.posts = posts;
out.rows = await runBatch('collect', jobs, config);
out.downloadHeaders = downloadHeaders;
out.glbMatches = (await import('node:fs')).readFileSync(jobs.replace(/jobs\\.json$/, 'models/0.glb')).equals(glb());
""",
    )
    assert out["posts"] == 2, "resubmitting must not create duplicate paid jobs"
    assert all(row["state"] == "downloaded" for row in out["rows"])
    assert out["downloadHeaders"] == [None, None], "download host must not get the Fal key"
    assert out["glbMatches"]
    saved = json.loads(jobs.read_text(encoding="utf-8"))
    assert all("/returned/" in job["status_url"] for job in saved["jobs"])


@needs_node
def test_fal_batch_never_retries_uncertain_submission(tmp_path):
    jobs = _fixture(tmp_path)
    out = _run_node(
        tmp_path,
        jobs,
        """
let calls = 0;
const config = { key: 'test-only-key', fetchFn: async () => { calls++; throw new Error('network timeout'); } };
out.first = (await runBatch('submit', jobs, config))[0].state;
await runBatch('submit', jobs, config);
out.calls = calls;
""",
    )
    assert out["first"] == "submission-uncertain"
    assert out["calls"] == 1


@needs_node
def test_fal_batch_redacts_rejected_submission_details(tmp_path):
    jobs = _fixture(tmp_path)
    key = "test-only-secret-key"
    out = _run_node(
        tmp_path,
        jobs,
        f"""
const key = {json.dumps(key)};
out.row = (await runBatch('submit', jobs, {{ key, fetchFn: async () => new Response(JSON.stringify({{
  detail: [{{ loc: ['body', 'texture_size'], msg: `Invalid size ${{key}} data:image/png;base64,AAAA`, input: 'DO NOT SAVE THIS IMAGE' }}],
}}), {{ status: 422 }}) }}))[0];
""",
    )
    assert out["row"]["state"] == "rejected"
    assert "body.texture_size: Invalid size" in out["row"]["error_detail"]
    saved = jobs.read_text(encoding="utf-8")
    for secret in (key, "DO NOT SAVE THIS IMAGE", "base64,AAAA"):
        assert secret not in saved


def _cli(jobs, command="check"):
    return subprocess.run(
        ["node", str(FAL_BATCH), command, str(jobs)],
        capture_output=True,
        text=True,
        timeout=60,
        env=_node_env(),
    )


@needs_node
def test_fal_batch_check_is_offline_and_leaves_plan_untouched(tmp_path):
    jobs = _fixture(
        tmp_path, endpoint="fal-ai/trellis", input={"mesh_simplify": 0.95, "texture_size": 1024}
    )
    before = jobs.read_text(encoding="utf-8")
    proc = _cli(jobs)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)[0]["state"] == "ready"
    assert jobs.read_text(encoding="utf-8") == before


@needs_node
@pytest.mark.parametrize(
    ("endpoint", "job_input", "message"),
    [
        ("fal-ai/trellis/image-to-3d", {}, "no /image-to-3d suffix"),
        ("fal-ai/trellis", {"face_limit": 200000}, "H3.1 option"),
        ("tripo3d/h3.1/image-to-3d", {"texture_size": 1024}, "Trellis option"),
    ],
)
def test_fal_batch_check_rejects_bad_plans(tmp_path, endpoint, job_input, message):
    proc = _cli(_fixture(tmp_path, endpoint=endpoint, input=job_input))
    assert proc.returncode == 1
    assert message in proc.stderr


@needs_node
def test_fal_batch_submit_requires_a_key(tmp_path):
    proc = _cli(_fixture(tmp_path), command="submit")
    assert proc.returncode == 1
    assert "FAL_KEY" in proc.stderr
