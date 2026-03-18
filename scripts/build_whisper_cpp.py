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


def _find_vulkan_sdk() -> str | None:
    """Return Vulkan SDK root (the one with Lib/vulkan-1.lib), or None."""
    # 1. VULKAN_SDK env var (set by LunarG installer)
    sdk = os.environ.get("VULKAN_SDK", "").strip()
    if sdk and (Path(sdk) / "Lib" / "vulkan-1.lib").exists():
        return sdk

    # 2. Scan C:/VulkanSDK/<version>/ — installed but env var not in this shell
    for base in [Path("C:/VulkanSDK"), Path("C:/vulkansdk")]:
        if not base.exists():
            continue
        candidates = sorted(
            (p for p in base.iterdir() if p.is_dir() and (p / "Lib" / "vulkan-1.lib").exists()),
            key=lambda p: p.name,
            reverse=True,
        )
        if candidates:
            return str(candidates[0])
    return None

_VS_GEN_MAP = {
    "17": "Visual Studio 17 2022",
    "16": "Visual Studio 16 2019",
    "15": "Visual Studio 15 2017",
}


def _find_vs_generator() -> str | None:
    """Detect cmake Visual Studio generator for installed VS IDE (not Build Tools).

    The VS generator only works with VS IDE installations, NOT with Build Tools only.
    Tries with C++ component requirement first, then any VS IDE install.
    """
    if not _VSWHERE.exists():
        return None
    for extra in (
        ["-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
         "-products", "Microsoft.VisualStudio.Product.Enterprise",
                      "Microsoft.VisualStudio.Product.Professional",
                      "Microsoft.VisualStudio.Product.Community"],
        ["-products", "Microsoft.VisualStudio.Product.Enterprise",
                      "Microsoft.VisualStudio.Product.Professional",
                      "Microsoft.VisualStudio.Product.Community"],
    ):
        try:
            r = subprocess.run(
                [str(_VSWHERE), "-latest", *extra, "-property", "installationVersion"],
                capture_output=True, text=True, timeout=15,
            )
            version = r.stdout.strip()
            if version:
                major = version.split(".")[0]
                gen = _VS_GEN_MAP.get(major)
                if gen:
                    return gen
        except Exception:
            pass
    return None


def _find_vcvarsall() -> Path | None:
    """Find vcvarsall.bat for VS IDE or Build Tools.

    First tries vswhere, then falls back to searching well-known install paths.
    This handles cases where vswhere is unavailable or returns nothing.
    """
    # 1. Try vswhere
    if _VSWHERE.exists():
        try:
            r = subprocess.run(
                [str(_VSWHERE), "-latest", "-products", "*", "-property", "installationPath"],
                capture_output=True, text=True, timeout=15,
            )
            install_path = r.stdout.strip()
            if install_path:
                vc = Path(install_path) / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
                if vc.exists():
                    return vc
                # vswhere found an install but vcvarsall.bat missing — store for diagnostic
                _find_vcvarsall._vswhere_path = install_path  # type: ignore[attr-defined]
        except Exception:
            pass
    else:
        _find_vcvarsall._vswhere_path = "<vswhere.exe not found>"  # type: ignore[attr-defined]

    # 2. Fallback: scan well-known install locations
    for base in [
        Path("C:/Program Files (x86)/Microsoft Visual Studio"),
        Path("C:/Program Files/Microsoft Visual Studio"),
    ]:
        if not base.exists():
            continue
        for year in ["2022", "2019", "2017"]:
            for edition in ["BuildTools", "Enterprise", "Professional", "Community"]:
                vc = base / year / edition / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
                if vc.exists():
                    return vc
    return None


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


def _run_vcvarsall(cmd: list[str], cwd: Path) -> tuple[bool, str]:
    """Run cmd after calling vcvarsall x64 (for Build Tools without VS IDE)."""
    vcvarsall = _find_vcvarsall()
    if not vcvarsall:
        return False, "vcvarsall.bat not found — install Visual Studio Build Tools"
    wrapped = f'call "{vcvarsall}" x64 2>&1 && {subprocess.list2cmdline(cmd)}'
    r = subprocess.run(["cmd", "/c", wrapped], cwd=cwd,
                       capture_output=True, text=True, timeout=600)
    return r.returncode == 0, (r.stdout or "") + (r.stderr or "")


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
    if _find_vcvarsall():
        return ""

    # Check if Build Tools IS installed but without the C++ workload (vcvarsall absent)
    vswhere_path = getattr(_find_vcvarsall, "_vswhere_path", None)
    if vswhere_path and not str(vswhere_path).startswith("<"):
        vs_installer = Path("C:/Program Files (x86)/Microsoft Visual Studio/Installer/vs_installer.exe")
        cmd = (
            f'"{vs_installer}" modify'
            f' --installPath "{vswhere_path}"'
            " --add Microsoft.VisualStudio.Workload.VCTools"
            " --includeRecommended --passive --norestart"
        )
        return (
            "\n\nBuild Tools установлен, но компонент C++ (vcvarsall.bat) отсутствует.\n"
            "Добавьте компонент одним из способов:\n\n"
            "  1. Через меню Пуск → «Visual Studio Installer»\n"
            "     → «Изменить» → «Средства сборки C++» → «Изменить»\n\n"
            "  2. Командой (запустить cmd от имени администратора):\n"
            f"     {cmd}\n\n"
            "После установки перезапустите консоль и повторите сборку."
        )

    return (
        "\n\nMSVC-компилятор не найден и Visual Studio Build Tools не обнаружены автоматически.\n"
        "Установите через меню пункт 1 (Установка) или вручную:\n"
        "  winget install Microsoft.VisualStudio.2022.BuildTools\n"
        "После установки перезапустите консоль и повторите сборку."
    )


def build(arch: str = "cpu") -> tuple[bool, str]:
    build_dir = WHISPER_DIR / f"build-{arch}"
    # Clean stale build dir if previous configure failed
    if build_dir.exists() and not (build_dir / "CMakeFiles" / "cmake.check_cache_file").exists():
        print(f"Removing stale build cache for {arch}...")
        shutil.rmtree(build_dir, ignore_errors=True)

    print(f"Configuring whisper.cpp (cmake) for {arch}...")
    base_cmake = [
        "cmake",
        "-B", f"build-{arch}",
        "-DWHISPER_BUILD_EXAMPLES=ON",
        "-DWHISPER_BUILD_TESTS=OFF",
    ]
    if arch == "cuda":
        base_cmake.append("-DGGML_CUDA=ON")
    elif arch == "amd":
        base_cmake.append("-DGGML_VULKAN=ON")
        # Pass Vulkan SDK path explicitly so cmake finds it even if VULKAN_SDK env
        # var is not set in the current shell (common after fresh SDK install)
        vulkan_sdk = _find_vulkan_sdk()
        if vulkan_sdk:
            print(f"  [amd] Vulkan SDK found at: {vulkan_sdk}")
            # cmake FindVulkan looks for Vulkan_ROOT (cmake var) or VULKAN_SDK (env var)
            # -DVULKAN_SDK is NOT the right variable name; use -DVulkan_ROOT
            base_cmake.append(f"-DVulkan_ROOT={vulkan_sdk}")
        else:
            print("  [amd] Vulkan SDK NOT found — install via menu item 1 or: winget install KhronosGroup.VulkanSDK")

    # Build strategy (tried in order):
    # A. cl.exe in PATH (Developer Command Prompt) → Ninja, single-config
    # B. VS IDE installed → VS generator, multi-config (cmake finds via registry)
    # C. Build Tools only → vcvarsall.bat + Ninja, single-config
    # D. Plain run (last resort)
    via_vcvarsall = False
    multi_config = False

    if _compiler_in_path():
        # A: already in Developer Prompt — Ninja is fastest
        print("  [build] Strategy A: cl.exe in PATH, using Ninja")
        ok, out = run(base_cmake + ["-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release"],
                      cwd=WHISPER_DIR, capture=True)
        if not ok:
            ok, out = run(base_cmake, cwd=WHISPER_DIR, capture=True)
            multi_config = ok
    else:
        ok, out = False, ""
        vs_gen = _find_vs_generator()
        if vs_gen:
            # B: VS IDE — multi-config generator, no vcvarsall needed
            print(f"  [build] Strategy B: VS IDE generator ({vs_gen})")
            ok, out = run(base_cmake + ["-G", vs_gen, "-A", "x64"],
                          cwd=WHISPER_DIR, capture=True)
            if ok:
                multi_config = True

        if not ok:
            # C: Build Tools only — vcvarsall.bat + Ninja (Ninja ships with Build Tools)
            vcvarsall_path = _find_vcvarsall()
            if vcvarsall_path:
                print(f"  [build] Strategy C: vcvarsall.bat found at {vcvarsall_path}, using Ninja")
                ok, out = _run_vcvarsall(
                    base_cmake + ["-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release"],
                    cwd=WHISPER_DIR,
                )
                if ok:
                    via_vcvarsall = True
            else:
                print("  [build] Strategy C: vcvarsall.bat NOT found — diagnostic:")
                vswhere_path = getattr(_find_vcvarsall, "_vswhere_path", "<not set>")
                print(f"    vswhere installationPath: {vswhere_path!r}")
                for base_p in [
                    Path("C:/Program Files (x86)/Microsoft Visual Studio"),
                    Path("C:/Program Files/Microsoft Visual Studio"),
                ]:
                    print(f"    {base_p} exists={base_p.exists()}")
                    if base_p.exists():
                        try:
                            top = sorted(p.name for p in base_p.iterdir() if p.is_dir())
                            print(f"      subdirs: {top}")
                            for sub in base_p.iterdir():
                                if sub.is_dir():
                                    try:
                                        children = sorted(p.name for p in sub.iterdir() if p.is_dir())
                                        print(f"      {sub.name}/: {children}")
                                        for child in sub.iterdir():
                                            if child.is_dir():
                                                vc = child / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
                                                print(f"        {child.name}/VC/Auxiliary/Build/vcvarsall.bat exists={vc.exists()}")
                                    except Exception:
                                        pass
                        except Exception as e:
                            print(f"      cannot list: {e}")

        if not ok:
            # D: plain run — last resort
            print("  [build] Strategy D: plain cmake (no MSVC env)")
            ok, out = run(base_cmake, cwd=WHISPER_DIR, capture=True)
            multi_config = ok

    if not ok:
        hint = _no_compiler_hint()
        if arch == "cuda" and ("nvcc" in out or "CUDA Toolkit" in out or "CUDAToolkit" in out):
            hint += (
                "\n\nДля CUDA нужен NVIDIA CUDA Toolkit. "
                "Установить: меню пункт 1 (Установка) → ответить «y» на вопрос про CUDA. "
                "Или: winget install -e --id Nvidia.CUDA\n"
                "После установки перезапустите консоль."
            )
        if arch == "amd" and ("vulkan" in out.lower()):
            hint += (
                "\n\nДля AMD нужен Vulkan SDK (LunarG). "
                "Установить: меню пункт 1 (Установка) → ответить «y» на вопрос про Vulkan SDK. "
                "Или: winget install KhronosGroup.VulkanSDK\n"
                "После установки перезапустите консоль."
            )
        return False, f"cmake configure failed: {out}{hint}"

    print(f"Building whisper.cpp (Release) for {arch}...")
    build_cmd = ["cmake", "--build", f"build-{arch}", "-j"]
    if multi_config:
        build_cmd += ["--config", "Release"]

    if via_vcvarsall:
        ok, out = _run_vcvarsall(build_cmd, cwd=WHISPER_DIR)
    else:
        ok, out = run(build_cmd, cwd=WHISPER_DIR, capture=True)

    if not ok:
        return False, (
            f"Build failed: {out}\n"
            "Убедитесь что нужные SDK установлены (CUDA Toolkit для NVIDIA, Vulkan SDK для AMD)."
        )
    return True, ""


def copy_to_bin(arch: str = "cpu") -> tuple[bool, str]:
    build_dir = WHISPER_DIR / f"build-{arch}"
    # VS generator (multi-config) puts exe in bin/Release/; Ninja puts it in bin/
    for subdir in [Path("bin") / "Release", Path("bin")]:
        cli_exe = build_dir / subdir / "whisper-cli.exe"
        if cli_exe.exists():
            break
    else:
        return False, (
            f"Build artifact not found in {build_dir}/bin/[Release/]\n"
            "Убедитесь что сборка прошла успешно."
        )

    BIN_DIR.mkdir(parents=True, exist_ok=True)
    dest_name = f"main-{arch}.exe"
    shutil.copy2(cli_exe, BIN_DIR / dest_name)
    for dll in cli_exe.parent.glob("*.dll"):
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
