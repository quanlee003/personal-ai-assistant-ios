# Personal AI Assistant for iPhone

A Vietnamese voice-controlled iPhone assistant, built independently with architectural inspiration from WhisperTest. No Apple Intelligence dependency.

## Target deployment

- Windows host connected to an iPhone.
- Apple Voice Control as the initial action execution mechanism.
- Vietnamese speech input, structured commands, screen observation, and an execution loop.
- This is not currently a standalone iPhone app or an App Store distribution design.

## Status

Speech (Deepgram), vision (AI Gateway), numbered Voice Control/TTS and screenshot verification modules are implemented. On 18 November 2026, WDA directly opened Settings on the connected iOS 27 iPhone and captured the resulting screen. No TTS was used. This validates that single action, not arbitrary app control.

Windows setup, evidence, limitations and commands: [Direct control on Windows](docs/direct-windows.md). The separate `iphone_assistant.direct_cli` supports Settings only and defaults to preview. Debug execution requires confirmation; explicit `--auto` enables the bounded voice workflow without prompts. Deepgram and AI Gateway remain the existing providers.

Automatic Settings-only voice mode: `python -m iphone_assistant.direct_cli --auto --max-turns 2`. This explicitly enables recording, Deepgram transcription, AI Gateway intent/screenshot verification and WDA execution without per-turn prompts. Silence ends each recording; say “dừng” while listening or press Ctrl+C to stop. A physical auto trial on 18 November 2026 recorded `verified_match`; two other trials stopped with `SpeechInputError` before attempting device actions. Audio robustness still needs improvement.

Without `--auto`, debug mode retains confirmations. With `--listen`, review the recognized text before processing: Enter keeps it, typing a full sentence replaces it, and `/cancel` exits. Sending to AI, executing and sharing the verification screenshot require their own confirmations in debug mode.

See docs/architecture.md.

Direct sessions: run `python -m iphone_assistant.direct_cli --session --listen --ai --execute --verify` in the project environment. Each turn requires fresh input and confirmation; `/quit` exits at the turn prompt. Local results are saved under `runtime/direct-results/` (Git-ignored). Sessions stop on cancellation, errors or uncertain verification and default to at most 10 turns.

## Inspiration

WhisperTest: https://github.com/iOSWhisperTest/whispertest

No WhisperTest source code is included in this initial commit. Any future reuse must preserve applicable licenses and notices.
