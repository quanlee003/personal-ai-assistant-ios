# Personal AI Assistant for iPhone

A Vietnamese voice-controlled iPhone assistant, built independently with architectural inspiration from WhisperTest. No Apple Intelligence dependency.

## Target deployment

- Windows host connected to an iPhone.
- Apple Voice Control as the initial action execution mechanism.
- Vietnamese speech input, structured commands, screen observation, and an execution loop.
- This is not currently a standalone iPhone app or an App Store distribution design.

## Status

Architecture initialization only. No working device control, speech recognition, or AI integration has been implemented yet. Device and OS compatibility are not guaranteed.

Development proceeds directly toward the application; there is no separate proof-of-concept phase. Normal debugging and integration checks remain part of implementation.

See docs/architecture.md.

## Inspiration

WhisperTest: https://github.com/iOSWhisperTest/whispertest

No WhisperTest source code is included in this initial commit. Any future reuse must preserve applicable licenses and notices.


docs/architecture.md:
# Architecture

## Proposed modules

- speech: transcribe Vietnamese speech through a replaceable provider; provider not selected yet.
- commands: represent actions such as swipe, open_app, select_target, enter_text, submit, and stop.
- planner: map direct requests to commands; use a replaceable AI provider for ambiguous or multi-step goals.
- observation: retrieve screenshots and, where available, accessibility data from the connected iPhone.
- execution: translate structured commands into the initial Voice Control/TTS mechanism and supported device operations.
- orchestrator: coordinate observation, action, result checking, cancellation, and bounded retries.
- interface: host-side microphone controls, task status, and stop control; interface technology not selected yet.

## Example task

Vietnamese request: Open YouTube and search for a phrase.

1. Interpret the requested app and exact search phrase.
2. Request app opening through the execution adapter.
3. Observe the current screen.
4. Locate and select search.
5. Enter the exact phrase.
6. Submit and observe the result.

These are target behaviors, not implemented capabilities. Text entry must preserve Vietnamese characters; the concrete mechanism remains an implementation decision rather than an assumption that English TTS can dictate Vietnamese correctly.

## Execution contract

Execution adapters must report success, failure, or unknown. Emitting a spoken command alone does not prove that the phone performed it. Unsupported operations must return explicit errors, not simulated success.

## Safety and privacy

- Provide stop/cancel and limits on action count and retries.
- Require explicit confirmation before sending communications, purchasing, deleting data, or changing account/security settings.
- Do not commit API keys, device pairing records, screenshots, transcripts, or recordings.
- Avoid retaining screen and microphone data by default.
- Treat screen content as untrusted data, not as instructions that override the user.

## Constraints

The initial design assumes a Windows host, an iPhone connection, and enabled Voice Control. Developer Mode or other device-service setup may be required by the selected implementation. Compatibility with the user's actual device and OS remains unverified. Reimplementing the architecture does not remove iOS platform restrictions.
