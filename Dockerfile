#
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=UTC


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


RUN pip3 install aqtinstall

RUN mkdir -p /root/.config/aqt && cat > /root/.config/aqt/settings.ini << 'EOF'
[requests]
max_retries_to_retrieve_hash = 0
connection_timeout = 300
response_timeout = 300

[mirrors]
trusted_mirrors = https://download.qt.io
EOF

ENV XDG_CONFIG_HOME=/root/.config

#RUN aqt install-qt linux desktop 6.5.0 gcc_64 \
 #   --outputdir /opt/Qt \
  #  --modules qtmultimedia qtshadertools
ENV Qt6_DIR=/opt/Qt/6.5.0/gcc_64
ENV PATH=/opt/Qt/6.5.0/gcc_64/bin:$PATH
ENV LD_LIBRARY_PATH=/opt/Qt/6.5.0/gcc_64/lib:$LD_LIBRARY_PATH
ENV QML_IMPORT_PATH=/opt/Qt/6.5.0/gcc_64/qml
ENV QT_PLUGIN_PATH=/opt/Qt/6.5.0/gcc_64/plugins

   
ENV Qt6_DIR=/opt/Qt/6.5.0/gcc_64
ENV PATH=/opt/Qt/6.5.0/gcc_64/bin:$PATH
ENV LD_LIBRARY_PATH=/opt/Qt/6.5.0/gcc_64/lib:$LD_LIBRARY_PATH
ENV QML_IMPORT_PATH=/opt/Qt/6.5.0/gcc_64/qml
ENV QT_PLUGIN_PATH=/opt/Qt/6.5.0/gcc_64/plugins


RUN python3.10 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
ENV VIRTUAL_ENV=/opt/venv

COPY python_renderer/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt


WORKDIR /workspace


# Local dev usage:
#   docker run -it \
#     -e DISPLAY=$DISPLAY \
#     -v /tmp/.X11-unix:/tmp/.X11-unix \
#     -v ~/repo/eye_gymnastics:/workspace \
#     eye-gymnastics
#

CMD ["/bin/bash"]
