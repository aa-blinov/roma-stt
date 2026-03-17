"""Clone/pull whisper.cpp, build with CMake, copy exe and DLLs to bin/. For automated install."""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WHISPER_DIR = ROOT / "whisper.cpp"
BIN_DIR = ROOT / "bin"
REPO_URL = "https://github.com/ggml-org/whisper.cpp.git"


def run(cmd: list[str], cwd: Path, capture: bool = False) -> tuple[bool, str]:
    r = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=capture,
        text=True,
        timeout=600,
    )
    if capture:
        return r.returncode == 0, (r.stdout or "") + (r.stderr or "")
    return r.returncode == 0, ""


def check_tools() -> tuple[bool, str]:
    """Require git and cmake. Return (False, msg) if something is missing."""
    ok, _ = run(["git", "--version"], cwd=ROOT, capture=True)
    if not ok:
        return False, ("Git not found. Install it (e.g. winget install Git.Git) and run Install again.")
    ok, _ = run(["cmake", "--version"], cwd=ROOT, capture=True)
    if not ok:
        return False, ("CMake not found. Install it (e.g. winget install Kitware.CMake) and run Install again.")
    return True, ""


def clone_or_pull() -> tuple[bool, str]:
    if not WHISPER_DIR.exists():
        print("Cloning whisper.cpp...")
        ok, out = run(["git", "clone", "--depth", "1", REPO_URL, str(WHISPER_DIR)], cwd=ROOT, capture=True)
        if not ok:
            return False, f"git clone failed: {out}"
        print("Cloned.")
    else:
        print("Updating whisper.cpp (git pull)...")
        ok, out = run(["git", "pull"], cwd=WHISPER_DIR, capture=True)
        if not ok:
            return False, f"git pull failed: {out}"
        print("Updated.")
    return True, ""


def build(arch: str = "cpu") -> tuple[bool, str]:
    print(f"Configuring whisper.cpp (cmake) for {arch}...")
    cmake_args = [
        "cmake",
        "-B",
        "build",
        "-DWHISPER_BUILD_EXAMPLES=ON",
        "-DWHISPER_BUILD_TESTS=OFF",
    ]
    if arch == "cuda":
        cmake_args.append("-DGGML_CUDA=ON")
    elif arch == "amd":
        cmake_args.append("-DGGML_VULKAN=ON")

    ok, out = run(cmake_args, cwd=WHISPER_DIR, capture=True)
    if not ok:
        hint = ""
        if arch == "cuda" and ("nvcc" in out or "CUDA Toolkit" in out or "CUDAToolkit" in out):
            hint = (
                "\n\nДля CUDA нужен NVIDIA CUDA Toolkit. "
                "Установить через батник: пункт 0 (Установка программ), затем ответить «y» на вопрос про CUDA. "
                "Или вручную: winget install -e --id Nvidia.CUDA или https://developer.nvidia.com/cuda-downloads\n"
                "После установки перезапустите консоль. Если cmake не находит nvcc, задайте: set CUDAToolkit_ROOT=C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v12.x"
            )
        return False, f"cmake configure failed: {out}{hint}"

    print(f"Building whisper.cpp (Release) for {arch}...")
    ok, out = run(
        ["cmake", "--build", "build", "--config", "Release", "-j"],
        cwd=WHISPER_DIR,
        capture=True,
    )
    if not ok:
        return False, (
            f"Build failed: {out}\n"
            "Ensure necessary build tools and SDKs (CUDA Toolkit for NVIDIA, Vulkan SDK for AMD) are installed."
        )
    return True, ""


def copy_to_bin(arch: str = "cpu") -> tuple[bool, str]:
    release = WHISPER_DIR / "build" / "bin" / "Release"
    cli_exe = release / "whisper-cli.exe"
    if not cli_exe.exists():
        return False, f"Build artifact not found: {cli_exe}"

    BIN_DIR.mkdir(parents=True, exist_ok=True)
    dest_name = f"main-{arch}.exe"
    shutil.copy2(cli_exe, BIN_DIR / dest_name)
    for dll in release.glob("*.dll"):
        shutil.copy2(dll, BIN_DIR / dll.name)
    print(f"Copied {dest_name} and DLLs to {BIN_DIR}.")
    return True, ""


def update_config(arch: str = "cpu") -> None:
    config_path = ROOT / "config.yaml"
    if not config_path.exists():
        return
    import yaml

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    key = f"whisper_cpp_path_{arch}"
    data[key] = f"bin/main-{arch}.exe"
    data["module"] = arch
    config_path.write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )
    print(f"Set {key} and module: {arch} in config.yaml.")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--arch", choices=["cpu", "cuda", "amd"], default="cpu")
    args = parser.parse_args()

    ok, msg = check_tools()
    if not ok:
        print(msg)
        return 1
    ok, msg = clone_or_pull()
    if not ok:
        print(msg)
        return 1
    ok, msg = build(args.arch)
    if not ok:
        print(msg)
        return 1
    ok, msg = copy_to_bin(args.arch)
    if not ok:
        print(msg)
        return 1
    update_config(args.arch)
    print(f"whisper.cpp build ({args.arch}) done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
