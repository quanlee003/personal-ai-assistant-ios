from dataclasses import dataclass, field
import re
import unicodedata


class UnsupportedCommand(ValueError):
    pass


@dataclass(frozen=True)
class Command:
    action: str
    arguments: dict[str, str] = field(default_factory=dict)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.casefold())
    text = "".join(
        c
        for c in text
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(text.replace("đ", "d").split())


def parse_command(text: str) -> Command:
    raw = text.strip()
    key = normalize(raw)

    if not key:
        raise UnsupportedCommand("Lệnh trống.")
    if key in {"dung", "dung lai", "huy", "stop"}:
        return Command("stop")

    tokens = raw.split(maxsplit=1)
    if len(tokens) == 2 and normalize(tokens[0]) == 'mo':
        value = tokens[1]

        if any(
            separator in value
            for separator in [";", "\n"]
        ):
            raise UnsupportedCommand(
                "Hiện mỗi yêu cầu chỉ nhận một lệnh."
            )

        if re.search(r"\b(?:roi|sau do)\b", normalize(value)):
            raise UnsupportedCommand(
                "Chuỗi nhiều bước cần planner, "
                "chưa được triển khai."
            )

        return Command('open_app', {'app_name': value})

    raise UnsupportedCommand(
        "Chưa hỗ trợ câu lệnh này. "
        "Không có thao tác nào được thực hiện."
    )
