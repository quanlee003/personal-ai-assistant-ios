import argparse
import struct
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_DEVICE_PYTHON = (
    PROJECT_ROOT
    / ".venv-device-x64"
    / "Scripts"
    / "python.exe"
)

DEFAULT_CAPTURE_DIR = PROJECT_ROOT / "captures"

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class DeviceError(RuntimeError):
    pass


def validate_png(path: Path) -> tuple[int, int]:
    if not path.is_file():
        raise DeviceError(
            "Lệnh kết thúc nhưng không tạo được file ảnh."
        )

    with path.open("rb") as image:
        header = image.read(24)

    if (
        len(header) != 24
        or header[:8] != PNG_SIGNATURE
        or header[12:16] != b"IHDR"
    ):
        raise DeviceError(
            "File nhận được không có header PNG hợp lệ."
        )

    width, height = struct.unpack(">II", header[16:24])

    if width == 0 or height == 0:
        raise DeviceError(
            "Ảnh nhận được có kích thước không hợp lệ."
        )

    return width, height


def capture_screen(
    output_dir: Path = DEFAULT_CAPTURE_DIR,
    device_python: Path = DEFAULT_DEVICE_PYTHON,
    timeout: float = 90.0,
) -> Path:
    device_python = Path(device_python).resolve()
    output_dir = Path(output_dir).resolve()

    if not device_python.is_file():
        raise DeviceError(
            "Không tìm thấy Python của môi trường thiết bị:\n"
            f"{device_python}"
        )

    if timeout <= 0:
        raise DeviceError("Timeout phải lớn hơn 0.")

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    identifier = uuid4().hex[:8]

    output_path = output_dir / (
        f"iphone-{timestamp}-{identifier}.png"
    )

    command = [
        str(device_python),
        "-m",
        "pymobiledevice3",
        "developer",
        "dvt",
        "screenshot",
        str(output_path),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )

        if result.returncode != 0:
            detail = "\n".join(
                part.strip()
                for part in (result.stdout, result.stderr)
                if part.strip()
            )

            raise DeviceError(
                "Chụp màn hình thất bại "
                f"(exit code {result.returncode}).\n"
                f"{detail or 'Không có thông báo từ công cụ.'}"
            )

        validate_png(output_path)
        return output_path

    except subprocess.TimeoutExpired as exc:
        output_path.unlink(missing_ok=True)

        raise DeviceError(
            f"Chụp màn hình quá thời gian {timeout:g} giây. "
            "Kiểm tra kết nối USB và trạng thái iPhone."
        ) from exc

    except (DeviceError, OSError):
        output_path.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chụp màn hình iPhone qua pymobiledevice3."
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_CAPTURE_DIR,
    )

    parser.add_argument(
        "--device-python",
        type=Path,
        default=DEFAULT_DEVICE_PYTHON,
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=90.0,
    )

    args = parser.parse_args()

    try:
        print("Đang chụp màn hình iPhone...", flush=True)

        image_path = capture_screen(
            output_dir=args.output_dir,
            device_python=args.device_python,
            timeout=args.timeout,
        )

        width, height = validate_png(image_path)

    except (DeviceError, OSError) as exc:
        parser.exit(1, f"Lỗi: {exc}\n")

    print(f"Đã lưu ảnh: {image_path}")
    print(f"Kích thước: {width} x {height}")
    print("Chưa phân tích ảnh hoặc thực hiện thao tác.")


if __name__ == "__main__":
    main()