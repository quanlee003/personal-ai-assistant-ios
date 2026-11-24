import os
from dataclasses import dataclass
from typing import Literal

from openai import APIError, OpenAI
from pydantic import BaseModel, ConfigDict, ValidationError

from .commands import Command


class IntentError(RuntimeError):
    pass


class ModelIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal[
        "action",
        "clarify",
        "unsupported",
    ]

    action: Literal[
        "none",
        "open_app",
        "select_target",
        "select_tab",
        "go_back",
        "stop",
    ]

    # Keep the response shape used by the direct prompt; no directional actions.
    direction: Literal["none"]

    value: str
    message: str


@dataclass(frozen=True)
class IntentResult:
    decision: str
    command: Command | None
    message: str


def validate_intent(item: ModelIntent) -> IntentResult:
    if item.decision != "action":
        if (
            item.action != "none"
            or item.direction != "none"
            or item.value != ""
            or not item.message.strip()
        ):
            raise IntentError(
                "Model trả kết quả không nhất quán."
            )

        return IntentResult(
            decision=item.decision,
            command=None,
            message=item.message.strip(),
        )

    if item.message != "":
        raise IntentError(
            "Kết quả hành động có trường message không hợp lệ."
        )

    if item.action in {"open_app", "select_target", "select_tab"}:
        if (
            item.direction != "none"
            or not item.value.strip()
        ):
            raise IntentError(
                "Model trả hành động thiếu hoặc sai tham số."
            )

        argument_name = {
            "open_app": "app_name",
            "select_target": "target",
            "select_tab": "target",
        }[item.action]

        command = Command(
            item.action,
            {argument_name: item.value},
        )

    elif item.action in {"stop", "go_back"}:
        if item.direction != "none" or item.value != "":
            raise IntentError(
                "Model trả hành động có tham số thừa."
            )

        command = Command(item.action)

    else:
        raise IntentError(
            "Model không trả về hành động hợp lệ."
        )

    return IntentResult(
        decision="action",
        command=command,
        message="",
    )


def understand_intent(transcript: str, *, system_prompt: str) -> IntentResult:
    if not transcript.strip():
        raise IntentError("Transcript trống.")

    api_key = os.environ.get(
        "AI_GATEWAY_API_KEY", ""
    ).strip()

    model = os.environ.get(
        "AI_GATEWAY_MODEL",
        "google/gemini-2.5-flash-lite",
    ).strip()

    if not api_key:
        raise IntentError(
            "Chưa đặt AI_GATEWAY_API_KEY trong .env."
        )

    if not model:
        raise IntentError("AI_GATEWAY_MODEL đang trống.")

    try:
        with OpenAI(
            api_key=api_key,
            base_url="https://ai-gateway.vercel.sh/v1",
            timeout=30.0,
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
                        "content": transcript,
                    },
                ],
                max_tokens=500,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "iphone_intent",
                        "schema": ModelIntent.model_json_schema(),
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

        raise IntentError(
            "Không gọi được Vercel AI Gateway."
            f"{detail} Kiểm tra key, credit, model "
            "và kết nối mạng. Không phát lệnh."
        ) from exc

    if not response.choices:
        raise IntentError("Gateway không trả kết quả.")

    choice = response.choices[0]

    if choice.finish_reason != "stop":
        raise IntentError(
            "Phản hồi model chưa hoàn chỉnh hoặc bị chặn. "
            "Không phát lệnh."
        )

    if choice.message.refusal:
        raise IntentError(
            "Model từ chối xử lý yêu cầu. Không phát lệnh."
        )

    content = choice.message.content

    if not content:
        raise IntentError("Model trả nội dung trống.")

    try:
        item = ModelIntent.model_validate_json(content)
    except ValidationError as exc:
        raise IntentError(
            "Đầu ra model không đúng schema. "
            "Không phát lệnh."
        ) from exc

    return validate_intent(item)
