import os
import shutil
import subprocess
from pathlib import Path

current_dir = Path(os.getcwd())
artifacts_dir = current_dir / "artifacts"
package_dir = current_dir / "package"
build_dir = current_dir / "build"
shared_lib = build_dir / "Release/libacme.so"

if build_dir.exists():
    shutil.rmtree(build_dir)

build_dir.mkdir()

binary_directory_path = f"-B{str(build_dir)}"
home_directory_path = f"-H{current_dir}"

subprocess.run(["cmake", binary_directory_path, home_directory_path])
subprocess.run(["cmake", "--build", str(build_dir), "--config", "Release"])

if artifacts_dir.exists():
    shutil.rmtree(artifacts_dir)

shutil.copytree(src=package_dir, dst=artifacts_dir)
shutil.copy2(src=shared_lib, dst=artifacts_dir)

