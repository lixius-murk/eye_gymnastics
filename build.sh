#!/bin/bash
# run this inside the container
set -e

cd /workspace
cmake -B build \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_PREFIX_PATH=/opt/Qt/6.5.0/gcc_64 \
    -DBUILD_QDS_COMPONENTS=OFF \
    -DLINK_INSIGHT=OFF
cmake --build build --parallel
./build/eye_gymnasticsApp
