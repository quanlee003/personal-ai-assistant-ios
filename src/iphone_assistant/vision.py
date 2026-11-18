import base64
import os
import struct
from pathlib import Path
from typing import Literal

from openai import APIError, OpenAI
from pydantic import BaseModel, ConfigDict, ValidationError

class VisionError(RuntimeError):
    pass


def validate_png(path: Path) -> tuple[int, int]:
    """Reject missing, truncated or invalid PNG headers before uploading."""
    with path.open('rb') as image:
        header = image.read(24)
    if (len(header) != 24 or header[:8] != b'\x89PNG\r\n\x1a\n'
            or header[12:16] != b'IHDR'):
        raise VisionError('File ảnh không có header PNG hợp lệ.')
    width, height = struct.unpack('>II', header[16:24])
    if width == 0 or height == 0:
        raise VisionError('Ảnh có kích thước không hợp lệ.')
    return width, height


class ScreenObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal[
        "found",
        "clarify",
        "not_found",
    ]

    screen_summary: str
    target_description: str
    target_location: str
    message: str


def validate_observation(
    result: ScreenObservation,
) -> ScreenObservation:
    if not result.screen_summary.strip():
        raise VisionError("Model không mô tả màn hình.")

    if not result.message.strip():
        raise VisionError("Model không giải thích kết quả.")

    if result.status == "found":
        if (
            not result.target_description.strip()
            or not result.target_location.strip()
        ):
            raise VisionError(
                "Model báo tìm thấy nhưng thiếu mô tả hoặc vị trí."
            )

    elif (
        result.target_description != ""
        or result.target_location != ""
    ):
        raise VisionError(
            "Model trả kết quả không nhất quán."
        )

    return result


def observe_screen(
    image_path: Path,
    request: str,
    *,
    system_prompt: str,
) -> ScreenObservation:
    if not request.strip():
        raise VisionError("Yêu cầu quan sát đang trống.")

    api_key = os.environ.get(
        "AI_GATEWAY_API_KEY", ""
    ).strip()

    model = os.environ.get(
        "AI_GATEWAY_VISION_MODEL",
        "google/gemini-2.5-flash",
    ).strip()

    if not api_key:
        raise VisionError(
            "Chưa đặt AI_GATEWAY_API_KEY trong .env."
        )

    if not model:
        raise VisionError(
            "AI_GATEWAY_VISION_MODEL đang trống."
        )

    image_path = Path(image_path)
    width, height = validate_png(image_path)

    image_data = base64.b64encode(
        image_path.read_bytes()
    ).decode("ascii")

    try:
        with OpenAI(
            api_key=api_key,
            base_url="https://ai-gateway.vercel.sh/v1",
            timeout=60.0,
            max_retries=0,
        ) as client:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    f"Kích thước ảnh: "
                                    f"{width} x {height} pixel.\n"
                                    f"Yêu cầu: {request}"
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": (
                                        "data:image/png;base64,"
                                        f"{image_data}"
                                    ),
                                },
                            },
                        ],
                    },
                ],
                max_tokens=1200,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "screen_observation",
                        "schema": (
                            ScreenObservation.model_json_schema()
                        ),
                    },
                },
            )

    except APIError as exc:
        status = getattr(exc, "status_code", None)
        detail = (
            f" HTTP {status}."
            if status is not None
            else ""
        )

        raise VisionError(
            "Không phân tích được ảnh qua AI Gateway."
            f"{detail} Kiểm tra key, credit, model "
            "và kết nối mạng. Không thực hiện thao tác."
        ) from exc

    if not response.choices:
        raise VisionError("Gateway không trả kết quả.")

    choice = response.choices[0]

    if choice.finish_reason != "stop":
        raise VisionError(
            "Phản hồi chưa hoàn chỉnh hoặc bị chặn."
        )

    if choice.message.refusal:
        raise VisionError(
            "Model từ chối phân tích yêu cầu."
        )

    content = choice.message.content

    if not content:
        raise VisionError("Model trả nội dung trống.")

    try:
        result = ScreenObservation.model_validate_json(
            content
        )
    except ValidationError as exc:
        raise VisionError(
            "Kết quả quan sát không đúng schema."
        ) from exc

    return validate_observation(result)
