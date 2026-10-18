#!/usr/bin/env bash
set -euo pipefail
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.11
uv python list
python311="$(uv python find 3.11)"
echo "PYTHON311=$python311"
"$python311" --version
# Recreate venv with 3.11
rm -rf "$HOME/.venvs/buildozer"
"$python311" -m venv "$HOME/.venvs/buildozer"
source "$HOME/.venvs/buildozer/bin/activate"
python -m pip install --upgrade pip setuptools wheel
python -m pip install "cython==0.29.36" "buildozer==1.5.0"
python -c "import buildozer, Cython, sys; print(sys.version); print('buildozer', buildozer.__version__, 'cython', Cython.__version__)"
echo "PY311_OK"
