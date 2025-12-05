# ruff-loong64

This project builds [ruff-vscode](https://github.com/astral-sh/ruff-vscode) for LoongArch with a bundled Ruff binary.

To get the extension, search for it in the extensions tab of VSCodium and install it directly.

To install the `.vsix` file offline, please get it from [releases](https://github.com/loongcodium/ruff-loong64/releases), and then install it with `codium --install-extension ruff-linux-loong64.vsix`. Ruff binary and wheel files are also provided.

## Q & A

### I don't want to use this. Can I use something from the upstream directly?
Yes, you can. Simply download the official release for your architecture and install it using `codium --install-extension`. Then, configure the installed extension to use your Ruff binary. This project is more about the bundled binary.
If you have Ruff installed in a configured virtual environment, the extension will use that binary automatically, and you don't even need to configure anything further.

### Why not just wait for upstreams?
It won't be done in the near future. For Astral / Ruff, support may be added after Debian adds LoongArch support and corresponding images are published officially.
For Open VSX, a [related issue](https://github.com/eclipse/openvsx/issues/1350) has received 0 replies when I'm writing this.

#### Why are you building Ruff here?
Ruff has [reverted](https://github.com/astral-sh/ruff/pull/20372) the [PR adding support for LoongArch](https://github.com/astral-sh/ruff/pull/20361) because the Astral team decided that it's necessary to wait for an official image for testing in CI, so we have to build Ruff manually.
It would be better to maintain a Ruff fork with LoongArch binary releases, but the [patch](patches/ruff.patch) needed is relatively simple, so I think the current approach would be enough for now.

#### Why are you publishing a universal version?
It is not possible to publish a LoongArch-specific extension to Open VSX because Open VSX doesn't support it yet, see the issue mentioned above.

## Development

Use `uv run scripts/update_workflow.py` to update `.github/workflows/release.yml`.
