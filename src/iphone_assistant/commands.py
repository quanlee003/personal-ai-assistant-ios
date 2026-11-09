from dataclasses import asdict, dataclass, field
import re
import unicodedata


class UnsupportedCommand(ValueError):
    pass


@dataclass(frozen=True)
class Command:
    action: str
    arguments: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


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

    match = re.fullmatch(
        r"(?:vuot|vuot sang|vuot len|vuot xuong) "
        r"(phai|trai|tren|duoi)",
        key,
    )

    directions = {
        "phai": "right",
        "trai": "left",
        "tren": "up",
        "duoi": "down",
    }

    if match:
        return Command(
            "swipe",
            {"direction": directions[match.group(1)]},
        )

    if key in {"vuot len", "vuot xuong"}:
        return Command(
            "swipe",
            {
                "direction": (
                    "up" if key.endswith("len") else "down"
                )
            },
        )

    if key in {"tim", "tim kiem", "roi tim"}:
        return Command("submit")

    tokens = raw.split()
    first = normalize(tokens[0])

    action = {
        "mo": "open_app",
        "bam": "select_target",
        "chon": "select_target",
        "go": "enter_text",
        "nhap": "enter_text",
    }.get(first)

    if action and len(tokens) > 1:
        value = raw.split(maxsplit=1)[1]

        if any(
            separator in value
            for separator in [";", "\n"]
        ):
            raise UnsupportedCommand(
                "Hiện mỗi yêu cầu chỉ nhận một lệnh."
            )

        if (
            action != "enter_text"
            and re.search(
                r"\b(?:roi|sau do)\b",
                normalize(value),
            )
        ):
            raise UnsupportedCommand(
                "Chuỗi nhiều bước cần planner, "
                "chưa được triển khai."
            )

        argument = {
            "open_app": "app_name",
            "select_target": "target",
            "enter_text": "text",
        }[action]

        return Command(action, {argument: value})

    raise UnsupportedCommand(
        "Chưa hỗ trợ câu lệnh này. "
        "Không có thao tác nào được thực hiện."
    )