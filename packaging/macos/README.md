# macOS Packaging (Deferred)

macOS native packaging is planned but deferred until an Apple Developer account is set up.

## What's Needed

### Apple Developer Account
- **Cost**: $99/year (USD)
- **URL**: https://developer.apple.com/programs/
- **What it provides**: Code signing certificate + notarization capability
- **Why it's required**: macOS Gatekeeper blocks unsigned apps since Catalina (10.15+). Without code signing, users get "app is damaged and can't be opened" errors.

The $99/year also allows publishing other apps to the Mac App Store and distributing any macOS software without Gatekeeper warnings.

### Build Approach: py2app

py2app creates standard macOS `.app` bundles from Python applications.

```bash
pip install py2app

# Build
python setup.py py2app --includes=sv_ttk,tkinter
```

This produces `dist/FSS-Mini-RAG.app/` which can be wrapped in a `.dmg` disk image.

### Code Signing

```bash
# Sign the app bundle
codesign --deep --force --options runtime \
  --sign "Developer ID Application: Your Name (TEAMID)" \
  dist/FSS-Mini-RAG.app
```

### Notarization (Required for Distribution)

```bash
# Create a zip for notarization
ditto -c -k --keepParent dist/FSS-Mini-RAG.app dist/FSS-Mini-RAG.zip

# Submit for notarization
xcrun notarytool submit dist/FSS-Mini-RAG.zip \
  --apple-id "your@email.com" \
  --team-id "TEAMID" \
  --password "app-specific-password" \
  --wait

# Staple the notarization ticket
xcrun stapler staple dist/FSS-Mini-RAG.app
```

### DMG Creation

```bash
brew install create-dmg

create-dmg \
  --volname "FSS-Mini-RAG" \
  --volicon "assets/fss-mini-rag.icns" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "FSS-Mini-RAG.app" 175 190 \
  --app-drop-link 425 190 \
  dist/FSS-Mini-RAG-2.3.0.dmg \
  dist/FSS-Mini-RAG.app
```

### GitHub Actions (Future)

```yaml
build-macos:
  runs-on: macos-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    - name: Build .app
      run: |
        pip install py2app
        pip install -r requirements.txt
        python setup_macos.py py2app
    - name: Sign and notarize
      env:
        MACOS_CERTIFICATE: ${{ secrets.MACOS_CERTIFICATE }}
        MACOS_CERTIFICATE_PASSWORD: ${{ secrets.MACOS_CERTIFICATE_PASSWORD }}
      run: |
        # Import certificate, sign, notarize
        ...
    - name: Create DMG
      run: |
        brew install create-dmg
        create-dmg ...
```

### Icon File

Need to create `assets/fss-mini-rag.icns` from the existing PNG:

```bash
# On macOS
mkdir icon.iconset
sips -z 16 16 assets/Fss_Mini_Rag.png --out icon.iconset/icon_16x16.png
sips -z 32 32 assets/Fss_Mini_Rag.png --out icon.iconset/icon_16x16@2x.png
sips -z 32 32 assets/Fss_Mini_Rag.png --out icon.iconset/icon_32x32.png
sips -z 64 64 assets/Fss_Mini_Rag.png --out icon.iconset/icon_32x32@2x.png
sips -z 128 128 assets/Fss_Mini_Rag.png --out icon.iconset/icon_128x128.png
sips -z 256 256 assets/Fss_Mini_Rag.png --out icon.iconset/icon_128x128@2x.png
sips -z 256 256 assets/Fss_Mini_Rag.png --out icon.iconset/icon_256x256.png
sips -z 512 512 assets/Fss_Mini_Rag.png --out icon.iconset/icon_256x256@2x.png
sips -z 512 512 assets/Fss_Mini_Rag.png --out icon.iconset/icon_512x512.png
sips -z 1024 1024 assets/Fss_Mini_Rag.png --out icon.iconset/icon_512x512@2x.png
iconutil -c icns icon.iconset -o assets/fss-mini-rag.icns
rm -rf icon.iconset
```

## Timeline

When the Apple Developer account is set up:
1. Create `packaging/macos/setup_macos.py` (py2app config)
2. Generate `.icns` icon file
3. Add `build-macos` job to GitHub Actions workflow
4. Set up signing secrets in GitHub
5. Test on macOS VM
