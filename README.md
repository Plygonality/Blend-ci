# Blend-ci

Headless Blender cook. Git is the source of truth. The `.blend` is a cache.

gn-as-code, Master-Node, Habitat-kit, and Unit-canon all say that. Nothing in those
repos proves a dump still cooks in Blender 4.2+ / 5.x. This repo does.

Apply an existing graph JSON or apply script plus a scene fixture. Run
`blender --background --python`. Write a structural dump (object names, dimensions,
unit_canon roles) and one workbench PNG. Fail CI if the dump drifts. The PNG hash
is advisory unless `UPDATE_GOLDENS=1`.

No DCC GUI. No MCP. No new graph format.

## Install

```bash
pip install -e ".[dev]"
blend-ci versions
blend-ci ensure-blender   # exit 2 if blender is missing — fail closed
```

Python 3.11+. Blender is not required to lint dumps, compare goldens, or emit
apply scripts. A cook without Blender is a hard failure, not a skip.

## Cook

```bash
blend-ci cook \
  --graph fixtures/column.json \
  --scene fixtures/canon_scene.py \
  --object Column \
  --out-dir artifacts \
  --golden tests/goldens/column.dump.json \
  --png-golden tests/goldens/column.png.sha256 \
  --gpu-backend opengl
```

| Input | What it is |
|---|---|
| `--graph` | Existing **gn-as-code** dump. Apply script is generated with `gn_as_code.apply.to_apply_script`. |
| `--apply` | Existing bpy script (gn-as-code `apply-script`, probe-kit `apply-script`, Master-Node `scripts/smoke_blender.py`). |
| `--scene` | Fixture: `.py` setup script or `.blend`. Shipped fixture is `fixtures/canon_scene.py`. |

Do not pass a novel JSON schema. Habitat-kit graphs are gn-as-code dumps when they land.

| Output | Gate |
|---|---|
| `artifacts/dump.json` | Compared to golden JSON. Names, roles, collections must match. Lengths use the Unit-canon 1 cm tolerance. |
| `artifacts/workbench.png` | SHA-256 is **advisory**. Workbench pixels move across 4.5 / 5.x and Vulkan / OpenGL. |

```bash
UPDATE_GOLDENS=1 blend-ci cook …   # rewrite dump + PNG hash goldens
```

The dump is a Collection-linter scene (`unit_canon.collection_linter.Scene`). After
the cook, Blend-ci runs `unit_canon.lint` so a role that no longer matches the
canon file fails closed.

## Matrix

LTS is the maintained 4.x line (covers the 4.2+ contract). Current is 5.x.

| Channel | Pin | Backend |
|---|---|---|
| LTS | 4.5.13 | `vulkan` and `opengl` |
| Current | 5.2.1 | `vulkan` and `opengl` |

Blender 5.x defaults to Vulkan and SIGSEGV / abort on GitHub-hosted runners
(no real GPU). Blend-ci already retries that crash with `--gpu-backend opengl`.
The OpenGL cell is the closed gate; the Vulkan cell starts on Vulkan and falls
back only on a crash exit.

```bash
blend-ci cook --gpu-backend vulkan                 # retry opengl on crash
blend-ci cook --gpu-backend vulkan --no-fallback-opengl
```

## Install Blender (exact cache step)

There is no official headless Blender container that this repo uses. Do **not**
use `lscr.io/linuxserver/blender` — that image is a KasmVNC desktop.

CI downloads the official linux-x64 tarball and caches the extract:

```
https://download.blender.org/release/Blender4.5/blender-4.5.13-linux-x64.tar.xz
https://download.blender.org/release/Blender5.2/blender-5.2.1-linux-x64.tar.xz
```

```bash
# cache key: blender-<version>-linux-x64
# cache path: $BLEND_CI_CACHE/blender-<version>/
# binary:     $BLEND_CI_CACHE/blender-<version>/blender
scripts/install_blender.sh 4.5.13
# or: lts | current
```

GitHub Actions (this is what `.github/actions/setup-blender` runs):

```yaml
- name: System GL / Vulkan / xvfb
  run: |
    sudo apt-get update
    sudo apt-get install -y --no-install-recommends \
      libegl1 libgl1 libgomp1 libsm6 libxfixes3 libxi6 \
      libxkbcommon0 libxrender1 libxxf86vm1 \
      mesa-utils mesa-vulkan-drivers xvfb
- uses: actions/cache@v4
  with:
    path: ${{ runner.tool_cache }}/blend-ci
    key: blender-4.5.13-linux-x64
- run: bash scripts/install_blender.sh 4.5.13
  env:
    BLEND_CI_CACHE: ${{ runner.tool_cache }}/blend-ci
- run: blend-ci ensure-blender   # exit 2 if the binary is missing
```

`xvfb-run` is used when `DISPLAY` is unset. Software GL is
`LIBGL_ALWAYS_SOFTWARE=1` + `GALLIUM_DRIVER=llvmpipe`.

## GitHub Action

From a sibling repo (graph JSON stays in that repo):

```yaml
jobs:
  cook:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        blender: ["4.5.13", "5.2.1"]
        gpu_backend: [opengl, vulkan]
    steps:
      - uses: actions/checkout@v4
      - uses: Plygonality/Blend-ci@main
        with:
          blender-version: ${{ matrix.blender }}
          gpu-backend: ${{ matrix.gpu_backend }}
          graph: graphs/column.json
          object: Column
          golden: tests/goldens/column.dump.json
```

Or the local composite in this repo: `.github/actions/setup-blender`.

## Tests

```bash
pip install -e ".[dev]"
pytest -q
ruff check src tests fixtures
```

Host pytest does not start Blender. The `blend-ci` workflow does.

## Why this repo exists

| Role | Job |
|---|---|
| **gn-as-code / Probe-kit / Habitat-kit** | Author the graph. JSON is the artifact. |
| **Master-Node** | Bind a category master. Pass `scripts/smoke_blender.py` as `--apply`. |
| **Unit-canon / Collection-linter** | Roles and lengths. This cook dumps them and lints them. |
| **This repo** | Prove the artifact still cooks in Blender 4.2+ / 5.x. |
| **Plygon-mcp** | Live GUI loop on localhost. Not used here. |
