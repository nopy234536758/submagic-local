# 📦 Packaging Submagic Local — Guide complet

## Prérequis communs
```bash
pip install pyinstaller
# ou pour une meilleure compatibilité :
pip install nuitka
```

---

## 🪟 Windows → `.exe`

### Avec PyInstaller (recommandé)
```bash
# Depuis le dossier src/ sous Windows
pip install pyinstaller pygame customtkinter

pyinstaller --onefile --windowed \
  --name "SubmagicLocal" \
  --icon assets/icon.ico \
  --add-data "assets;assets" \
  app.py
```
Le `.exe` sera dans `dist/SubmagicLocal.exe`.

### One-liner sans console
```bash
pyinstaller --onefile --noconsole --name SubmagicLocal app.py
```

### Note FFmpeg sous Windows
FFmpeg doit être dans le PATH ou bundlé :
```python
# Dans video_composer.py, ajouter en haut :
import sys, os
if getattr(sys, 'frozen', False):
    os.environ["PATH"] += os.pathsep + sys._MEIPASS
```
Puis dans le spec PyInstaller :
```python
binaries=[('C:/ffmpeg/bin/ffmpeg.exe', '.')]
```

---

## 🍎 macOS → `.app` + `.dmg`

### Avec PyInstaller
```bash
pip install pyinstaller py2app

pyinstaller --onefile --windowed \
  --name "SubmagicLocal" \
  --icon assets/icon.icns \
  app.py
```
→ `dist/SubmagicLocal.app`

### Créer un DMG (optionnel)
```bash
pip install create-dmg
create-dmg \
  --volname "Submagic Local" \
  --window-size 600 400 \
  --icon SubmagicLocal.app 150 150 \
  --app-drop-link 450 150 \
  SubmagicLocal.dmg dist/SubmagicLocal.app
```

### Signature (pour distribution)
```bash
codesign --deep --force --sign "Developer ID Application: ..." dist/SubmagicLocal.app
```

---

## 🐧 Linux → `.deb` et `.AppImage`

### `.AppImage` (universel, recommandé)

1. Installer `appimagetool` :
```bash
wget https://github.com/AppImage/AppImageKit/releases/latest/download/appimagetool-x86_64.AppImage
chmod +x appimagetool-x86_64.AppImage
```

2. Builder avec PyInstaller :
```bash
pyinstaller --onedir --name SubmagicLocal app.py
```

3. Créer la structure AppDir :
```bash
mkdir -p SubmagicLocal.AppDir/usr/bin
cp -r dist/SubmagicLocal/* SubmagicLocal.AppDir/usr/bin/

cat > SubmagicLocal.AppDir/SubmagicLocal.desktop << 'EOF'
[Desktop Entry]
Name=Submagic Local
Exec=SubmagicLocal
Icon=submagic
Type=Application
Categories=Video;
EOF

cp assets/icon.png SubmagicLocal.AppDir/submagic.png
cp assets/icon.png SubmagicLocal.AppDir/.DirIcon

cat > SubmagicLocal.AppDir/AppRun << 'APPRUN'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
exec "$HERE/usr/bin/SubmagicLocal" "$@"
APPRUN
chmod +x SubmagicLocal.AppDir/AppRun
```

4. Générer l'AppImage :
```bash
./appimagetool-x86_64.AppImage SubmagicLocal.AppDir SubmagicLocal.AppImage
```

---

### `.deb` (Debian / Ubuntu)

```bash
# Installer fpm (outil de packaging)
gem install fpm

# Builder d'abord avec PyInstaller
pyinstaller --onedir --name SubmagicLocal app.py

# Créer le .deb
fpm -s dir -t deb \
  --name submagic-local \
  --version 1.0.0 \
  --architecture amd64 \
  --description "Submagic Local — sous-titres animés" \
  --depends ffmpeg \
  dist/SubmagicLocal/=/opt/SubmagicLocal \
  assets/submagic.desktop=/usr/share/applications/submagic.desktop
```

Résultat : `submagic-local_1.0.0_amd64.deb`

Installation :
```bash
sudo dpkg -i submagic-local_1.0.0_amd64.deb
```

---

## ☕ JAR Java ? → Non applicable

L'app est en Python/Tkinter, pas en Java. Un JAR n'est pas le bon format.
**Alternative cross-platform propre :**
- Utilise **AppImage** sous Linux (fonctionne partout sans installation)
- Ou **Briefcase** (Python natif) :

```bash
pip install briefcase
briefcase new   # configure le projet
briefcase build
briefcase package
```

Briefcase génère automatiquement `.msi` (Windows), `.dmg` (macOS), `.AppImage` (Linux).

---

## 🚀 Solution tout-en-un : Briefcase (recommandé)

```bash
pip install briefcase

# Initialiser (une seule fois)
briefcase new

# Construire pour la plateforme courante
briefcase build

# Packager
briefcase package

# Lancer pour tester
briefcase run
```

Briefcase gère automatiquement le bundling de Python, des dépendances, et
produit le format natif de chaque OS.
