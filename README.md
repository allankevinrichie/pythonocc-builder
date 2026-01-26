# pythonocc-core Wheel Builder

This repository contains an automated build system to compile and package `pythonocc-core` wheels for Linux. It builds OpenCASCADE Technology (OCCT) and all necessary third-party dependencies from source, ensuring that the resulting wheels are self-contained and compatible with standard Linux distributions (via `manylinux_2_28_x86_64` compliance).

## Features

-   **Full Source Build**: Compiles Tcl/Tk, FreeType, SWIG, and OCCT 7.9.0 from source using CMake `ExternalProject`.
-   **Multi-Python Support**: Automatically builds wheels for Python 3.12, 3.13, and 3.14 (experimental).
-   **Self-Contained Wheels**: Uses `auditwheel` to bundle all shared libraries (OCCT, Tcl/Tk, FreeType) into the wheel.
-   **Automated Workflow**: GitHub Actions workflow using modern packaging standards (`pyproject.toml`, `scikit-build-core`).

## Repository Structure

-   `src/occt`: OpenCASCADE Technology source code (Git Submodule).
-   `src/pythonocc-core`: pythonocc-core source code (Git Submodule).
-   `src/3rdparty/`: Source tarballs for Tcl, Tk, FreeType, and SWIG.
-   `CMakeLists.txt`: Superbuild configuration to compile dependencies and OCCT.
-   `local_build.sh`: Script to run the build locally using Docker.
-   `pyproject.toml`: Configuration for the Python package build (scikit-build-core).
-   `.github/workflows/build_and_deploy.yml`: CI/CD workflow definition.

## Prerequisites

-   Linux (or any OS with Docker).
-   Docker (required for `cibuildwheel` execution).
-   Git.

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

### 2. Run the Build (Locally)

You can reproduce the CI build process locally using the provided script. This script uses Docker to build dependencies and then runs `cibuildwheel`.

```bash
./local_build.sh
```

This will:
1.  Build dependencies (OCCT, Tcl/Tk, etc.) inside a Docker container (cached in `./install`).
2.  Run `cibuildwheel` to build and repair wheels for Python 3.12, 3.13, and 3.14.

### 3. Output

The final, ready-to-use wheels will be placed in the `wheelhouse/` directory.

```bash
ls wheelhouse/
# pythonocc_core-7.9.0-cp312-cp312-manylinux_2_28_x86_64.whl
# pythonocc_core-7.9.0-cp313-cp313-manylinux_2_28_x86_64.whl
# ...
```

## Installation

You can install the generated wheels directly with pip:

```bash
pip install wheelhouse/pythonocc_core-7.9.0-cp312-cp312-manylinux_2_28_x86_64.whl
```

No external system dependencies (like OCCT or Tcl/Tk) are required at runtime.

## CI/CD

The GitHub Actions workflow (`.github/workflows/build_and_deploy.yml`) automatically builds wheels on push to `master` and deploys them to the `manylinux_2_28_x86_64` branch.
