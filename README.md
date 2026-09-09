# FFBeastier

A fork of the [FFBeast documentation site](https://github.com/ffbeast/ffbeast.github.io) that tracks upstream
and adds one concrete DIY direct-drive wheel build on top of it:

- **ODESC V4.2 (56V)** single-axis controller
- **38 mm, 6 mm shaft, 2500 PPR push-pull** optical encoder (10000 CPR)
- 6.5 inch hoverboard motor

Everything upstream is kept intact, including the firmware downloads. The additions live in one place:

| What                                         | Where                                                                                    |
|----------------------------------------------|------------------------------------------------------------------------------------------|
| Build guide: wiring, encoders, setup, tuning | `docs/en/wheel_beastier*.md`, shown as **FFBeast Wheel > Beastier build** on the site    |
| Wiring diagram                               | `assets/images/beastier/wiring_odesc42_pushpull.svg`                                     |
| Telemetry effects tool (Python)              | `tools/beastier-effects/`                                                                |

## Site

Built with Jekyll and the Just the Docs theme through the GitHub Pages workflow in `.github/workflows/pages.yml`.
The workflow passes the Pages base path automatically, so the site works at
`https://thepicklebaron.github.io/ffbeastier.github.io/` without further configuration.

To publish, enable Pages once on the repository with source **GitHub Actions**:

```bash
gh api -X POST repos/ThePickleBaron/ffbeastier.github.io/pages -f build_type=workflow
```

Local preview needs Ruby and Bundler:

```bash
bundle install
bundle exec jekyll serve
```

## Keeping up with upstream

The fork carries a handful of added files and three edited ones (`_config.yml`, `index.md`, `README.md`), so
upstream merges are normally clean:

```bash
git remote add upstream https://github.com/ffbeast/ffbeast.github.io.git
git fetch upstream
git merge upstream/main
git push origin main
```

## Telemetry effects tool

`tools/beastier-effects` is a small Python program that adds road texture, kerbs, ABS, lock-up and understeer
cues from Forza or Assetto Corsa telemetry using the wheel's documented USB API. See its
[README](tools/beastier-effects/README.md) and the site page **Beastier build > Telemetry effects**.

```bash
cd tools/beastier-effects
python -m pip install -e ".[hid,dev]"
python -m pytest
python -m beastier_effects --source demo --dry-run
```

## License

The site template is MIT licensed (see `LICENSE`). Upstream FFBeast content and firmware remain the property of
their author under the terms on the site's **Terms of use** page. The telemetry tool in `tools/` is MIT.
