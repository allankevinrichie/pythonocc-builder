import sys
import sysconfig
import os
import subprocess
from pathlib import Path

def check_python_detection():
    print(f"Current Python: {sys.executable}")
    print(f"Version: {sys.version}")
    
    # Simulate the logic in build_wheels.py
    python_exe = sys.executable
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    
    print("\n--- Simulation of build_wheels.py logic ---")
    
    # 1. Include Dir
    python_include = sysconfig.get_path('include')
    print(f"PYTHON_INCLUDE_DIR: {python_include}")
    if not os.path.exists(python_include):
        print("  [WARNING] Include dir does not exist!")
    
    # 2. Lib Dir
    libdir = sysconfig.get_config_var('LIBDIR')
    ldlibrary = sysconfig.get_config_var('LDLIBRARY')
    library = sysconfig.get_config_var('LIBRARY')
    
    print(f"sysconfig LIBDIR: {libdir}")
    print(f"sysconfig LDLIBRARY: {ldlibrary}")
    print(f"sysconfig LIBRARY: {library}")

    # 3. Search Logic
    python_lib = os.path.join(libdir, ldlibrary)
    print(f"Initial guess PYTHON_LIBRARY: {python_lib}")
    
    final_lib = None
    
    if not os.path.exists(python_lib) or os.path.isdir(python_lib):
        print("  -> Initial guess is invalid (not found or is dir). Searching...")
        
        candidates = list(Path(libdir).glob(f"libpython{python_version}*.so*"))
        static_candidates = list(Path(libdir).glob(f"libpython{python_version}*.a"))

        # If not found in libdir, try looking in lib64 (sometimes libdir is lib but real libs are in lib64)
        if not candidates and not static_candidates:
             parent = Path(libdir).parent
             if (parent / "lib64").exists():
                 print(f"  -> Checking lib64: {parent}/lib64")
                 candidates.extend(list((parent / "lib64").glob(f"libpython{python_version}*.so*")))
                 static_candidates.extend(list((parent / "lib64").glob(f"libpython{python_version}*.a")))
         
        # Also try looking in python3.X/config-... dir inside libdir
        if not candidates and not static_candidates:
             config_dirs = list(Path(libdir).glob(f"python{python_version}*/config*"))
             print(f"  -> Checking config dirs: {[str(d) for d in config_dirs]}")
             for cdir in config_dirs:
                  candidates.extend(list(cdir.glob(f"libpython{python_version}*.so*")))
                  static_candidates.extend(list(cdir.glob(f"libpython{python_version}*.a")))

        print(f"  -> Shared lib candidates: {[str(c) for c in candidates]}")
        print(f"  -> Static lib candidates: {[str(c) for c in static_candidates]}")
        
        if candidates:
            final_lib = str(candidates[0])
            print(f"  -> Selected SHARED lib: {final_lib}")
        elif static_candidates:
            final_lib = str(static_candidates[0])
            print(f"  -> Selected STATIC lib: {final_lib}")
        else:
            print("  -> [ERROR] No suitable library found!")
    else:
        final_lib = python_lib
        print(f"  -> Initial guess is VALID.")

    if final_lib:
        print(f"\nFINAL DECISION for CMake: -DPYTHON_LIBRARY={final_lib}")
    else:
        print(f"\nFINAL DECISION for CMake: (NOT SET)")

if __name__ == "__main__":
    check_python_detection()
