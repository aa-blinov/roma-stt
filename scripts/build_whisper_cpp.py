"""Clone/pull whisper.cpp, build with CMake, copy exe and DLLs to bin/. For automated install."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WHISPER_DIR = ROOT / "whisper.cpp"
BIN_DIR = ROOT / "bin"
REPO_URL = "https://github.com/ggml-org/whisper.cpp.git"

_VSWHERE = Path("C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe")


def _find_vcvarsall() -> Path | None:
    """Find vcvarsall.bat for the latest VS installation via vswhere."""
    if not _VSWHERE.exists():
        return None
    try:
        r = subprocess.run(
            [str(_VSWHERE), "-latest", "-products", "*", "-property", "installationPath"],
            capture_output=True, text=True, timeout=15,
        )
        install_path = r.stdout.strip()
    except Exception:
        return None
    if not install_path:
        return None
    vcvarsall = Path(install_path) / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
    return vcvarsall if vcvarsall.exists() else None


def _compiler_in_path() -> bool:
    """Return True if cl.exe is already available (Developer Command Prompt)."""
    return shutil.which("cl") is not None


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


def run_msvc(cmd: list[str], cwd: Path) -> tuple[bool, str]:
    """Run cmd with MSVC environment initialized (vcvarsall x64), or plain if already set."""
    if _compiler_in_path():
        return run(cmd, cwd, capture=True)

    vcvarsall = _find_vcvarsall()
    if vcvarsall:
        # Wrap: call vcvarsall to set MSVC env, then run our command
        wrapped = f'call "{vcvarsall}" x64 2>&1 && {subprocess.list2cmdline(cmd)}'
        r = subprocess.run(
            ["cmd", "/c", wrapped],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=600,
        )
        return r.returncode == 0, (r.stdout or "") + (r.stderr or "")

    # No vcvarsall found — try plain (may fail with compiler errors)
    return run(cmd, cwd, capture=True)


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


def _no_compiler_hint() -> str:
    if _compiler_in_path():
        return ""
    vcvarsall = _find_vcvarsall()
    if vcvarsall:
        return ""  # will be set up automatically via run_msvc
    return (
        "\n\nMSVC-компилятор не найден и Visual Studio Build Tools не обнаружены автоматически.\n"
        "Установите через батник пункт 0 (Установка программ) или вручную:\n"
        "  winget install Microsoft.VisualStudio.2022.BuildTools\n"
        "После установки перезапустите консоль и повторите сборку."
    )


def build(arch: str = "cpu") -> tuple[bool, str]:
    build_dir = WHISPER_DIR / f"build-{arch}"
    # Clean stale build dir if previous configure failed (no cmake.check_cache_file = broken cache)
    if build_dir.exists() and not (build_dir / "CMakeFiles" / "cmake.check_cache_file").exists():
        print(f"Removing stale build cache for {arch}...")
        shutil.rmtree(build_dir, ignore_errors=True)

    print(f"Configuring whisper.cpp (cmake) for {arch}...")
    cmake_args = [
        "cmake",
        "-B", f"build-{arch}",
        "-DWHISPER_BUILD_EXAMPLES=ON",
        "-DWHISPER_BUILD_TESTS=OFF",
    ]
    if arch == "cuda":
        cmake_args.append("-DGGML_CUDA=ON")
    elif arch == "amd":
        cmake_args.append("-DGGML_VULKAN=ON")

    ok, out = run_msvc(cmake_args, cwd=WHISPER_DIR)
    if not ok:
        hint = _no_compiler_hint()
        if arch == "cuda" and ("nvcc" in out or "CUDA Toolkit" in out or "CUDAToolkit" in out):
            hint += (
                "\n\nДля CUDA нужен NVIDIA CUDA Toolkit. "
                "Установить: пункт 0 батника → ответить «y» на вопрос про CUDA. "
                "Или: winget install -e --id Nvidia.CUDA\n"
                "После установки перезапустите консоль."
            )
        if arch == "amd" and ("Vulkan" in out or "vulkan" in out):
            hint += (
                "\n\nДля AMD нужен Vulkan SDK (LunarG). "
                "Установить: пункт 0 батника → ответить «y» на вопрос про Vulkan SDK. "
                "Или: winget install KhronosGroup.VulkanSDK\n"
                "После установки перезапустите консоль."
            )
        if "nmake" in out.lower() or "CMAKE_C_COMPILER not set" in out:
            hint += (
                "\n\nЕсли ошибка повторяется — удалите папку whisper.cpp\\build вручную "
                "и запустите сборку снова."
            )
        return False, f"cmake configure failed: {out}{hint}"

    print(f"Building whisper.cpp (Release) for {arch}...")
    ok, out = run_msvc(
        ["cmake", "--build", f"build-{arch}", "--config", "Release", "-j"],
        cwd=WHISPER_DIR,
    )
    if not ok:
        return False, (
            f"Build failed: {out}\n"
            "Убедитесь что нужные SDK установлены (CUDA Toolkit для NVIDIA, Vulkan SDK для AMD)."
        )
    return True, ""


def copy_to_bin(arch: str = "cpu") -> tuple[bool, str]:
    release = WHISPER_DIR / f"build-{arch}" / "bin" / "Release"
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
