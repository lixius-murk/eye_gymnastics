#!/bin/bash

set -e

xhost + local:docker


# Add user to docker group (requires logout/login to take effect)
sudo usermod -aG docker $USER

# Build and enter container
docker compose up --build
