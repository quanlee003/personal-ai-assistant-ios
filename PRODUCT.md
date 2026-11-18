# Product

<!-- impeccable:product-schema 1 -->

## Platform

Windows desktop (native Tkinter; the skill's mobile/web taxonomy does not cover this target).

## Stack

User selected Python/Tkinter on 18/11/2026. Reuse the existing Python WDA workflow.

## Users and purpose

The repository owner uses a Windows PC and USB iPhone, speaks Vietnamese, and wants
to operate supported phone tasks without terminals or confirmation on every turn.
This first desktop surface is for testing and simplifying that workflow before productization.

## Capabilities and constraints

Only open Settings and its Battery page. Deepgram handles speech; AI Gateway
handles intent and screenshot verification. No general planner or settings changes.
Existing WDA/tunnel/provisioning remains a prerequisite. The UI must not claim to
install or repair those automatically. No background listening before Start.
Stop must prevent subsequent steps and explain that requests already sent cannot be undone.

## Current scope

Connection/microphone/configuration checks, Start/Stop, progress and turn results.
Retain CLI compatibility, typed structured results and local evidence. Keys stay in
the existing .env; screenshots/logs are not uploaded to new services.

## Principles

- Show readiness and real state, never synthetic success.
- One obvious action; technical details stay secondary.
- Keep cancellation and uncertain outcomes visible.
- Separate the UI from device/cloud execution.

## Open decisions

Installer, public distribution, account management and a final product name remain undecided.
