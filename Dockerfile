<<<<<<< HEAD
FROM ubuntu:22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Clean and update package lists, then install all dependencies
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get update --fix-missing && \
    apt-get install -y --fix-missing --no-install-recommends \
        build-essential \
        cmake \
        ninja-build \
        git \
        wget \
        curl \
        pkg-config \
        libgl1-mesa-dev \
        libglu1-mesa-dev \
        mesa-utils \
        libegl1-mesa-dev \
        libgstreamer1.0-dev \
        libgstreamer-plugins-base1.0-dev \
        libgstreamer-plugins-good1.0-dev \
        gstreamer1.0-plugins-base \
        gstreamer1.0-plugins-good \
        gstreamer1.0-libav \
        libpulse-dev \
        libasound2-dev \
        libx11-dev \
        libxcb1-dev \
        libxcb-xinerama0 \
        libxcb-cursor0 \
        libxkbcommon-x11-0 \
        libxkbcommon-dev \
        python3.10 \
        python3.10-venv \
        python3.10-dev \
        python3-pip \
        libopencv-dev \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Qt 6.4.2 via aqtinstall
RUN pip3 install aqtinstall && \
    aqt install-qt linux desktop 6.4.2 gcc_64 \
        --modules qtmultimedia \
        --outputdir /opt/Qt

ENV Qt6_DIR=/opt/Qt/6.4.2/gcc_64
ENV PATH=$Qt6_DIR/bin:$PATH
ENV LD_LIBRARY_PATH=$Qt6_DIR/lib:$LD_LIBRARY_PATH
ENV QML_IMPORT_PATH=$Qt6_DIR/qml
ENV QT_PLUGIN_PATH=$Qt6_DIR/plugins

# Python venv with project dependencies
RUN python3.10 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

COPY python_renderer/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# Copy source files
COPY ./src /app/src
COPY ./CMakeLists.txt /app/
COPY ./python_renderer /app/python_renderer

# Build C++ app
WORKDIR /app/build
RUN cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=$Qt6_DIR && \
    cmake --build . --config Release --parallel 4

# ---------- Runtime stage ----------
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1-mesa-glx \
        libglu1-mesa \
        libgstreamer1.0-0 \
        libgstreamer-plugins-base1.0-0 \
        gstreamer1.0-plugins-good \
        gstreamer1.0-plugins-bad \
        gstreamer1.0-libav \
        libxcb-xinerama0 \
        libxkbcommon-x11-0 \
        libxkbcommon0 \
        libxcb-cursor0 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-randr0 \
        libxcb-render-util0 \
        libxcb-shape0 \
        libxcb-sync1 \
        libxcb-util1 \
        libxcb-xfixes0 \
        libxcb-xkb1 \
        libxcb-xv0 \
        libx11-xcb1 \
        libopencv-core4.5 \
        libopencv-imgproc4.5 \
        libopencv-highgui4.5 \
        libopencv-videoio4.5 \
        python3.10 \
        python3.10-venv \
        python3-pip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy from builder
COPY --from=builder /opt/Qt /opt/Qt
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/build/eye_gymnasticsApp /app/eye_gymnasticsApp
COPY --from=builder /app/python_renderer /app/python_renderer

# Set environment variables
ENV Qt6_DIR=/opt/Qt/6.4.2/gcc_64
ENV PATH=/opt/venv/bin:$Qt6_DIR/bin:$PATH
ENV LD_LIBRARY_PATH=$Qt6_DIR/lib:$LD_LIBRARY_PATH
ENV QML_IMPORT_PATH=$Qt6_DIR/qml
ENV QT_PLUGIN_PATH=$Qt6_DIR/plugins
ENV QT_QPA_PLATFORM=offscreen
ENV DISPLAY=:0

WORKDIR /app

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app /opt/venv
USER appuser

ENTRYPOINT ["./eye_gymnasticsApp"]
=======
# syntax=docker/dockerfile:1
# Eye Gymnastics — Qt6 + Python OpenGL build & run environment
# Base: Ubuntu 22.04 (required for Qt 6.5 + GStreamer + OpenGL)

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=UTC

# ── System dependencies ────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build tools
    build-essential \
    cmake \
    ninja-build \
    git \
    pkg-config \
    # Qt runtime dependencies
    libgl1-mesa-dev \
    libgles2-mesa-dev \
    libxcb1-dev \
    libxcb-xinerama0-dev \
    libxcb-icccm4-dev \
    libxcb-image0-dev \
    libxcb-keysyms1-dev \
    libxcb-randr0-dev \
    libxcb-render-util0-dev \
    libxcb-shape0-dev \
    libxcb-xfixes0-dev \
    libxcb-xkb-dev \
    libxkbcommon-dev \
    libxkbcommon-x11-dev \
    libfontconfig1-dev \
    libfreetype6-dev \
    libdbus-1-dev \
    # GStreamer for Qt Multimedia / camera recording
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libgstreamer-plugins-good1.0-dev \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-libav \
    gstreamer1.0-x \
    # OpenGL for Python renderer
    libgl1-mesa-glx \
    libglu1-mesa-dev \
    mesa-utils \
    # Python
    python3.10 \
    python3.10-venv \
    python3.10-dev \
    python3-pip \
    # Qt installer tool deps
    wget \
    p7zip-full \
    && rm -rf /var/lib/apt/lists/*

# ── Install Qt 6.5.0 via aqtinstall ───────────────────────────────────────────
RUN pip3 install aqtinstall

RUN aqt install-qt linux desktop 6.5.0 gcc_64 \
    --outputdir /opt/Qt \
    --modules qtmultimedia qtshadertools

ENV Qt6_DIR=/opt/Qt/6.5.0/gcc_64
ENV PATH=/opt/Qt/6.5.0/gcc_64/bin:$PATH
ENV LD_LIBRARY_PATH=/opt/Qt/6.5.0/gcc_64/lib:$LD_LIBRARY_PATH
ENV QML_IMPORT_PATH=/opt/Qt/6.5.0/gcc_64/qml
ENV QT_PLUGIN_PATH=/opt/Qt/6.5.0/gcc_64/plugins

# ── Python venv with renderer dependencies ────────────────────────────────────
RUN python3.10 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
ENV VIRTUAL_ENV=/opt/venv

COPY python_renderer/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ── Workspace ─────────────────────────────────────────────────────────────────
WORKDIR /workspace

# ── Default: interactive shell for local dev ──────────────────────────────────
# Local dev usage:
#   docker run -it \
#     -e DISPLAY=$DISPLAY \
#     -v /tmp/.X11-unix:/tmp/.X11-unix \
#     -v ~/repo/eye_gymnastics:/workspace \
#     eye-gymnastics
#
# CI usage: override CMD with build commands
CMD ["/bin/bash"]
>>>>>>> docker-init
