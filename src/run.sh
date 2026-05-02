#!/usr/bin/env bash
source "$HOME/submagic_env/bin/activate"
cd "$(dirname "${BASH_SOURCE[0]}")/src"
python3 app.py "$@"
