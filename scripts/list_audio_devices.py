"""List Windows input (recording) devices. Optionally set chosen device in config. For roma-stt.bat."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"


def list_input_devices() -> list[dict]:
    import sounddevice as sd

    devices = sd.query_devices()
    result = []
    for i in range(len(devices)):
        dev = devices[i]
        if not isinstance(dev, dict):
            continue
        if dev.get("max_input_channels", 0) > 0:
            result.append({
                "index": dev["index"],
                "name": dev.get("name", "?"),
                "channels": dev["max_input_channels"],
            })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Список устройств ввода (микрофонов) для выбора в config.")
    parser.add_argument("--set", type=int, metavar="N", help="Записать в config.yaml устройство с номером N")
    parser.add_argument("--default", action="store_true", help="Сбросить на системный микрофон по умолчанию (удалить input_device)")
    args = parser.parse_args()

    try:
        devices = list_input_devices()
    except Exception as e:
        print(f"Ошибка при сканировании устройств: {e}")
        return 1

    if not devices:
        print("Устройства ввода не найдены.")
        return 1

    print("Устройства ввода (микрофоны). Номер — для выбора в меню:")
    for d in devices:
        print(f"  {d['index']}. {d['name']} (каналов: {d['channels']})")
    print("  (в config.yaml ключ input_device можно удалить или поставить null — тогда системный по умолчанию)")

    if args.default:
        import yaml
        config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else {}
        if config is None:
            config = {}
        config.pop("input_device", None)
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(yaml.dump(config, allow_unicode=True, default_flow_style=False), encoding="utf-8")
        print("Сброшено: используется системный микрофон по умолчанию.")
        return 0

    if args.set is not None:
        indices = {d["index"]: d for d in devices}
        if args.set not in indices:
            print(f"Номер {args.set} не найден в списке. Введите номер из списка выше.")
            return 1
        if not CONFIG_PATH.exists():
            import yaml
            config = {}
        else:
            import yaml
            config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
        config["input_device"] = args.set
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        import yaml
        CONFIG_PATH.write_text(yaml.dump(config, allow_unicode=True, default_flow_style=False), encoding="utf-8")
        print(f"В config.yaml записано: input_device: {args.set} ({indices[args.set]['name']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
