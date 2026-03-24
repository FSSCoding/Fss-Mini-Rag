# Windows Packaging

## Standalone Installer (.exe)

The Windows installer bundles Python + all dependencies. Users don't need Python installed.

### How It Works

1. **Embedded Python**: Downloads the official Python embeddable distribution (~25MB)
2. **Dependencies**: Installs all requirements into the embedded Python
3. **Inno Setup**: Wraps everything in a professional installer with:
   - Install wizard with license agreement
   - Start Menu shortcuts (GUI + CLI)
   - Optional desktop shortcut
   - Optional PATH integration
   - Clean uninstaller

### Building Locally

Prerequisites:
- Python 3.10+ (for building the wheel)
- [Inno Setup 6+](https://jrsoftware.org/isinfo.php)

```powershell
powershell -ExecutionPolicy Bypass -File packaging\windows\build-installer.ps1
```

Output: `dist/fss-mini-rag-2.3.0-setup.exe`

### Building in CI

The GitHub Actions workflow handles this automatically on `windows-latest`.

### What Gets Installed

```
C:\Program Files\FSS-Mini-RAG\
  python\              Embedded Python 3.11 + all packages
  rag-mini.bat         CLI launcher
  rag-mini-gui.bat     GUI launcher
  icon.ico             Application icon
  README.md            Documentation
```

Start Menu:
- FSS-Mini-RAG (GUI)
- FSS-Mini-RAG CLI
- Uninstall FSS-Mini-RAG

### Icon

The installer needs `assets/fss-mini-rag.ico`. Convert from the existing PNG:
```bash
# Linux (imagemagick)
convert assets/Fss_Mini_Rag.png -resize 256x256 assets/fss-mini-rag.ico

# Or use an online converter
```

## Files

| File | Purpose |
|------|---------|
| `installer.iss` | Inno Setup script |
| `build-installer.ps1` | Build automation (downloads Python, installs deps, runs iscc) |
