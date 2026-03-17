@echo off
setlocal enabledelayedexpansion

py -3.10 -m pip install aqtinstall

py -3.10 -m aqt install-qt windows desktop 6.5.0 win64_msvc2019_64 ^
    --outputdir C:\Qt ^
    --modules qtmultimedia qtshadertools
if %ERRORLEVEL% neq 0 (
    echo ERROR: Qt installation failed
    exit /b 1
)

echo Deploying Qt DLLs...
set WINDEPLOYQT=C:\Qt\6.5.0\msvc2019_64\bin\windeployqt6.exe

if not exist "%WINDEPLOYQT%" (
    echo ERROR: windeployqt6.exe not found at %WINDEPLOYQT%
    exit /b 1
)

"%WINDEPLOYQT%" ^
    --release ^
    --qmldir . ^
    --no-translations ^
    build\Release\eye_gymnasticsApp.exe

cd python_renderer
py -3.10 -m venv .venv
.venv\Scripts\pip install ^
    colormath==3.0.0 ^
    networkx==3.4.2 ^
    numpy==2.2.6 ^
    opencv-python==4.13.0.92 ^
    pygame==2.6.1 ^
    PyOpenGL==3.1.10 ^
    python-json-logger==4.0.0

if %ERRORLEVEL% neq 0 (
    echo ERROR: Python dependencies failed
    exit /b 1
)
cd ..

if exist build rmdir /s /q build


cmake -B build ^
    -G "Visual Studio 17 2022" ^
    -A x64 ^
    -DCMAKE_PREFIX_PATH=C:\Qt\6.5.0\msvc2019_64 ^
    -DBUILD_QDS_COMPONENTS=OFF ^
    -DLINK_INSIGHT=OFF

if %ERRORLEVEL% neq 0 (
    echo ERROR: CMake configure failed
    exit /b 1
)

cmake --build build --config Release

if %ERRORLEVEL% neq 0 (
    echo ERROR: Build failed
    exit /b 1
)


COPY build.sh /usr/local/bin/build.sh
RUN chmod +x /usr/local/bin/build.sh

CMD ["/bin/bash"]
