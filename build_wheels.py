#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import argparse
import glob
from pathlib import Path

def run_command(cmd, cwd=None, env=None, shell=False):
    """Run a shell command and handle errors."""
    print(f"Running: {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
    sys.stdout.flush()
    try:
        subprocess.check_call(cmd, cwd=cwd, env=env, shell=shell)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        # If output was captured, printing it here would be useful.
        # But check_call streams to stdout/stderr by default, so user should have seen it.
        # We can try to provide more context if needed.
        sys.exit(1)

def ensure_uv():
    """Ensure uv is installed."""
    try:
        subprocess.check_call(["uv", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("uv is already installed.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Installing uv...")
        run_command("curl -LsSf https://astral.sh/uv/install.sh | sh", shell=True)
        # Update PATH to include ~/.local/bin if not already present
        local_bin = os.path.expanduser("~/.local/bin")
        if local_bin not in os.environ["PATH"]:
            os.environ["PATH"] = f"{local_bin}:{os.environ['PATH']}"

def create_venv(python_version, venv_path):
    """Create a virtual environment using uv."""
    print(f"Creating virtual environment for Python {python_version} at {venv_path}...")
    run_command(["uv", "venv", str(venv_path), "--python", python_version])
    
    # Install dependencies
    # uv is not installed inside the venv by default when using 'uv venv'.
    # We should use the global 'uv pip' command and point it to the venv python.
    # Or simply activate the venv, but subprocess doesn't support 'activate'.
    # Better approach: 'uv pip install --python <path_to_venv_python> ...'
    
    python_exe = Path(venv_path) / "bin" / "python"
    pip_cmd = ["uv", "pip", "install", "--python", str(python_exe), "numpy", "wheel", "build", "auditwheel"]
    run_command(pip_cmd)

def compile_pythonocc(python_version, venv_path, src_dir, occt_install_dir, build_base_dir, install_base_dir):
    """Compile pythonocc-core for a specific Python version."""
    venv_bin = Path(venv_path) / "bin"
    python_exe = venv_bin / "python"
    
    # Get numpy include dir
    numpy_include = subprocess.check_output(
        [str(python_exe), "-c", "import numpy; print(numpy.get_include())"],
        text=True
    ).strip()
    
    # Get python include dir
    python_include = subprocess.check_output(
        [str(python_exe), "-c", "import sysconfig; print(sysconfig.get_path('include'))"],
        text=True
    ).strip()

    # Get python library
    # We try to find the shared library.
    # On manylinux, it might be in /opt/python/cp310-cp310/lib/libpython3.10.so or similar.
    # Or in standard locations.
    python_lib = subprocess.check_output(
        [str(python_exe), "-c", "import sysconfig; import os; print(os.path.join(sysconfig.get_config_var('LIBDIR'), sysconfig.get_config_var('LDLIBRARY')))"],
        text=True
    ).strip()
    
    # Fallback if the specific .so path doesn't exist (sometimes LDLIBRARY is just the name)
    # AND sometimes sysconfig reports a static lib (.a) but we need shared, or it reports nothing useful.
    if not os.path.exists(python_lib) or os.path.isdir(python_lib):
         # Try just LIBDIR, but CMake expects a FILE path for PYTHON_LIBRARY if we want to be explicit.
         # However, if we give a directory, FindPython might get confused or treat it as a lib path search dir.
         # Let's try to be smarter.
         libdir = subprocess.check_output(
            [str(python_exe), "-c", "import sysconfig; print(sysconfig.get_config_var('LIBDIR'))"],
            text=True
         ).strip()
         
         # Try to find libpython*.so in libdir
         # In manylinux, libpythonX.Y.so usually exists in /usr/lib64 or /usr/local/lib or /opt/python/.../lib
         # We search recursively? No, just in libdir.
         candidates = list(Path(libdir).glob(f"libpython{python_version}*.so*"))
         
         # Also try static lib if shared is not found, CMake might accept it.
         static_candidates = list(Path(libdir).glob(f"libpython{python_version}*.a"))
         
         if candidates:
             python_lib = str(candidates[0])
         elif static_candidates:
             python_lib = str(static_candidates[0])
         else:
             # If we can't find it, maybe we are on a static python build (manylinux often is).
             # But pythonocc needs to link against something? 
             # Actually, for extension modules, we shouldn't link against libpython on Linux 
             # (symbols are exported by the executable).
             # But FindPython3 module insists on finding it if Development component is requested.
             
             # IMPORTANT: On manylinux, we might not have a shared libpython.
             # We can try to trick CMake by not setting PYTHON_LIBRARY and let it find what it can,
             # OR we point it to the static lib if we found it.
             
             # If we failed to find any lib file, let's try to find it in standard system paths
             # or just unset python_lib so we don't pass a directory as a file.
             pass

    build_dir = Path(build_base_dir) / f"pythonocc-{python_version}"
    install_dir = Path(install_base_dir) / f"pythonocc-{python_version}"
    
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)
    
    cmake_cmd = [
        "cmake",
        str(src_dir),
        f"-DOCCT_INCLUDE_DIR={occt_install_dir}/include/opencascade",
        f"-DOCCT_LIBRARY_DIR={occt_install_dir}/lib",
        f"-DPYTHONOCC_INSTALL_DIRECTORY={install_dir}",
        f"-DSWIG_EXECUTABLE={occt_install_dir}/../swig/bin/swig", # Assuming swig is in ../swig relative to occt
        "-DCMAKE_BUILD_TYPE=Release",
        # Force FindPython3 to use the artifacts from our specified environment
        "-DPython3_FIND_STRATEGY=LOCATION", 
        f"-DPYTHON_EXECUTABLE={python_exe}",
        f"-DPYTHON_INCLUDE_DIR={python_include}",
        f"-DPYTHON_INCLUDE_DIRS={python_include};{numpy_include}"
    ]
    
    # Only add PYTHON_LIBRARY if it points to a file. 
    # If it points to a dir or doesn't exist, passing it might confuse CMake.
    if os.path.exists(python_lib) and os.path.isfile(python_lib):
        cmake_cmd.append(f"-DPYTHON_LIBRARY={python_lib}")
    
    # Set CPLUS_INCLUDE_PATH for numpy headers during make
    env = os.environ.copy()
    env["CPLUS_INCLUDE_PATH"] = f"{numpy_include}:{env.get('CPLUS_INCLUDE_PATH', '')}"
    
    print(f"Configuring pythonocc for Python {python_version}...")
    run_command(cmake_cmd, cwd=build_dir, env=env)
    
    print(f"Building pythonocc for Python {python_version}...")
    run_command(["make", f"-j{os.cpu_count()}"], cwd=build_dir, env=env)
    
    print(f"Installing pythonocc for Python {python_version}...")
    run_command(["make", "install"], cwd=build_dir, env=env)
    
    return install_dir

def package_wheel(install_dir, python_version, output_dir, create_wheel_script):
    """Package the installed pythonocc into a wheel."""
    # python_version format "3.12" -> tag "cp312"
    ver_parts = python_version.split('.')
    abi_tag = f"cp{ver_parts[0]}{ver_parts[1]}"
    
    raw_wheels_dir = Path(output_dir) / "raw"
    raw_wheels_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Packaging wheel for {python_version} ({abi_tag})...")
    # We use the system python to run the wheel creation script, as it just purely python logic
    # But we pass the tag explicitly
    run_command([sys.executable, create_wheel_script, str(install_dir), str(raw_wheels_dir), abi_tag])
    
    # Find the created wheel
    wheels = list(raw_wheels_dir.glob(f"*{abi_tag}*.whl"))
    if not wheels:
        raise RuntimeError(f"No wheel found for {abi_tag} in {raw_wheels_dir}")
    return wheels[0]

def repair_wheel(wheel_path, plat_tag, output_dir, venv_path, occt_lib_path):
    """Repair the wheel using auditwheel."""
    print(f"Repairing wheel {wheel_path} for platform {plat_tag}...")
    
    # Set LD_LIBRARY_PATH to include OCCT libs so auditwheel can find them
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = f"{occt_lib_path}:{env.get('LD_LIBRARY_PATH', '')}"
    
    auditwheel_cmd = [
        str(Path(venv_path) / "bin" / "python"),
        "-m", "auditwheel", "repair",
        str(wheel_path),
        "--plat", plat_tag,
        "-w", str(output_dir)
    ]
    
    run_command(auditwheel_cmd, env=env)

def main():
    parser = argparse.ArgumentParser(description="Automated pythonocc-core build and wheel packaging script.")
    parser.add_argument("--py-versions", nargs="+", default=["3.10", "3.11", "3.12", "3.13"], help="List of Python versions to build for.")
    parser.add_argument("--plat-tag", default="manylinux_2_28_x86_64", help="Platform tag for auditwheel (e.g., manylinux_2_28_x86_64).")
    parser.add_argument("--occt-install-dir", default="./install/occt", help="Path to OCCT installation directory (containing include/ and lib/).")
    parser.add_argument("--occt-lib-path", default="./install/occt/lib:./install/tcltk/lib:./install/freetype/lib", help="LD_LIBRARY_PATH components for OCCT and dependencies (separated by :).")
    parser.add_argument("--src-dir", default="./src/pythonocc-core", help="Path to pythonocc-core source directory.")
    parser.add_argument("--work-dir", default="./work_wheels", help="Working directory for builds and venvs.")
    parser.add_argument("--output-dir", default="./wheels", help="Directory to store final wheels.")
    parser.add_argument("--create-wheel-script", default="./create_wheel.py", help="Path to the create_wheel.py script.")

    args = parser.parse_args()

    ensure_uv()
    
    work_dir = Path(args.work_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    src_dir = Path(args.src_dir).resolve()
    occt_install_dir = Path(args.occt_install_dir).resolve()
    create_wheel_script = Path(args.create_wheel_script).resolve()
    
    # Resolve occt_lib_path components relative to current dir if they are relative
    occt_lib_paths = []
    for p in args.occt_lib_path.split(':'):
        resolved_p = Path(p).resolve()
        occt_lib_paths.append(str(resolved_p))
    occt_lib_path_str = ':'.join(occt_lib_paths)
    
    work_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 0. Build 3rd-party dependencies and OCCT
    print("\n=== Building 3rd-party dependencies and OCCT ===")
    # Run build_3rdparty.py first
    # Assume it's in the same directory as this script
    build_3rdparty_script = Path(__file__).parent / "build_3rdparty.py"
    run_command([sys.executable, str(build_3rdparty_script), "--src-dir", str(src_dir.parent), "--install-dir", str(occt_install_dir.parent)])

    for py_ver in args.py_versions:
        print(f"\n=== Processing Python {py_ver} ===")
        venv_path = work_dir / f"venv-{py_ver}"
        
        # 1. Create Environment
        create_venv(py_ver, venv_path)
        
        # 2. Compile pythonocc
        install_dir = compile_pythonocc(
            py_ver, 
            venv_path, 
            src_dir, 
            occt_install_dir, 
            work_dir / "build", 
            work_dir / "install"
        )
        
        # 3. Package Wheel
        raw_wheel = package_wheel(install_dir, py_ver, work_dir / "wheels_raw", create_wheel_script)
        
        # 4. Repair Wheel
        repair_wheel(raw_wheel, args.plat_tag, output_dir, venv_path, occt_lib_path_str)

    print(f"\nAll builds complete! Wheels are in {output_dir}")

if __name__ == "__main__":
    main()
