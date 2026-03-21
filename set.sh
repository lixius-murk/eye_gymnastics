#!/bin/bash
set -e

xhost +local:docker
sudo usermod -aG docker $USER


docker compose build

echo "Starting interactive shell in container..."
docker compose run --rm eye_gymnastics
