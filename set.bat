@echo off
setlocal enabledelayedexpansion





pip install aqtinstall
aqt install-qt windows desktop 6.5.0 win64_msvc2019_64 ^
    --outputdir C:\Qt ^
    --modules qtmultimedia qtshadertools

if %ERRORLEVEL% neq 0 (
    echo ERROR: Qt installation failed
    exit /b 1
)



cd python_renderer
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

if %ERRORLEVEL% neq 0 (
    echo ERROR: Python dependencies failed
    exit /b 1
)
cd ..



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


echo Run with: .\build\Release\eye_gymnasticsApp.exe
