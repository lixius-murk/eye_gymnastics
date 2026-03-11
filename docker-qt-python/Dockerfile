FROM ubuntu:latest AS builder
 

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Base build tools
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    ninja-build \
    git \
    wget \
    curl \
    pkg-config \
    # OpenGL / Mesa
    libgl1-mesa-dev \
    libglu1-mesa-dev \
    mesa-utils \
    libegl1-mesa-dev \
    # GStreamer for Qt Multimedia
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libgstreamer-plugins-good1.0-dev \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-libav \
    # Audio
    libpulse-dev \
    libasound2-dev \
    # X11 / display
    libx11-dev \
    libxcb1-dev \
    libxcb-xinerama0 \
    libxcb-cursor0 \
    libxkbcommon-x11-0 \
    libxkbcommon-dev \
    # Python
    python3.10 \
    python3.10-venv \
    python3.10-dev \
    python3-pip \
    # OpenCV system deps
    libopencv-dev \
    # Misc
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Qt 6.5.0 via aqtinstall
RUN pip3 install aqtinstall && \
    aqt install-qt linux desktop 6.4.2 gcc_64 \
        --modules qtmultimedia \
        --outputdir /opt/Qt

ENV Qt6_DIR=/opt/Qt/6.4.2/gcc_64
ENV PATH=$Qt6_DIR/bin:$PATH
ENV LD_LIBRARY_PATH=$Qt6_DIR/lib:$LD_LIBRARY_PATH
ENV QML_IMPORT_PATH=$Qt6_DIR/qml
ENV QT_PLUGIN_PATH=$Qt6_DIR/plugins


COPY ../src /app/src
COPY ../CMakeFIles.txt /app/
COPY ../python_renderer /app/python_renderer


WORKDIR /app/build

RUN cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=$Qt6_DIR && \
    cmake --build . --config Release --parallel 4



# Python venv with project dependencies
RUN python3.10 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt



FROM ubuntu:latest

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
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
    libopencv-core4.5d \
    libopencv-imgproc4.5d \
    libopencv-highgui4.5d \
    libopencv-videoio4.5d \
    python3.10 \
    python3.10-venv \
    && rm -rf /var/lib/apt/lists/*

# Copy Qt libraries from builder
COPY --from=builder /opt/Qt /opt/Qt

# Copy Python venv from builder
COPY --from=builder /opt/venv /opt/venv

# Copy built application
COPY --from=builder /app/build/eye_gymnasticsApp /app/eye_gymnasticsApp

# Set environment variables
ENV Qt6_DIR=/opt/Qt/6.4.2/gcc_64
ENV PATH=/opt/venv/bin:$Qt6_DIR/bin:$PATH
ENV LD_LIBRARY_PATH=$Qt6_DIR/lib:$LD_LIBRARY_PATH
ENV QML_IMPORT_PATH=$Qt6_DIR/qml
ENV QT_PLUGIN_PATH=$Qt6_DIR/plugins
ENV QT_QPA_PLATFORM=offscreen
ENV DISPLAY=:0

WORKDIR /app

# Create a non-root user to run the app
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app /opt/venv
USER appuser

# Command to run the application
ENTRYPOINT ["./eye_gymnasticsApp"]
