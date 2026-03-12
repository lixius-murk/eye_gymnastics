pip install aqtinstall aqt install-qt windows desktop 6.5.0 win64_msvc2019_64 --outputdir C:\Qt --modules qtmultimedia qtshadertools

cd python_renderer python -m venv .venv .venv\Scripts\pip install -r requirements.txt

cd .. cmake -B build -G "Visual Studio 17 2022" -A x64 -DCMAKE_PREFIX_PATH=C:\Qt\6.5.0\msvc2019_64 -DBUILD_QDS_COMPONENTS=OFF -DLINK_INSIGHT=OFF cmake --build build --config Release

.\build\Release\eye_gymnasticsApp.exe
