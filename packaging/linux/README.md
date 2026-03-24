# Linux Packaging

## .deb Package (Debian/Ubuntu)

### Prerequisites
```bash
sudo apt install ruby ruby-dev
sudo gem install fpm
```

### Build
```bash
bash packaging/linux/build-deb.sh 2.3.0
```

### Install
```bash
sudo dpkg -i dist/fss-mini-rag_2.3.0_amd64.deb
sudo apt-get install -f  # Fix any missing dependencies
```

### What it installs
- Python venv at `/opt/fss-mini-rag/venv/`
- CLI command: `/usr/local/bin/rag-mini`
- GUI command: `/usr/local/bin/rag-mini-gui`
- Desktop entry in application menu
- Depends on: `python3`, `python3-tk`, `python3-venv`

### Uninstall
```bash
sudo dpkg -r fss-mini-rag
```

## AppImage (Portable)

### Build
```bash
bash packaging/linux/build-appimage.sh 2.3.0
```

### Use
```bash
chmod +x FSS-Mini-RAG-2.3.0-x86_64.AppImage
./FSS-Mini-RAG-2.3.0-x86_64.AppImage              # Launch GUI
./FSS-Mini-RAG-2.3.0-x86_64.AppImage search "query" # CLI mode
```

### What it bundles
- Python 3.11 runtime
- All dependencies (lancedb, numpy, pyarrow, etc.)
- Tkinter + sv-ttk theme
- Works on any Linux with glibc 2.28+ (Ubuntu 18.04+, Debian 10+, Fedora 29+)

No installation needed. Single file, runs anywhere.

## Files

| File | Purpose |
|------|---------|
| `build-deb.sh` | fpm wrapper for building .deb |
| `build-appimage.sh` | AppImage builder |
| `fss-mini-rag.desktop` | Desktop entry (used by both .deb and AppImage) |
| `postinstall.sh` | Post-install script for .deb (creates venv, symlinks) |
