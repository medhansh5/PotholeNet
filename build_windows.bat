@echo off
REM PotholeNet v2.3 - Windows Build Script
REM Builds the native C++ library for Windows testing

echo Building PotholeNet v2.3 Native Bridge for Windows...
echo.

REM Check if Visual Studio is available
where cl >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Visual Studio compiler not found. Please run this from a Visual Studio Developer Command Prompt.
    exit /b 1
)

REM Create build directory
if not exist build_windows (
    mkdir build_windows
)

cd build_windows

REM Configure with CMake
echo Configuring with CMake...
cmake .. -G "Visual Studio 16 2019" -A x64 -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: CMake configuration failed.
    cd ..
    exit /b 1
)

REM Build the project
echo Building project...
cmake --build . --config Release --parallel

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Build failed.
    cd ..
    exit /b 1
)

REM Copy output to root directory
echo Copying output files...
copy Release\libpotholenet_core.dll ..\
copy Release\potholenet_core.lib ..\

cd ..

echo.
echo Build completed successfully!
echo Output files:
echo   libpotholenet_core.dll
echo   potholenet_core.lib
echo.
echo Ready for Flutter FFI integration on Windows.

pause
