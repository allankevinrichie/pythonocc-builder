# pythonocc-core Wheel Builder

This repository contains an automated build system to compile and package `pythonocc-core` wheels for Linux. It builds OpenCASCADE Technology (OCCT) and all necessary third-party dependencies from source, ensuring that the resulting wheels are self-contained and compatible with standard Linux distributions (via `manylinux_2_28_x86_64` compliance).

## Features

-   **Full Source Build**: Compiles Tcl/Tk, FreeType, SWIG, and OCCT 7.9.0 from source.
-   **Multi-Python Support**: Automatically creates environments and builds wheels for Python 3.10, 3.11, 3.12, and 3.13.
-   **Self-Contained Wheels**: Uses `auditwheel` to bundle all shared libraries (OCCT, Tcl/Tk, FreeType) into the wheel.
-   **Automated Workflow**: A single script handles the entire process from dependency compilation to wheel packaging.

## Repository Structure

-   `src/occt`: OpenCASCADE Technology source code (Git Submodule).
-   `src/pythonocc-core`: pythonocc-core source code (Git Submodule).
-   `src/3rdparty/`: Source tarballs for Tcl, Tk, FreeType, and SWIG.
-   `build_wheels.py`: Main driver script for the build process.
-   `build_3rdparty.py`: Helper script to compile dependencies and OCCT.
-   `create_wheel.py`: Helper script to package the compiled artifacts into a .whl file.

## Prerequisites

-   Linux (tested on AlmaLinux 8 / compatible with manylinux_2_28).
-   Python 3 (for running the build scripts).
-   `git`, `cmake`, `make`, `gcc`, `g++`.
-   `uv` (will be automatically installed if missing, but having it pre-installed is fine).

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

### 2. Run the Build

The `build_wheels.py` script manages the entire process. It will:
1.  Build Tcl, Tk, FreeType, and SWIG.
2.  Build OCCT 7.9.0 linking against these local dependencies.
3.  For each target Python version (3.10-3.13):
    -   Create a virtual environment using `uv`.
    -   Compile `pythonocc-core`.
    -   Package the wheel.
    -   Repair the wheel using `auditwheel` to include shared libraries.

```bash
./build_wheels.py
```

You can customize the build using arguments (though defaults are usually sufficient):

```bash
./build_wheels.py --py-versions 3.11 3.12 --plat-tag manylinux_2_28_x86_64
```

### 3. Output

The final, ready-to-use wheels will be placed in the `wheels/` directory.

```bash
ls wheels/
# pythonocc_core-7.9.0-cp311-cp311-manylinux_2_28_x86_64.whl
# pythonocc_core-7.9.0-cp312-cp312-manylinux_2_28_x86_64.whl
# ...
```

## Installation

You can install the generated wheels directly with pip:

```bash
pip install wheels/pythonocc_core-7.9.0-cp312-cp312-manylinux_2_28_x86_64.whl
```

No external system dependencies (like OCCT or Tcl/Tk) are required at runtime.
