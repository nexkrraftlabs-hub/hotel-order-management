#!/usr/bin/env bash
# Render build script for The Royal Feast
set -o errexit

echo "===> Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "===> Running database setup & seeding..."
python seed.py

echo "===> Build completed successfully!"
