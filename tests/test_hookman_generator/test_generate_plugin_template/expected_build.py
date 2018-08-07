import os
import shutil
import subprocess
from pathlib import Path

current_dir = Path(os.getcwd())
build_dir = current_dir / "build"
shared_lib = build_dir / "Release/acme.dll"

if build_dir.exists():
    shutil.rmtree(build_dir)

build_dir.mkdir()

binary_directory_path = f"-B{str(build_dir)}"
home_directory_path = f"-H{current_dir}"

subprocess.run(["cmake", binary_directory_path, home_directory_path])
subprocess.run(["cmake", "--build", str(build_dir), "--config", "Release"])
subprocess.run(["cp", str(shared_lib), str(current_dir)])
