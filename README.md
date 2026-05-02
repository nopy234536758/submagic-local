# ✦ Submagic Local 

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Linux](https://img.shields.io/badge/platform-Linux-blue?logo=linux)](https://github.com/Nopy234536758/submagic-local)
[![Windows](https://img.shields.io/badge/platform-Windows-blue?logo=windows)](https://github.com/Nopy234536758/submagic-local)
[![macOS](https://img.shields.io/badge/platform-macOS-blue?logo=apple)](https://github.com/Nopy234536758/submagic-local)

**English** | **Français**

> 💬 *This project was entirely **vibe‑coded** by [Claude](https://claude.ai) and [DeepSeek](https://deepseek.com) – because even AIs need to have fun making cool stuff.*  
> *Projet entièrement **vibé‑codé** par Claude et DeepSeek – parce que même les IA aiment s’amuser à faire des trucs cool.*

---

## ✨ English

**Submagic Local** is an open‑source, fully local subtitle tool that generates **word‑by‑word animated captions** for videos.  
Inspired by Submagic, powered by [WhisperX](https://github.com/m-bain/whisperX) (forced alignment) and [MoviePy](https://github.com/Zulko/moviepy) / PIL.

> No paywall, no cloud, no upload – your video never leaves your computer.

### Features

| Feature | Description |
|---------|-------------|
| 🎙 **Word‑level transcription** | Uses WhisperX to get exact timestamps for every single word |
| 🎨 **Dynamic negative colour** | Text colour automatically adapts to the video background (complementary colour) |
| 🔤 **Custom fonts** | Import any `.ttf` / `.otf` font |
| 🎛 **Ultra‑customisable style** | Font size, outline, shadow, word background, karaoke highlight, alignment, animation‑in (pop, fade, slide, bounce) |
| 🎬 **Real‑time preview** | Built‑in video player with audio sync (requires `pygame`) |
| 📝 **Subtitle editor** | Modify timestamps and text directly in the UI |
| 💾 **Export MP4** | Burn subtitles into video, keep original audio |
| 📄 **Export SRT** | Generate standard subtitle files (word‑by‑word or grouped) |
| ⚡ **Threaded background tasks** | UI never freezes during transcription or export |
| 📦 **Standalone executables** | AppImage (Linux), `.exe` (Windows), and `.app` (macOS) via GitHub Actions |

### Installation

#### Linux
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv ffmpeg
# Optional for better font rendering
sudo apt install imagemagick
```

#### From source (all platforms)
```bash
git clone https://github.com/Nopy234536758/submagic-local.git
cd submagic-local
python3 -m venv submagic_env
source submagic_env/bin/activate   # Windows: submagic_env\Scripts\activate
pip install -r src/requirements.txt
python3 src/app.py
```

#### Pre‑built binaries
Download from [Releases](https://github.com/Nopy234536758/submagic-local/releases):
- **Linux** : `SubmagicLocal.AppImage` (make executable with `chmod +x`)
- **Windows** : `SubmagicLocal.exe`
- **macOS** : `SubmagicLocal-macos.zip` (unzip and drag to Applications)

### Usage
1. Load a video (MP4, AVI, MOV, MKV, WebM).
2. Choose Whisper model (`tiny` to `large`). `small` is a good CPU compromise.
3. Click **Transcribe** – wait for word‑level timestamps.
4. Customise style in the right panel (size, colour, outline, shadow, negative dynamic effect, karaoke, etc.).
5. Preview with the built‑in player (audio requires `pygame`).
6. Export as MP4 (subtitles burned in) or SRT.

### Development & Build
```bash
# Activate environment
source submagic_env/bin/activate
# Run the app
python src/app.py

# Build with PyInstaller
pip install pyinstaller
pyinstaller --onefile --windowed --name SubmagicLocal --add-data "src:src" src/app.py
```

### Project structure
```
.
├── .github/workflows/       # CI build scripts
├── src/
│   ├── app.py               # Main GUI (CustomTkinter)
│   ├── transcriber.py       # WhisperX pipeline
│   ├── video_composer.py    # PIL + FFmpeg subtitle rendering
│   ├── style_config.py      # Dataclass for style
│   └── srt_exporter.py      # SRT generation
├── assets/                  # Icons, images
├── fonts/                   # Default fonts
├── requirements.txt
├── README.md
└── LICENSE
```

### License
MIT – free for personal and commercial use.

---

## ✨ Français

**Submagic Local** est un outil de sous‑titrage open‑source, 100 % local, qui génère des **sous‑titres animés mot‑par‑mot** pour vos vidéos.  
Inspiré de Submagic, propulsé par [WhisperX](https://github.com/m-bain/whisperX) (alignement forcé) et [MoviePy](https://github.com/Zulko/moviepy) / PIL.

> Pas de paywall, pas de cloud, pas d’upload – votre vidéo ne quitte jamais votre ordinateur.

### Fonctionnalités

| Fonctionnalité | Description |
|----------------|-------------|
| 🎙 **Transcription mot‑à‑mot** | WhisperX avec timestamps précis pour chaque mot |
| 🎨 **Couleur négative dynamique** | La couleur du texte s’adapte automatiquement au fond de la vidéo (complémentaire) |
| 🔤 **Polices personnalisées** | Importez vos fichiers `.ttf` / `.otf` |
| 🎛 **Style ultra‑personnalisable** | Taille, contour, ombre, fond du mot, surlignage karaoké, alignement, animation d’entrée (pop, fondu, glissement, rebond) |
| 🎬 **Prévisualisation en temps réel** | Lecteur vidéo intégré avec synchronisation audio (nécessite `pygame`) |
| 📝 **Éditeur de sous‑titres** | Modifiez directement les timestamps et le texte dans l’interface |
| 💾 **Export MP4** | Sous‑titres incrustés, audio conservé |
| 📄 **Export SRT** | Génère des fichiers SRT standards (mot‑à‑mot ou regroupés) |
| ⚡ **Tâches en arrière‑plan** | L’interface ne se bloque jamais pendant la transcription ou l’export |
| 📦 **Exécutables autonomes** | AppImage (Linux), `.exe` (Windows) et `.app` (macOS) via GitHub Actions |

### Installation

#### Linux
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv ffmpeg
# Optionnel pour un meilleur rendu des polices
sudo apt install imagemagick
```

#### Depuis les sources (toutes plateformes)
```bash
git clone https://github.com/Nopy234536758/submagic-local.git
cd submagic-local
python3 -m venv submagic_env
source submagic_env/bin/activate   # Windows: submagic_env\Scripts\activate
pip install -r src/requirements.txt
python3 src/app.py
```

#### Binaires pré‑compilés
Téléchargez depuis les [Releases](https://github.com/Nopy234536758/submagic-local/releases) :
- **Linux** : `SubmagicLocal.AppImage` (rendez‑le exécutable avec `chmod +x`)
- **Windows** : `SubmagicLocal.exe`
- **macOS** : `SubmagicLocal-macos.zip` (décompressez et glissez dans Applications)

### Utilisation
1. Chargez une vidéo (MP4, AVI, MOV, MKV, WebM).
2. Choisissez le modèle Whisper (`tiny` à `large`). `small` est un bon compromis sur CPU.
3. Cliquez sur **Transcrire** – attendez l’obtention des timestamps mot‑par‑mot.
4. Personnalisez le style dans le panneau de droite (taille, couleur, contour, ombre, effet négatif dynamique, karaoké, etc.).
5. Prévisualisez avec le lecteur intégré (l’audio nécessite `pygame`).
6. Exportez en MP4 (sous‑titres incrustés) ou SRT.

### Développement & compilation
```bash
# Activez l’environnement
source submagic_env/bin/activate
# Lancez l’application
python src/app.py

# Compilation avec PyInstaller
pip install pyinstaller
pyinstaller --onefile --windowed --name SubmagicLocal --add-data "src:src" src/app.py
```

### Structure du projet
```
.
├── .github/workflows/       # Scripts CI
├── src/
│   ├── app.py               # Interface principale (CustomTkinter)
│   ├── transcriber.py       # Pipeline WhisperX
│   ├── video_composer.py    # Rendu des sous‑titres (PIL + FFmpeg)
│   ├── style_config.py      # Dataclass de style
│   └── srt_exporter.py      # Génération SRT
├── assets/                  # Icônes, images
├── fonts/                   # Polices par défaut
├── requirements.txt
├── README.md
└── LICENSE
```

### Licence
MIT – libre pour usage personnel et commercial.

---

**Enjoy / Amusez‑vous bien !** 🎬
```
