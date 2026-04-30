# PotholeNet v2.3 - Native Bridge CMake Configuration
# Cross-platform build system for Windows DLL and Android .so

cmake_minimum_required(VERSION 3.16)
project(PotholeNetCore VERSION 2.3.0 LANGUAGES CXX)

# Set C++17 standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Build configuration
option(BUILD_SHARED_LIBS "Build shared libraries" ON)
option(BUILD_TESTS "Build unit tests" OFF)
option(ENABLE_PROFILING "Enable performance profiling" OFF)
option(ANDROID_BUILD "Building for Android" OFF)

# Platform detection
if(WIN32)
    set(PLATFORM_WINDOWS TRUE)
elseif(ANDROID)
    set(PLATFORM_ANDROID TRUE)
elseif(APPLE)
    set(PLATFORM_MACOS TRUE)
elseif(UNIX)
    set(PLATFORM_LINUX TRUE)
endif()

# Compiler-specific optimizations
if(CMAKE_CXX_COMPILER_ID MATCHES "MSVC")
    # Microsoft Visual C++ optimizations
    add_compile_options(/O2 /Ob2 /Ot)
    add_compile_definitions(_CRT_SECURE_NO_WARNINGS)
    add_compile_definitions(POTHOLENET_CORE_EXPORTS)
    
    # Enable high-performance floating point
    if(CMAKE_BUILD_TYPE STREQUAL "Release")
        add_compile_options(/fp:fast)
    endif()
    
elseif(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    # GCC/Clang optimizations
    add_compile_options(-O3 -march=native -mtune=native)
    add_compile_options(-ffast-math -funroll-loops)
    
    # Position-independent code for shared libraries
    set(CMAKE_POSITION_INDEPENDENT_CODE ON)
    
    # Export symbols
    add_compile_definitions(POTHOLENET_CORE_EXPORTS)
endif()

# Source files
set(CORE_SOURCES
    potholenet_core.cpp
)

# Header files
set(PUBLIC_HEADERS
    potholenet_core.h
)

# Create shared library
add_library(potholenet_core SHARED ${CORE_SOURCES})

# Set target properties
set_target_properties(potholenet_core PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION ${PROJECT_VERSION_MAJOR}
    PUBLIC_HEADER "${PUBLIC_HEADERS}"
)

# Platform-specific library naming
if(PLATFORM_WINDOWS)
    set_target_properties(potholenet_core PROPERTIES
        OUTPUT_NAME "potholenet_core"
        PREFIX "lib"
        SUFFIX ".dll"
    )
elseif(PLATFORM_ANDROID)
    set_target_properties(potholenet_core PROPERTIES
        OUTPUT_NAME "potholenet_core"
        PREFIX "lib"
        SUFFIX ".so"
    )
else()
    set_target_properties(potholenet_core PROPERTIES
        OUTPUT_NAME "potholenet_core"
        PREFIX "lib"
        SUFFIX ".so"
    )
endif()

# Include directories
target_include_directories(potholenet_core
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}
)

# Math library for Linux/Android
if(PLATFORM_LINUX OR PLATFORM_ANDROID)
    target_link_libraries(potholenet_core PRIVATE m)
endif()

# Android-specific configuration
if(PLATFORM_ANDROID)
    # Android NDK configuration
    set(ANDROID_PLATFORM_LEVEL 21)  # Android 5.0+
    set(ANDROID_STL c++_shared)
    set(ANDROID_ABI armeabi-v7a arm64-v8a x86 x86_64)
    
    # Android-specific compiler flags
    target_compile_options(potholenet_core PRIVATE
        -fno-exceptions
        -fno-rtti
        -ffunction-sections
        -fdata-sections
        -Wl,--gc-sections
    )
    
    # Linker optimizations
    target_link_options(potholenet_core PRIVATE
        -Wl,--gc-sections
        -Wl,--strip-all
    )
endif()

# Windows-specific configuration
if(PLATFORM_WINDOWS)
    # Windows-specific compiler flags
    target_compile_options(potholenet_core PRIVATE
        /D_WINDOWS
        /D_USRDLL
        /DPOTHOLENET_CORE_EXPORTS
    )
    
    # Linker options
    target_link_options(potholenet_core PRIVATE
        /DLL
        /OPT:REF
        /OPT:ICF
    )
endif()

# Profiling configuration
if(ENABLE_PROFILING)
    if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
        target_compile_options(potholenet_core PRIVATE -pg)
        target_link_options(potholenet_core PRIVATE -pg)
    elseif(CMAKE_CXX_COMPILER_ID MATCHES "MSVC")
        target_compile_options(potholenet_core PRIVATE /PROFILE)
    endif()
endif()

# Testing configuration
if(BUILD_TESTS)
    enable_testing()
    
    # Test executable
    add_executable(potholenet_test test_potholenet_core.cpp)
    target_link_libraries(potholenet_test PRIVATE potholenet_core)
    
    # Add test
    add_test(NAME PotholeNetCoreTest COMMAND potholenet_test)
endif()

# Installation configuration
install(TARGETS potholenet_core
    EXPORT PotholeNetCoreTargets
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
    PUBLIC_HEADER DESTINATION include
)

# Export configuration
install(EXPORT PotholeNetCoreTargets
    FILE PotholeNetCoreTargets.cmake
    NAMESPACE PotholeNet::
    DESTINATION lib/cmake/PotholeNetCore
)

# Package configuration
include(CMakePackageConfigHelpers)
write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/PotholeNetCoreConfigVersion.cmake"
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)

configure_package_config_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/PotholeNetCoreConfig.cmake.in"
    "${CMAKE_CURRENT_BINARY_DIR}/PotholeNetCoreConfig.cmake"
    INSTALL_DESTINATION lib/cmake/PotholeNetCore
)

install(FILES
    "${CMAKE_CURRENT_BINARY_DIR}/PotholeNetCoreConfig.cmake"
    "${CMAKE_CURRENT_BINARY_DIR}/PotholeNetCoreConfigVersion.cmake"
    DESTINATION lib/cmake/PotholeNetCore
)

# Build scripts
# Windows build script
if(PLATFORM_WINDOWS)
    configure_file(
        "${CMAKE_CURRENT_SOURCE_DIR}/build_windows.bat.in"
        "${CMAKE_CURRENT_BINARY_DIR}/build_windows.bat"
        @ONLY
    )
endif()

# Android build script
configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/build_android.sh.in"
    "${CMAKE_CURRENT_BINARY_DIR}/build_android.sh"
    @ONLY
)

# Print configuration summary
message(STATUS "PotholeNet v${PROJECT_VERSION} Configuration Summary:")
message(STATUS "  Platform: ${CMAKE_SYSTEM_NAME}")
message(STATUS "  Compiler: ${CMAKE_CXX_COMPILER_ID}")
message(STATUS "  Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "  C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "  Shared Library: ${BUILD_SHARED_LIBS}")
message(STATUS "  Tests: ${BUILD_TESTS}")
message(STATUS "  Profiling: ${ENABLE_PROFILING}")

if(PLATFORM_ANDROID)
    message(STATUS "  Android Platform: ${ANDROID_PLATFORM_LEVEL}")
    message(STATUS "  Android STL: ${ANDROID_STL}")
    message(STATUS "  Android ABI: ${ANDROID_ABI}")
endif()

# Performance warnings
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    message(WARNING "Debug build may have reduced performance. Use Release build for production.")
endif()

if(NOT CMAKE_BUILD_TYPE STREQUAL "Release" AND NOT CMAKE_BUILD_TYPE STREQUAL "RelWithDebInfo")
    message(WARNING "Optimized build recommended for mobile deployment.")
endif()
