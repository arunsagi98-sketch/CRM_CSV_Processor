#!/usr/bin/env bash
set -o errexit

# Install dependencies with pre-built wheels
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

echo "Dependencies installed successfully"
