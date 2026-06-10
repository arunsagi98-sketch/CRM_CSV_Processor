#!/usr/bin/env bash
set -euo pipefail

# Upgrade pip, setuptools, and wheel first
python -m pip install --upgrade pip setuptools wheel

# Install packages preferring binary wheels to avoid source builds on Render
pip install --prefer-binary --no-cache-dir -r requirements.txt

echo "Dependencies installed successfully"
