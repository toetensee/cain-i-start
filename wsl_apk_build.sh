#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
export ANDROIDAPI=35
export ANDROIDMINAPI=28
SRC="/mnt/c/xampp/htdocs/php/cain-i-start"
WORK="$HOME/cain-i-start"

echo "=== Copy project to Linux filesystem ==="
mkdir -p "$WORK"
rsync -a --delete \
  --exclude '.git/' \
  --exclude '__pycache__/' \
  --exclude '.buildozer/' \
  --exclude 'bin/' \
  --exclude 'wsl_apk_build.sh' \
  "$SRC/" "$WORK/"
cd "$WORK"
ls -la

echo "=== Create venv and install Buildozer ==="
if [ ! -d "$HOME/.venvs/buildozer" ]; then
  python3 -m venv "$HOME/.venvs/buildozer"
fi
# shellcheck disable=SC1091
source "$HOME/.venvs/buildozer/bin/activate"
python -m pip install --upgrade pip setuptools wheel
python -m pip install "cython>=3.0,<3.2" buildozer
python -c "import buildozer, Cython; print('buildozer', buildozer.__version__, 'cython', Cython.__version__)"

JAVA_CANDIDATE="$(dirname "$(dirname "$(readlink -f "$(command -v javac)")")")"
export JAVA_HOME="${JAVA_HOME:-$JAVA_CANDIDATE}"
echo "JAVA_HOME=$JAVA_HOME"
java -version

echo "=== Start Android debug build ==="
buildozer -v android debug
echo "=== Copy APK back to Windows project bin/ ==="
mkdir -p "$SRC/bin"
cp -v "$WORK"/bin/*.apk "$SRC/bin/"
ls -la "$SRC/bin" "$WORK/bin"
echo "BUILD SUCCESS"
