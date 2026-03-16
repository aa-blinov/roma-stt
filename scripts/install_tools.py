"""Install required tools (uv, Git, CMake, VS Build Tools) via winget. For bat menu 8."""

import subprocess
import sys


def run(cmd: list[str], timeout: int = 300) -> bool:
    r = subprocess.run(cmd, timeout=timeout)
    return r.returncode == 0


def has_winget() -> bool:
    try:
        r = subprocess.run(
            ["winget", "--version"],
            capture_output=True,
            timeout=10,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def main() -> int:
    print("Установка нужных программ для Roma-STT (через winget)...")
    print()
    if not has_winget():
        print("winget не найден. Установите программы вручную:")
        print("  uv:        https://docs.astral.sh/uv/getting-started/installation/")
        print("  Git:       https://git-scm.com/download/win")
        print("  CMake:     https://cmake.org/download/")
        print("  VS Build:  https://visualstudio.microsoft.com/visual-cpp-build-tools/")
        print()
        print("Или обновите Windows (winget есть в Windows 10/11 из коробки после обновлений).")
        return 1

    tools = [
        ("astral-sh.uv", "uv (Python и зависимости)"),
        ("Git.Git", "Git"),
        ("Kitware.CMake", "CMake"),
    ]
    for pkg, name in tools:
        print(f"Устанавливаю {name}...")
        if not run(["winget", "install", "--id", pkg, "--accept-package-agreements", "--accept-source-agreements"]):
            print(f"  Ошибка установки {name}. Можно поставить вручную, см. README или ИНСТРУКЦИЯ.md")
        else:
            print(f"  {name} установлен.")
        print()

    print("Теперь нужно поставить Visual Studio Build Tools (для сборки программы распознавания речи).")
    print("Это большой пакет, установка может занять несколько минут.")
    yes = input("Установить сейчас? (y/N): ").strip().lower()
    if yes == "y" or yes == "д":
        print("Устанавливаю Visual Studio Build Tools (C++)...")
        if not run(
            [
                "winget",
                "install",
                "--id",
                "Microsoft.VisualStudio.2022.BuildTools",
                "--override",
                "--wait",
                "--passive",
                "--add",
                "Microsoft.VisualStudio.Workload.VCTools",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ],
            timeout=600,
        ):
            print("  Не удалось. Поставьте вручную: https://visualstudio.microsoft.com/visual-cpp-build-tools/")
        else:
            print("  Готово. Возможно, потребуется перезапуск компьютера.")
    else:
        print("Пропущено. Поставьте потом вручную или запустите пункт 0 снова.")
        print("Ссылка: https://visualstudio.microsoft.com/visual-cpp-build-tools/")

    print()
    print("После установки закройте это окно, откройте заново папку и запустите roma-stt.bat.")
    print("Дальше: пункт 1 (Установка), затем 2 (Проверка), затем 3 (Запуск).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
