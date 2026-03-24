# FSS-Mini-RAG Packaging

Build scripts and configs for creating native installers on each platform.

## Release Pipeline

When a version tag (`v*`) is pushed to GitHub, the CI pipeline builds:

| Artifact | Platform | Built By |
|----------|----------|----------|
| `fss_mini_rag-*.whl` | All (universal) | `python -m build` |
| `fss-mini-rag-*.tar.gz` | All (source) | `python -m build` |
| `rag-mini.pyz` | All (needs Python) | `scripts/build_pyz.py` |
| `fss-mini-rag_*_amd64.deb` | Debian/Ubuntu | `packaging/linux/build-deb.sh` |
| `FSS-Mini-RAG-x86_64.AppImage` | Linux (portable) | `packaging/linux/build-appimage.sh` |
| `fss-mini-rag-*-setup.exe` | Windows (standalone) | `packaging/windows/installer.iss` |

## Directory Layout

```
packaging/
  windows/
    installer.iss          Inno Setup script (standalone .exe with embedded Python)
    build-installer.ps1    CI build script
    README.md              Windows packaging notes
  linux/
    build-deb.sh           fpm wrapper for .deb
    build-appimage.sh      AppImage build script
    fss-mini-rag.desktop   Desktop entry for Linux app menus
    postinstall.sh         Post-install script for .deb (creates venv, symlinks)
    README.md              Linux packaging notes
  macos/
    README.md              Deferred: Apple Developer account needed ($99/yr)
```

## Local Builds

```bash
# Universal wheel
make build

# Linux .deb (needs fpm: gem install fpm)
make build-deb

# Linux AppImage
make build-appimage

# Zipapp
make build-pyz
```

The Windows installer must be built on Windows (or via GitHub Actions on `windows-latest`).

## Adding a New Platform

1. Create `packaging/<platform>/` with build script and config
2. Add a job to `.github/workflows/build-and-release.yml`
3. Add artifact upload + download in the `create-release` job
4. Update this README
