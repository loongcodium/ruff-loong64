# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "ruamel-yaml",
# ]
# ///
from urllib.request import urlopen
from ruamel.yaml import YAML

yaml = YAML()
yaml.width = 160

ruff_version = "0.13.0"
ruff_vscode_version = "2025.26.0"


def get_ruff_binaries_job(
    original_workflow, ruff_version, patch_path="patches/ruff.patch"
):
    cross_job = original_workflow["jobs"]["linux-cross"]

    # Remove running condition
    cross_job.pop("if")

    # Update repo and ref of the checkout step
    checkout_step = list(
        filter(
            lambda step: step.get("uses")
            and step.get("uses").startswith("actions/checkout"),
            cross_job["steps"],
        )
    )[0]
    checkout_step["with"]["repository"] = "astral-sh/ruff"
    checkout_step["with"]["ref"] = ruff_version

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
    index = cross_job["steps"].index(checkout_step)
    for i, step in enumerate(patch_steps):
        cross_job["steps"].insert(index + 1 + i, step)

    # Only build for loongarch64 platform
    platform_loongarch64 = yaml.load("""\
# There's currently no loong64 support for Ubuntu so we are using Debian
- target: loongarch64-unknown-linux-gnu
  arch: loong64
  base_image: --platform=linux/loong64 ghcr.io/loong64/debian:trixie
  maturin_docker_options: -e JEMALLOC_SYS_WITH_LG_PAGE=16
""")
    cross_job["strategy"]["matrix"]["platform"] = platform_loongarch64

    # Patch check step
    test_wheel_step = list(
        filter(lambda step: step.get("name") == "Test wheel", cross_job["steps"])
    )[0]
    test_wheel_step["with"]["base_image"] = "${{ matrix.platform.base_image }}"
    test_wheel_step["with"]["install"] = """\
apt-get update
apt-get install -y --no-install-recommends python3 python3-pip python3-venv libatomic1
"""
    test_wheel_step["with"]["run"] = """\
python3 -m venv .venv
source .venv/bin/activate
pip3 install -U pip
pip3 install ${{ env.PACKAGE_NAME }} --no-index --find-links dist/ --force-reinstall
ruff --help
"""

    return cross_job


def gen_workflow():
    template_file = "./workflow-template.yml"
    with open(template_file) as f:
        template = yaml.load(f)

    with urlopen(
        f"https://raw.githubusercontent.com/astral-sh/ruff/refs/tags/{ruff_version}/.github/workflows/build-binaries.yml"
    ) as r:
        binaries_workflow = yaml.load(r)
        template["jobs"]["build-ruff"] = get_ruff_binaries_job(
            binaries_workflow, ruff_version
        )
        template["jobs"]["build-ruff"]["env"] = binaries_workflow["env"]

    with urlopen(
        f"https://raw.githubusercontent.com/astral-sh/ruff-vscode/refs/tags/{ruff_vscode_version}/.github/workflows/release.yaml"
    ) as r:
        release_workflow = yaml.load(r)
        template["jobs"]["build-id"] = release_workflow["jobs"]["build-id"]
        template["jobs"]["build-id"]["steps"][0]["with"]["repository"] = (
            "astral-sh/ruff-vscode"
        )
        try:
            template["jobs"]["build-id"]["steps"][-1].ca.items["run"][2] = None
        except Exception as e:
            print(f"Failed to remove comment in build-id\n{e}")

    return template


with open(".github/workflows/release.yml", "w") as f:
    yaml.dump(gen_workflow(), f)
