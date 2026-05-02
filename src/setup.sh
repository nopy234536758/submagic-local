#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# setup.sh — Installation complète de Submagic Local sur Linux
# Usage : bash setup.sh
# ─────────────────────────────────────────────────────────────────
set -e

VENV_DIR="$HOME/submagic_env"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Submagic Local — Setup Linux"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. Vérifications système ──
echo "[1/6] Vérification des dépendances système…"
for cmd in python3 pip ffmpeg git; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "  ⚠  '$cmd' manquant. Installez-le avec :"
        echo "     sudo apt install $cmd"
    else
        echo "  ✓  $cmd"
    fi
done

# ImageMagick (optionnel, pour TextClip MoviePy)
if command -v convert &>/dev/null; then
    echo "  ✓  ImageMagick"
else
    echo "  ℹ  ImageMagick non trouvé (optionnel)."
    echo "     Pour l'installer : sudo apt install imagemagick"
fi

# ── 2. Environnement virtuel ──
echo ""
echo "[2/6] Création de l'environnement virtuel dans $VENV_DIR…"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "  ✓  Environnement créé."
else
    echo "  ℹ  Environnement existant, réutilisation."
fi

source "$VENV_DIR/bin/activate"

# ── 3. pip à jour ──
echo ""
echo "[3/6] Mise à jour de pip…"
pip install --upgrade pip --quiet

# ── 4. Dépendances Python ──
echo ""
echo "[4/6] Installation des dépendances Python…"
pip install -r "$PROJECT_DIR/requirements.txt"

# ── 5. PyTorch (CUDA si disponible, sinon CPU) ──
echo ""
echo "[5/6] Vérification PyTorch + CUDA…"
python3 -c "
import torch
if torch.cuda.is_available():
    print(f'  ✓  CUDA disponible : {torch.cuda.get_device_name(0)}')
else:
    print('  ℹ  Pas de CUDA, mode CPU (plus lent mais fonctionnel).')
"

# ── 6. Lanceur ──
echo ""
echo "[6/6] Création du script de lancement…"

cat > "$PROJECT_DIR/run.sh" << 'EOF'
#!/usr/bin/env bash
source "$HOME/submagic_env/bin/activate"
cd "$(dirname "${BASH_SOURCE[0]}")/src"
python3 app.py "$@"
EOF
chmod +x "$PROJECT_DIR/run.sh"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅  Installation terminée !"
echo ""
echo "  Pour lancer l'application :"
echo "     bash $PROJECT_DIR/run.sh"
echo ""
echo "  Pour packager en exécutable :"
echo "     pip install pyinstaller"
echo "     pyinstaller --onefile --windowed src/app.py"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
