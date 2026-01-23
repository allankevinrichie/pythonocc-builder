# pythonocc-core Wheel Builder

This repository contains an automated build system to compile and package `pythonocc-core` wheels for Linux. It builds OpenCASCADE Technology (OCCT) and all necessary third-party dependencies from source, ensuring that the resulting wheels are self-contained and compatible with standard Linux distributions (via `manylinux_2_28_x86_64` compliance).

## Features

-   **Full Source Build**: Compiles Tcl/Tk, FreeType, SWIG, and OCCT 7.9.0 from source.
-   **Multi-Python Support**: Uses `cibuildwheel` to automatically build wheels for Python 3.10, 3.11, 3.12, and 3.13.
-   **Self-Contained Wheels**: Uses `auditwheel` to bundle all shared libraries (OCCT, Tcl/Tk, FreeType) into the wheel.
-   **Automated Workflow**: Fully automated GitHub Actions workflow using modern packaging standards (`pyproject.toml`, `scikit-build-core`).

## Repository Structure

-   `src/occt`: OpenCASCADE Technology source code (Git Submodule).
-   `src/pythonocc-core`: pythonocc-core source code (Git Submodule).
-   `src/3rdparty/`: Source tarballs for Tcl, Tk, FreeType, and SWIG.
-   `build_3rdparty.py`: Helper script to compile dependencies and OCCT.
-   `pyproject.toml`: Configuration for the Python package build (scikit-build-core).
-   `.github/workflows/build_and_deploy.yml`: CI/CD workflow definition.

## Prerequisites

-   Linux (tested on Ubuntu 22.04+ / manylinux_2_28).
-   Python 3.
-   `git`, `cmake`, `make`, `gcc`, `g++`.
-   Docker (for local `cibuildwheel` execution).

## Usage

### 1. Clone the Repository

Make sure to clone with submodules to get the source code for OCCT and pythonocc-core.

```bash
git clone --recursive <repository-url>
cd <repository-directory>
```

If you already cloned without submodules:

```bash
git submodule update --init --recursive
```

### 2. Run the Build (Locally with cibuildwheel)

You can reproduce the CI build process locally using `cibuildwheel`. This requires Docker.

First, install `cibuildwheel`:

```bash
pip install cibuildwheel
```

Then, run the build (this will pull the manylinux container and run the build inside it):

```bash
# Build only for Python 3.10 as an example
export CIBW_BUILD=cp310-manylinux_x86_64

# Define the setup script (same as in CI)
export CIBW_BEFORE_ALL_LINUX="yum install -y wget git cmake libX11-devel libXext-devel libXt-devel libXi-devel libXmu-devel mesa-libGL-devel mesa-libGLU-devel pcre2-devel fontconfig-devel && python3 build_3rdparty.py --src-dir src --install-dir /host/install --build-dir build"

# Define environment variables for CMake
export CIBW_ENVIRONMENT_LINUX='OCCT_INCLUDE_DIR="/host/install/occt/include/opencascade" OCCT_LIBRARY_DIR="/host/install/occt/lib" LD_LIBRARY_PATH="/host/install/occt/lib:/host/install/tcltk/lib:/host/install/freetype/lib:$LD_LIBRARY_PATH" SKBUILD_CMAKE_DEFINE="OCCT_INCLUDE_DIR=/host/install/occt/include/opencascade;OCCT_LIBRARY_DIR=/host/install/occt/lib;SWIG_EXECUTABLE=/host/install/swig/bin/swig"'

# Define repair command
export CIBW_REPAIR_WHEEL_COMMAND_LINUX="export LD_LIBRARY_PATH=/host/install/occt/lib:/host/install/tcltk/lib:/host/install/freetype/lib:$LD_LIBRARY_PATH && auditwheel repair -w {dest_dir} {wheel}"

cibuildwheel --platform linux
```

### 3. Output

The final, ready-to-use wheels will be placed in the `wheelhouse/` directory.

```bash
ls wheelhouse/
# pythonocc_core-7.9.0-cp310-cp310-manylinux_2_28_x86_64.whl
# ...
```

## Installation

You can install the generated wheels directly with pip:

```bash
pip install wheelhouse/pythonocc_core-7.9.0-cp310-cp310-manylinux_2_28_x86_64.whl
```

No external system dependencies (like OCCT or Tcl/Tk) are required at runtime.
