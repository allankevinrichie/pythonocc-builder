import os
import shutil
import sys
from wheel.wheelfile import WheelFile
from email.message import Message

def create_wheel(src_dir, output_dir, python_version):
    # python_version e.g., "cp311"
    package_name = "pythonocc_core"
    version = "7.9.0"
    
    # Tag
    abi_tag = f"{python_version}" # e.g. cp311
    platform_tag = "linux_x86_64"
    tag = f"{python_version}-{abi_tag}-{platform_tag}"
    
    wheel_name = f"{package_name}-{version}-{tag}.whl"
    dist_info_dir = f"{package_name}-{version}.dist-info"
    
    build_dir = f"build_wheel_{python_version}"
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir)
    
    # 1. Copy package content
    # src_dir (install/pythonocc) -> build_dir/OCC
    dest_pkg_dir = os.path.join(build_dir, "OCC")
    shutil.copytree(src_dir, dest_pkg_dir)
    
    # 2. Create .dist-info
    dest_dist_info = os.path.join(build_dir, dist_info_dir)
    os.makedirs(dest_dist_info)
    
    # METADATA
    with open(os.path.join(dest_dist_info, 'METADATA'), 'w') as f:
        f.write(f"Metadata-Version: 2.1\n")
        f.write(f"Name: pythonocc-core\n")
        f.write(f"Version: {version}\n")
        f.write(f"Summary: pythonocc-core 7.9.0 built from source\n")
        f.write(f"\n")
        
    # WHEEL
    with open(os.path.join(dest_dist_info, 'WHEEL'), 'w') as f:
        f.write(f"Wheel-Version: 1.0\n")
        f.write(f"Generator: custom\n")
        f.write(f"Root-Is-Purelib: false\n")
        f.write(f"Tag: {tag}\n")

    # 3. Pack
    output_wheel_path = os.path.join(output_dir, wheel_name)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print(f"Packing {build_dir} to {output_wheel_path}...")
    with WheelFile(output_wheel_path, 'w') as wf:
        wf.write_files(build_dir)
        
    print(f"Created {output_wheel_path}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python create_wheel.py <src_dir> <output_dir> <python_tag>")
        sys.exit(1)
    create_wheel(sys.argv[1], sys.argv[2], sys.argv[3])
