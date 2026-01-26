#!/bin/bash
set -e

# Configuration
DEPENDENCIES_DIR="$(pwd)/install"
CACHE_MARKER=".deps_built"

# 1. Build Dependencies (if not cached)
if [ ! -f "$CACHE_MARKER" ]; then
    echo "Building dependencies (simulating build_deps job)..."
    docker run --rm -v $(pwd):/host quay.io/pypa/manylinux_2_28_x86_64:latest /bin/bash -c "
        yum install -y wget git cmake libX11-devel libXext-devel libXt-devel libXi-devel libXmu-devel mesa-libGL-devel mesa-libGLU-devel pcre2-devel fontconfig-devel &&
        cd /host &&
        cmake -S . -B build -DINSTALL_DIR=/host/install &&
        cmake --build build
    "
    touch "$CACHE_MARKER"
    echo "Dependencies built and cached in $DEPENDENCIES_DIR"
else
    echo "Using cached dependencies from $DEPENDENCIES_DIR"
fi

# 2. Build Wheels (simulating build_wheels job)
echo "Building wheels..."
export CIBW_PLATFORM=linux
export CIBW_BUILD="cp312-manylinux_x86_64 cp313-manylinux_x86_64 cp314-manylinux_x86_64"
export CIBW_MANYLINUX_X86_64_IMAGE="quay.io/pypa/manylinux_2_28_x86_64:latest"
export CIBW_BEFORE_ALL_LINUX="yum install -y wget git cmake libX11-devel libXext-devel libXt-devel libXi-devel libXmu-devel mesa-libGL-devel mesa-libGLU-devel pcre2-devel fontconfig-devel rapidjson-devel && sed -i 's/COMPONENTS Interpreter Development REQUIRED/COMPONENTS Interpreter Development.Module REQUIRED/g' src/pythonocc-core/CMakeLists.txt && sed -i 's/COMPONENTS Interpreter Development NumPy REQUIRED/COMPONENTS Interpreter Development.Module NumPy REQUIRED/g' src/pythonocc-core/CMakeLists.txt"
export CIBW_ENVIRONMENT_LINUX="OCCT_INCLUDE_DIR=\"/project/install/include/opencascade\" OCCT_LIBRARY_DIR=\"/project/install/lib\" LD_LIBRARY_PATH=\"/project/install/lib:\$LD_LIBRARY_PATH\" SKBUILD_CMAKE_DEFINE=\"OCCT_INCLUDE_DIR=/project/install/include/opencascade;OCCT_LIBRARY_DIR=/project/install/lib;SWIG_EXECUTABLE=/project/install/bin/swig;SWIG_DIR=/project/install/share/swig/4.2.1;FREETYPE_DIR=/project/install;FREETYPE_INCLUDE_DIR_freetype2=/project/install/include/freetype2;FREETYPE_LIBRARY=/project/install/lib/libfreetype.so;PYTHONOCC_MESHDS_NUMPY=ON;PYTHONOCC_INSTALL_DIRECTORY=OCC\""
export CIBW_REPAIR_WHEEL_COMMAND_LINUX="export LD_LIBRARY_PATH=/project/install/lib:\$LD_LIBRARY_PATH && auditwheel repair -w {dest_dir} {wheel}"

# Clean previous build artifacts
rm -rf build src/pythonocc-core/build src/pythonocc-core/dist src/pythonocc-core/*.egg-info src/pythonocc-core/src/SWIG_files/wrapper/*.so build_wheel_*

# Run cibuildwheel
cibuildwheel --platform linux

echo "Build complete. Wheels are in ./wheelhouse"
