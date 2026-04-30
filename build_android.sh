#!/bin/bash
# PotholeNet v2.3 - Android Build Script
# Builds the native C++ library for Android deployment

set -e

echo "Building PotholeNet v2.3 Native Bridge for Android..."
echo

# Check if Android NDK is available
if [ -z "$ANDROID_NDK_ROOT" ]; then
    echo "ERROR: ANDROID_NDK_ROOT environment variable not set."
    echo "Please set it to your Android NDK path."
    echo "Example: export ANDROID_NDK_ROOT=/path/to/android-ndk"
    exit 1
fi

# Check if CMake is available
if ! command -v cmake &> /dev/null; then
    echo "ERROR: CMake not found. Please install CMake."
    exit 1
fi

# Create build directory
mkdir -p build_android
cd build_android

# Android ABIs to build for
ABIS=("armeabi-v7a" "arm64-v8a" "x86" "x86_64")
MIN_SDK_VERSION=21

# Build for each ABI
for ABI in "${ABIS[@]}"; do
    echo "Building for ABI: $ABI"
    
    # Create ABI-specific build directory
    mkdir -p "build_$ABI"
    cd "build_$ABI"
    
    # Configure with CMake for Android
    cmake ../.. \
        -G "Unix Makefiles" \
        -DANDROID_PLATFORM=$MIN_SDK_VERSION \
        -DANDROID_ABI=$ABI \
        -DANDROID_NDK=$ANDROID_NDK_ROOT \
        -DCMAKE_TOOLCHAIN_FILE=$ANDROID_NDK_ROOT/build/cmake/android.toolchain.cmake \
        -DCMAKE_BUILD_TYPE=Release \
        -DANDROID_BUILD=ON \
        -DBUILD_TESTS=OFF \
        -DCMAKE_INSTALL_PREFIX=../install/$ABI
    
    if [ $? -ne 0 ]; then
        echo "ERROR: CMake configuration failed for ABI $ABI"
        cd ../..
        exit 1
    fi
    
    # Build the library
    make -j$(nproc)
    
    if [ $? -ne 0 ]; then
        echo "ERROR: Build failed for ABI $ABI"
        cd ../..
        exit 1
    fi
    
    # Install to ABI-specific directory
    make install
    
    cd ..
    echo "✓ Build completed for $ABI"
done

# Create Android library structure
echo "Creating Android library structure..."
mkdir -p android_libs/lib

# Copy built libraries to Android structure
for ABI in "${ABIS[@]}"; do
    if [ -f "install/$ABI/lib/libpotholenet_core.so" ]; then
        cp "install/$ABI/lib/libpotholenet_core.so" "android_libs/lib/$ABI/"
        echo "✓ Copied libpotholenet_core.so for $ABI"
    else
        echo "⚠ Warning: Library not found for $ABI"
    fi
done

# Copy headers
mkdir -p android_libs/include
cp ../*.h android_libs/include/ 2>/dev/null || echo "No headers to copy"

cd ..

# Create Flutter-ready directory structure
echo "Creating Flutter-ready structure..."
mkdir -p flutter_integration/android/src/main/jniLibs
cp -r android_libs/lib/* flutter_integration/android/src/main/jniLibs/

echo.
echo "Android build completed successfully!"
echo.
echo "Output structure:"
echo "  android_libs/"
echo "    lib/"
for ABI in "${ABIS[@]}"; do
    if [ -f "android_libs/lib/$ABI/libpotholenet_core.so" ]; then
        echo "      $ABI/libpotholenet_core.so ✓"
    fi
done
echo "  flutter_integration/android/src/main/jniLibs/"
echo "    (ready for Flutter Android integration)"
echo.
echo "Integration instructions:"
echo "1. Copy flutter_integration/android/src/main/jniLibs to your Flutter Android project"
echo "2. Add FFI bindings in your Flutter app"
echo "3. Load library with DynamicLibrary.open('libpotholenet_core.so')"
echo.
echo "Ready for Flutter FFI integration on Android!"
