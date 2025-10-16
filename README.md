# loongcodium-ruff

This project builds [ruff-vscode](https://github.com/astral-sh/ruff-vscode) for LoongArch with a bundled Ruff binary.

To get the extension, please navigate to [releases](https://github.com/SkyBird233/loongcodium-ruff/releases) and download the `.vsix` file, and then install it with `codium --install-extension ruff-linux-loong64.vsix`. Ruff binary and wheel files are also provided.

If you are not sure which version to download, just grab [the latest version](https://github.com/SkyBird233/loongcodium-ruff/releases/latest/download/ruff-linux-loong64.vsix). If you need a specific version, please download the version with the largest `-x`.

## Q & A

### I don't want to use this. Can I use something from the upstream directly?
Yes, you can. Simply download the official release for your architecture and install it using `codium --install-extension`. Then, configure the installed extension to use your Ruff binary. This project is more about the bundled binary.
If you have Ruff installed in a configured virtual environment, the extension will use that binary automatically, and you don't even need to configure anything further.

### Why not just wait for upstreams
It won't be done in the near future. For Astral / Ruff, support may be added after Debian adds LoongArch support and corresponding images are published officially.
For Open VSX, a [related issue](https://github.com/eclipse/openvsx/issues/1350) has got 0 replies when I'm writing this.

#### Why are you building Ruff here?
Ruff has [reverted](https://github.com/astral-sh/ruff/pull/20372) the [PR adding support for LoongArch](https://github.com/astral-sh/ruff/pull/20361) because the Astral team decided that it's necessary to wait for an official image for testing in CI, so we have to build Ruff manually.
It would be better to maintain a Ruff fork with LoongArch binary releases, but the [patch](patches/ruff.patch) needed is relatively simple, so I think the current approach would be enough for now.

#### Why don't you publish the extension to Open VSX?
It is not possible to publish this extension to Open VSX because Open VSX doesn't support LoongArch-specific extensions.
Although it's possible to pretend that it's a universal extension and nothing wrong would happen as long as people don't install it on architectures other than LoongArch, 
[trying to add such support to upstream](https://github.com/eclipse/openvsx/issues/1350) first may be better.

Maybe building a universal extension that asks users to provide their binary would be better, as only this part is actually platform-specific.

## Development

Use `uv run scripts/update_workflow.py` to update `.github/workflows/release.yml`.
