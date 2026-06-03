#!/usr/bin/env bash
set -o errexit

# Upgrade pip, setuptools, and wheel first
pip install --upgrade pip setuptools wheel

# Install packages with explicit binary-only preference
pip install --only-binary :all: -r requirements.txt

echo "Dependencies installed successfully"
