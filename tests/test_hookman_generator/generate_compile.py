import os
import shutil
import subprocess
import sys
from pathlib import Path

current_dir = Path(os.getcwd())

artifacts_dir = current_dir / "artifacts"
assets = current_dir / "assets"
build_dir = current_dir / "build"
package_dir = current_dir / "package"

if sys.platform == 'win32':
    shared_lib_path = artifacts_dir / "acme.dll"
else:
    shared_lib_path = artifacts_dir / "libacme.so"

if build_dir.exists():
    shutil.rmtree(build_dir)

build_dir.mkdir()

binary_directory_path = f"-B{str(build_dir)}"
home_directory_path = f"-H{current_dir}"
sdk_include_dir = f"-DSDK_INCLUDE_DIR={os.getenv('SDK_INCLUDE_DIR', '')}"
build_generator = "Visual Studio 14 2015 Win64" if sys.platform == "win32" else "Unix Makefiles"
if artifacts_dir.exists():
    shutil.rmtree(artifacts_dir)

subprocess.check_call(["cmake", binary_directory_path, home_directory_path, sdk_include_dir, "-G", build_generator])
subprocess.check_call(["cmake", "--build", str(build_dir), "--config", "Release", "--target", "install"])

if package_dir.exists():
    shutil.rmtree(package_dir)

shutil.copytree(src=assets, dst=package_dir)
shutil.copy2(src=shared_lib_path, dst=package_dir)
