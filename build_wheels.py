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
    try:
        subprocess.check_call(cmd, cwd=cwd, env=env, shell=shell)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
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
    pip_cmd = [str(Path(venv_path) / "bin" / "uv"), "pip", "install", "numpy", "wheel", "build", "auditwheel"]
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
        f"-DPYTHON_EXECUTABLE={python_exe}",
        f"-DPYTHON_INCLUDE_DIRS={python_include};{numpy_include}"
    ]
    
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
        "-w", str(output_dir),
        "--patchelf-args", "--page-size 65536"
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
