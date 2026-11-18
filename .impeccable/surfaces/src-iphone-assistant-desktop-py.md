---
version: 1
slug: "src-iphone-assistant-desktop-py"
primary_target: "src/iphone_assistant/desktop.py"
related_targets: []
---

# Desktop surface

MODE: Operate

THESIS: A quiet Windows control desk makes readiness, the current voice turn, and its actual outcome visible at once.

OWN-WORLD: Vietnamese personal iPhone assistant at a Windows desk. Native Segoe UI, daylight off-white surfaces, dark ink, a restrained teal primary action. No decorative media or animation.

STORY: Check connection, press Start, speak once, see the verified result. Stop prevents future work while an already sent request finishes. No per-turn confirmation.

FIRST VIEWPORT: Header; left connection checks, center session and Start/Stop, right latest result. Empty result teaches what appears after the first request. User explicitly selected this layout and Tkinter/code-first.

FORM: 1100x700 resizable Windows window, minimum 980x680 to fit the actual 1280x800 Windows display including chrome/taskbar. Three separated columns, weighted center and result area. Native keyboard focus, text-labelled states, accessible contrast, scrollable result text. One font family; 10/11/14/18/20 pt hierarchy. Spacing 8/12/16/24 px.

FINISH: Seed 5119c415, grounded index 5 (monitoring desk). User-pinned light status/result layout selects this direction. Code-led; no approved image comp. Check ready, missing prerequisite, working, stopping, error and empty states. Native Windows: no HTML/CSS detector or mobile reference applies.
