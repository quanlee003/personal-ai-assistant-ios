# Development

Requires Python 3.11 or newer. From the repository root:

```powershell
py -m venv .venv

.\.venv\Scripts\python.exe -m pip install -e .

.\.venv\Scripts\iphone-assistant.exe "vuốt sang phải"

.\.venv\Scripts\iphone-assistant.exe "mở YouTube"

.\.venv\Scripts\iphone-assistant.exe "bấm tìm kiếm"

.\.venv\Scripts\iphone-assistant.exe "gõ cách nấu phở"
```

This increment parses one textual command into structured JSON.

It does not capture microphone audio, connect to a phone,
generate Voice Control audio, or execute actions.

`executed` is always false.

Multi-step planning and speech/device adapters remain to be
implemented. Do not interpret successful parsing as successful
device control.

The parser normalizes accents only for command matching;
payloads retain their original spelling and Vietnamese accents.

It is a limited rule-based parser, not a general Vietnamese
language model.