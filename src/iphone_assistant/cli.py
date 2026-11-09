import argparse
import json

from .commands import UnsupportedCommand, parse_command


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Phân tích lệnh tiếng Việt; "
            "chưa điều khiển iPhone."
        )
    )

    parser.add_argument(
        "text",
        help="Một câu lệnh, đặt trong dấu nháy",
    )

    args = parser.parse_args()

    try:
        command = parse_command(args.text)
    except UnsupportedCommand as exc:
        parser.error(str(exc))

    print(
        json.dumps(
            {
                "status": "parsed_only",
                "executed": False,
                "command": command.to_dict(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()