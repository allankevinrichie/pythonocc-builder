#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import tarfile
import argparse
from pathlib import Path

def run_command(cmd, cwd=None, env=None, shell=False):
    """Run a shell command and handle errors."""
    print(f"Running: {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
    sys.stdout.flush()
    try:
        subprocess.check_call(cmd, cwd=cwd, env=env, shell=shell)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        sys.exit(1)

def extract_tar(tar_path, extract_to):
    """Extract a tar.gz file."""
    print(f"Extracting {tar_path} to {extract_to}...")
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(path=extract_to)

def build_tcl(src_root, install_dir):
    """Build Tcl."""
    tcl_src = next(Path(src_root).glob("tcl8*"))
    unix_dir = tcl_src / "unix"
    print(f"Building Tcl from {unix_dir}...")
    
    cmd = [
        str(unix_dir / "configure"),
        f"--prefix={install_dir}",
        "--enable-shared"
    ]
    run_command(cmd, cwd=unix_dir)
    run_command(["make", f"-j{os.cpu_count()}"], cwd=unix_dir)
    run_command(["make", "install"], cwd=unix_dir)

def build_tk(src_root, install_dir, tcl_install_dir):
    """Build Tk."""
    tk_src = next(Path(src_root).glob("tk8*"))
    unix_dir = tk_src / "unix"
    print(f"Building Tk from {unix_dir}...")
    
    cmd = [
        str(unix_dir / "configure"),
        f"--prefix={install_dir}",
        "--enable-shared",
        f"--with-tcl={tcl_install_dir}/lib"
    ]
    run_command(cmd, cwd=unix_dir)
    run_command(["make", f"-j{os.cpu_count()}"], cwd=unix_dir)
    run_command(["make", "install"], cwd=unix_dir)

def build_freetype(src_root, install_dir):
    """Build FreeType."""
    ft_src = next(Path(src_root).glob("freetype-*"))
    print(f"Building FreeType from {ft_src}...")
    
    cmd = [
        str(ft_src / "configure"),
        f"--prefix={install_dir}",
        "--enable-shared"
    ]
    run_command(cmd, cwd=ft_src)
    run_command(["make", f"-j{os.cpu_count()}"], cwd=ft_src)
    run_command(["make", "install"], cwd=ft_src)

def build_swig(src_root, install_dir):
    """Build SWIG."""
    swig_src = next(Path(src_root).glob("swig-*"))
    print(f"Building SWIG from {swig_src}...")
    
    cmd = [
        str(swig_src / "configure"),
        f"--prefix={install_dir}"
    ]
    run_command(cmd, cwd=swig_src)
    run_command(["make", f"-j{os.cpu_count()}"], cwd=swig_src)
    run_command(["make", "install"], cwd=swig_src)

def build_occt(occt_src, install_dir, tcl_dir, freetype_dir):
    """Build OCCT."""
    build_dir = Path("build/occt")
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Building OCCT from {occt_src}...")
    
    cmake_cmd = [
        "cmake",
        str(occt_src),
        f"-DINSTALL_DIR={install_dir}",
        "-DUSE_FREETYPE=ON",
        f"-D3RDPARTY_FREETYPE_DIR={freetype_dir}",
        f"-D3RDPARTY_FREETYPE_INCLUDE_DIR_ft2build={freetype_dir}/include/freetype2",
        f"-D3RDPARTY_FREETYPE_INCLUDE_DIR_freetype2={freetype_dir}/include/freetype2",
        f"-D3RDPARTY_FREETYPE_LIBRARY_DIR={freetype_dir}/lib",
        "-DUSE_TCL=ON",
        "-DUSE_TK=ON",
        f"-D3RDPARTY_TCL_DIR={tcl_dir}",
        f"-D3RDPARTY_TK_DIR={tcl_dir}",
        f"-D3RDPARTY_TCL_INCLUDE_DIR={tcl_dir}/include",
        f"-D3RDPARTY_TK_INCLUDE_DIR={tcl_dir}/include",
        f"-D3RDPARTY_TCL_LIBRARY_DIR={tcl_dir}/lib",
        f"-D3RDPARTY_TK_LIBRARY_DIR={tcl_dir}/lib",
        # Explicitly set library paths to avoid finding system ones
        f"-D3RDPARTY_TCL_LIBRARY={tcl_dir}/lib/libtcl8.6.so",
        f"-D3RDPARTY_TK_LIBRARY={tcl_dir}/lib/libtk8.6.so",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DBUILD_RELEASE_DISABLE_EXCEPTIONS=OFF"
    ]
    
    run_command(cmake_cmd, cwd=build_dir)
    run_command(["make", f"-j{os.cpu_count()}"], cwd=build_dir)
    run_command(["make", "install"], cwd=build_dir)

def main():
    parser = argparse.ArgumentParser(description="Build 3rd-party dependencies and OCCT.")
    parser.add_argument("--src-dir", default="./src", help="Source directory root.")
    parser.add_argument("--install-dir", default="./install", help="Installation directory root.")
    parser.add_argument("--build-dir", default="./build", help="Temporary build directory.")
    
    args = parser.parse_args()
    
    src_dir = Path(args.src_dir).resolve()
    install_dir = Path(args.install_dir).resolve()
    build_dir = Path(args.build_dir).resolve()
    
    # 3rd party sources
    party3_src = src_dir / "3rdparty"
    party3_build = build_dir / "3rdparty"
    
    if party3_build.exists():
        shutil.rmtree(party3_build)
    party3_build.mkdir(parents=True, exist_ok=True)
    
    # Extract sources
    for tar in party3_src.glob("*.tar.gz"):
        extract_tar(tar, party3_build)
        
    # Build Tcl/Tk
    tcltk_install = install_dir / "tcltk"
    build_tcl(party3_build, tcltk_install)
    build_tk(party3_build, tcltk_install, tcltk_install)
    
    # Build FreeType
    freetype_install = install_dir / "freetype"
    build_freetype(party3_build, freetype_install)
    
    # Build SWIG
    swig_install = install_dir / "swig"
    build_swig(party3_build, swig_install)
    
    # Build OCCT
    occt_src = src_dir / "occt"
    occt_install = install_dir / "occt"
    build_occt(occt_src, occt_install, tcltk_install, freetype_install)
    
    print("\nAll 3rd-party dependencies and OCCT built successfully!")

if __name__ == "__main__":
    main()
