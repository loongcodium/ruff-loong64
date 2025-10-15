# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "ruamel-yaml",
# ]
# ///
from urllib.request import urlopen
from sys import argv
from textwrap import dedent
from ruamel.yaml import YAML, comments
from get_versions import get_ruff_versions

yaml = YAML()
yaml.width = 160
yaml.indent(mapping=2, sequence=4, offset=2)


def get_step(steps, field="uses", starts="actions/checkout"):
    return next(s for s in steps if s.get(field) and s.get(field).startswith(starts))


def remove_comments(y):
    delattr(y, comments.Comment.attrib)


def gen_ruff_binaries_job(original_workflow, patch_path="patches/ruff.patch"):
    job = original_workflow["jobs"]["linux-cross"]

    # Remove running condition
    job.pop("if")

    # Update repo and ref of the checkout step
    checkout_step = get_step(job["steps"])
    checkout_step["with"]["repository"] = "astral-sh/ruff"
    checkout_step["with"]["ref"] = "${{ env.RUFF_VERSION }}"

    # Add patch steps
    patch_steps_path = "loongcodium-ruff"
    patch_steps = yaml.load(f"""\
        - uses: actions/checkout@v5
          with:
            path: {patch_steps_path}
            sparse-checkout: |
              {patch_path}
            sparse-checkout-cone-mode: false
        - name: Apply patch
          run : |
            git apply {patch_steps_path}/{patch_path}
            rm -rf {patch_steps_path}
    """)
    index = job["steps"].index(checkout_step)
    for i, step in enumerate(patch_steps):
        job["steps"].insert(index + 1 + i, step)

    # Only build for loongarch64 platform
    platform_loongarch64 = yaml.load("""\
        # There's currently no loong64 support for Ubuntu so we are using Debian
        - target: loongarch64-unknown-linux-gnu
          arch: loong64
          base_image: --platform=linux/loong64 ghcr.io/loong64/debian:trixie
          maturin_docker_options: -e JEMALLOC_SYS_WITH_LG_PAGE=16
    """)
    job["strategy"]["matrix"]["platform"] = platform_loongarch64

    # Patch check step
    test_wheel_step = list(
        filter(lambda step: step.get("name") == "Test wheel", job["steps"])
    )[0]
    test_wheel_step["with"]["base_image"] = "${{ matrix.platform.base_image }}"
    test_wheel_step["with"]["install"] = dedent("""\
        apt-get update
        apt-get install -y --no-install-recommends python3 python3-pip python3-venv libatomic1
    """)
    test_wheel_step["with"]["run"] = dedent("""\
        python3 -m venv .venv
        source .venv/bin/activate
        pip3 install -U pip
        pip3 install ${{ env.PACKAGE_NAME }} --no-index --find-links dist/ --force-reinstall
        ruff --help
    """)

    job["env"] = original_workflow["env"]

    return job


def gen_ruff_vscode_build_id_job(original_workflow):
    job = original_workflow["jobs"]["build-id"]
    steps = original_workflow["jobs"]["build-id"]["steps"]

    job["env"] = original_workflow["env"]

    get_step(steps)["with"]["repository"] = "astral-sh/ruff-vscode"
    get_step(steps)["with"]["ref"] = "${{ env.RUFF_VSCODE_VERSION }}"
    remove_comments(steps[-1])

    return job


def gen_ruff_vscode_job(original_workflow):
    job = original_workflow["jobs"]["build"]
    steps = job["steps"]

    # Remove unused steps
    steps.remove(get_step(steps, "run", "arch -arm64"))
    steps.remove(get_step(steps, "run", "arch -x86_64"))
    steps.remove(get_step(steps, "uses", "uraimo/run-on-arch-action"))
    steps.remove(get_step(steps, "uses", "jirutka/setup-alpine"))
    steps.remove(get_step(steps, "shell", "alpine.sh"))
    steps.remove(get_step(steps, "run", "python -m pip install -t ./bundled/libs"))

    # Update target list
    job["strategy"] = yaml.load("""\
      matrix:
        include:
          - os: ubuntu-22.04
            target: loongarch64-unknown-linux-gnu
            code-target: linux-loong64
            python-platform: manylinux_2_36_loongarch64

    """)
    job["needs"] = yaml.load('["build-id", "build-ruff"]')

    # Update checkout step
    remove_comments(get_step(steps)["with"])
    get_step(steps)["with"]["repository"] = "astral-sh/ruff-vscode"
    get_step(steps)["with"]["ref"] = "${{ env.RUFF_VSCODE_VERSION }}"

    # Install bundled wheels
    install_wheels_steps = yaml.load("""\
        - name: Install the latest version of uv
          uses: astral-sh/setup-uv@v6

        - name: Download wheels from previous step
          uses: actions/download-artifact@v5
          with:
            name: wheels-${{ matrix.target }}

        - name: Install libraries
          run: |
            uv pip compile --python-version 3.7.9 --generate-hashes -o ./requirements.txt ./pyproject.toml --no-emit-package ruff
            git diff -- requirements.txt
            python3 -m pip install -t ./bundled/libs --implementation py --no-deps --upgrade -r ./requirements.txt --platform=${{ matrix.python-platform }}
            python3 -m pip install -t ./bundled/libs --implementation py --no-deps --upgrade ruff --no-index --find-links . --platform=${{ matrix.python-platform }}

    """)
    setup_python_step = get_step(steps, "uses", "actions/setup-python")
    remove_comments(setup_python_step["with"])
    install_wheels_index = steps.index(setup_python_step)
    for i, step in enumerate(install_wheels_steps):
        job["steps"].insert(install_wheels_index + 1 + i, step)

    # Build step
    build_cmd = 'npx vsce package -o "./dist/ruff-${{ matrix.code-target }}.vsix"'
    get_step(steps, "name", "Package Extension (release)")["run"] = build_cmd
    get_step(steps, "name", "Package Extension (nightly)")["run"] = (
        build_cmd + " --pre-release"
    )

    # Patch vsix
    patch_vsix_steps = yaml.load("""\
        - name: Checkout repository
          uses: actions/checkout@v5
          with:
            path: loongcodium-ruff

        - name: Patch vsix
          run: uv run --no-project loongcodium-ruff/scripts/patch-vsix.py "./dist/ruff-${{ matrix.code-target }}.vsix"

    """)
    patch_vsix_index = steps.index(get_step(steps, "name", "Upload artifacts"))
    for i, step in enumerate(patch_vsix_steps):
        job["steps"].insert(patch_vsix_index + i, step)

    remove_comments(steps[-1]["with"])

    return job


def gen_workflow(ruff_version, ruff_vscode_version):
    template = yaml.load(dedent("""\
        # This file is generated by scripts/update_workflow.py
                         
        name: Release
        on:
          push:
            tags:
              - "*.*.*"
          workflow_dispatch:
        
        env:

        jobs:
          build-ruff:
          build-id:
          build:

          release:
            runs-on: ubuntu-latest
            if: startsWith(github.ref, 'refs/tags/')
            needs: ["build"]
            permissions:
              contents: write
            steps:
              - name: Download artifacts
                uses: actions/download-artifact@v5
              - uses: softprops/action-gh-release@v2
                with:
                  files: |
                    ./**/*.vsix
                    ./**/*.whl
                    ./**/*.tar.gz
                    ./**/*.sha256
    """))

    template["env"] = {
        "RUFF_VERSION": ruff_version,
        "RUFF_VSCODE_VERSION": ruff_vscode_version,
    }

    with urlopen(
        f"https://raw.githubusercontent.com/astral-sh/ruff/refs/tags/{ruff_version}/.github/workflows/build-binaries.yml"
    ) as r:
        binaries_workflow = yaml.load(r)
        template["jobs"]["build-ruff"] = gen_ruff_binaries_job(binaries_workflow)

    with urlopen(
        f"https://raw.githubusercontent.com/astral-sh/ruff-vscode/refs/tags/{ruff_vscode_version}/.github/workflows/release.yaml"
    ) as r:
        release_workflow = yaml.load(r)
        template["jobs"]["build-id"] = gen_ruff_vscode_build_id_job(release_workflow)
        template["jobs"]["build"] = gen_ruff_vscode_job(release_workflow)

    return template


if __name__ == "__main__":
    workflow = gen_workflow(*get_ruff_versions(argv[1] if len(argv) > 1 else None))
    with open(".github/workflows/release.yml", "w") as f:
        yaml.dump(workflow, f)
