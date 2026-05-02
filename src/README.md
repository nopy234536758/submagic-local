# Submagic Local ✦ Turfu Edition

Application open-source de sous-titres animés mot-à-mot, 100 % locale, sans paywall.
Inspirée de Submagic, propulsée par WhisperX et MoviePy.

---

## ✨ Fonctionnalités

| Fonctionnalité | Détail |
|---|---|
| 🎙 Transcription mot-à-mot | WhisperX avec alignement forcé (timestamps précis) |
| 🎨 Effet "négatif dynamique" | Couleur complémentaire du fond sous chaque mot |
| 🔤 Import de polices | `.ttf` / `.otf` personnalisées |
| 🎛 Style complet | Taille, contour, épaisseur, position Y |
| 👁 Prévisualisation rapide | Export temporaire pour vérifier avant l'export final |
| 💾 Export MP4 | Sous-titres incrustés, audio conservé |
| 📄 Export SRT | Génération de fichiers `.srt` (mot-à-mot ou par blocs) |
| ⚡ Threading | Interface non bloquante pendant les opérations longues |
| 📦 Packagable | PyInstaller → `.exe` (Windows) / `.app` (macOS) |

---

## 🚀 Installation (Linux)

### Prérequis système

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv ffmpeg git
# Optionnel (meilleur rendu de polices avec MoviePy) :
sudo apt install imagemagick
```

### Installation automatique

```bash
git clone https://github.com/vous/submagic-local.git
cd submagic-local
bash setup.sh
```

### Installation manuelle

```bash
python3 -m venv ~/submagic_env
source ~/submagic_env/bin/activate
pip install -r requirements.txt
```

---

## ▶️ Lancement

```bash
bash run.sh
# ou
source ~/submagic_env/bin/activate
cd src && python3 app.py
```

---

## 🗂 Structure du projet

```
submagic-local/
├── src/
│   ├── app.py              ← Point d'entrée, interface CustomTkinter
│   ├── transcriber.py      ← Pipeline WhisperX (extraction audio + alignement)
│   ├── video_composer.py   ← Génération des clips (PIL + MoviePy)
│   ├── style_config.py     ← Dataclass de configuration du style
│   └── srt_exporter.py     ← Export .srt (par mot ou par blocs)
├── assets/                 ← Icônes, images
├── fonts/                  ← Polices personnalisées par défaut
├── tests/                  ← Tests unitaires
├── requirements.txt
├── setup.sh                ← Script d'installation Linux
├── run.sh                  ← Script de lancement (généré par setup.sh)
├── submagic.spec           ← Config PyInstaller
└── README.md
```

---

## 🎨 Effet "Négatif Dynamique"

Pour chaque mot prononcé, l'application :
1. Capture la frame vidéo à l'instant `t`
2. Extrait la couleur moyenne de la zone rectangulaire sous le mot
3. Calcule la couleur complémentaire : `(255-R, 255-G, 255-B)`
4. Applique un seuil de luminosité minimal (lisibilité garantie)

Résultat : les sous-titres s'adaptent automatiquement au fond de la vidéo.

---

## 🔧 Modèles Whisper

| Modèle | VRAM | Vitesse | Qualité |
|--------|------|---------|---------|
| `tiny` | ~1 GB | ⚡⚡⚡⚡ | ⭐⭐ |
| `small` | ~2 GB | ⚡⚡⚡ | ⭐⭐⭐ |
| `medium` | ~5 GB | ⚡⚡ | ⭐⭐⭐⭐ |
| `large` | ~10 GB | ⚡ | ⭐⭐⭐⭐⭐ |

Sur CPU, `small` est recommandé (bon compromis vitesse/qualité).

---

## 📦 Packaging en exécutable

```bash
source ~/submagic_env/bin/activate
pip install pyinstaller
pyinstaller submagic.spec
# → dist/SubmagicLocal (Linux/macOS) ou dist/SubmagicLocal.exe (Windows)
```

---

## 🤝 Contribution

Les PR sont les bienvenues ! Idées pour la roadmap :
- [ ] Effet karaoké (surlignage mot courant)
- [ ] Templates de styles pré-définis
- [ ] Support multi-langues amélioré
- [ ] Export WebVTT
- [ ] Prévisualisation en temps réel dans l'UI

---

## 📄 Licence

MIT — libre pour usage personnel et commercial.
