import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv(Path(__file__).resolve().parent / ".env")


async def transcribe_audio(audio: bytes) -> str:
    api_key = os.getenv("DEEPGRAM_API_KEY", "").strip()

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Backend chưa được cấu hình Deepgram API key.",
        )

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0)
        ) as client:
            response = await client.post(
                "https://api.deepgram.com/v1/listen",
                params={
                    "model": "nova-3",
                    "language": "multi",
                    "smart_format": "true",
                    "keyterm": "ghi chú",
                },
                headers={
                    "Authorization": f"Token {api_key}",
                    "Content-Type": "application/octet-stream",
                },
                content=audio,
            )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Hết thời gian chờ Deepgram. Hãy thử bản ghi ngắn hơn.",
        ) from None
    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Backend không kết nối được tới Deepgram.",
        ) from None

    if response.status_code in (401, 403):
        raise HTTPException(
            status_code=502,
            detail=(
                "Deepgram từ chối xác thực hoặc quyền truy cập. "
                "Kiểm tra API key và quyền của key ở backend."
            ),
        )

    if response.status_code == 429:
        raise HTTPException(
            status_code=503,
            detail=(
                "Deepgram đang giới hạn request. "
                "Hãy kiểm tra tài khoản và thử lại sau."
            ),
        )

    if response.is_error:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Deepgram trả về HTTP {response.status_code}. "
                "Kiểm tra file audio, cấu hình model và tài khoản."
            ),
        )

    try:
        data = response.json()
        text = data["results"]["channels"][0]["alternatives"][0]["transcript"]

        if not isinstance(text, str):
            raise TypeError("Transcript không phải chuỗi.")

        return text.strip()
    except (ValueError, KeyError, IndexError, TypeError):
        raise HTTPException(
            status_code=502,
            detail="Deepgram trả về dữ liệu không đúng cấu trúc mong đợi.",
        ) from None