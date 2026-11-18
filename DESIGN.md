---
name: iPhone Assistant Desktop
description: A quiet native Windows control desk for Vietnamese voice sessions.
colors:
  canvas: "#F3F5F6"
  ink: "#192D38"
  muted: "#536570"
  primary: "#086A63"
  warning: "#945218"
  error: "#A52B32"
  surface: "white"
  control-active: "#E3E9EC"
  control-disabled-text: "#697780"
  primary-disabled: "#DCE3E5"
  primary-active: "#07574F"
  primary-disabled-text: "#56646D"
  selection: "#CEEAE5"
typography:
  display:
    fontFamily: Segoe UI
    fontSize: 20pt
    fontWeight: 700
  headline:
    fontFamily: Segoe UI
    fontSize: 18pt
    fontWeight: 700
  title:
    fontFamily: Segoe UI
    fontSize: 14pt
    fontWeight: 700
  result-title:
    fontFamily: Segoe UI
    fontSize: 12pt
    fontWeight: 700
  body:
    fontFamily: Segoe UI
    fontSize: 11pt
    fontWeight: 400
  action:
    fontFamily: Segoe UI
    fontSize: 11pt
    fontWeight: 700
  label:
    fontFamily: Segoe UI
    fontSize: 10pt
    fontWeight: 400
spacing:
  compact: 6px
  small: 8px
  medium: 12px
  panel: 16px
  large: 24px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    typography: "{typography.action}"
    padding: 9px 12px
  button-primary-active:
    backgroundColor: "{colors.primary-active}"
    textColor: "{colors.surface}"
  button-primary-disabled:
    backgroundColor: "{colors.primary-disabled}"
    textColor: "{colors.primary-disabled-text}"
  button-secondary:
    typography: "{typography.label}"
    padding: 9px 12px
  button-secondary-active:
    backgroundColor: "{colors.control-active}"
  button-secondary-disabled:
    textColor: "{colors.control-disabled-text}"
  panel:
    backgroundColor: "{colors.surface}"
    padding: 16px
  turn-selector:
    typography: "{typography.label}"
    padding: 6px
  result-text:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    padding: 4px 0px
---

# Design System: iPhone Assistant Desktop

## Overview

**Creative North Star: "A Quiet Windows Control Desk"**

The implemented world is a restrained, daylight desktop workspace: off-white surroundings, white work areas, dark ink and a single teal action accent. Vietnamese text carries state and guidance; decoration does not compete with the work.

This is a native Python/Tkinter system using the `clam` ttk theme. Tokens above are extracted from `src/iphone_assistant/desktop.py`; theme-owned details remain theme-owned. The chosen light readiness/session/results composition is recorded in `.impeccable/surfaces/src-iphone-assistant-desktop-py.md`, rather than imposed on every future screen.

Key characteristics:

- One Segoe UI family and a clear size/weight hierarchy.
- Flat tonal separation and generous panel interiors.
- Text-labelled states, visible cancellation and scrollable results.

## Colors

### Primary

Restrained teal (`primary`) identifies Start, listening, ready checks and verified matches. Its active and disabled variants are explicit tokens. Pale teal (`selection`) marks selected result text.

### Neutral

Cool off-white (`canvas`) surrounds white (`surface`) panels. Dark ink (`ink`) carries main content; slate (`muted`) carries support text. Secondary controls use the theme at rest, with explicit active and disabled text tokens.

Amber (`warning`) marks missing prerequisites and outcomes other than a verified match. Red (`error`) marks a session-level error event. These are semantic state colors, not additional brand accents.

**The Text Carries State Rule.** Always pair state color with readable status text; color alone never establishes readiness or success.

## Typography

Segoe UI is the sole explicitly configured family. Display is the application heading; headline is the current phase; title is a panel heading; result-title names the latest outcome. Body serves explanations and result text, action serves Start, and label serves auxiliary text and default ttk controls. Connection category labels use bold body text.

Font sizes are Tk point sizes, not CSS pixels. Line height, letter spacing and fallback families are not explicitly configured. Preserve Vietnamese diacritics and allow natural wrapping.

## Layout

The current window opens at 1100 by 700, with a minimum of 980 by 680. It resizes as a native Windows window; there are no web breakpoints or mobile layouts. This geometry was chosen to fit the actual 1280 by 800 desktop with window chrome and taskbar.

The current surface has a header and supporting sentence above three columns. The connection column has a minimum width of 220 and no expansion weight. Session and result columns each have minimum width 290 and equal expansion weight. Outer horizontal margins use `large`; white panels use `panel` padding. The left column has a 20-pixel trailing gap; the session column has a `panel` trailing gap.

Use the documented recurring spacing scale; small local offsets remain component-specific. Wrapped labels in white panels adapt to panel width minus 40, with a minimum wrap length of 180. Connection copy wraps at 195; the footer wraps at 900. Result text expands and has a vertical scrollbar.

## Elevation & Depth

The application draws no shadows. White panel surfaces against the cool canvas create separation. ttk owns its control relief and focus rendering; do not describe these as custom shadows or a custom focus-ring system.

## Shapes

Panels are rectangular Tk frames without an authored radius or decorative border. Result text has flat relief. Buttons have a configured one-pixel border width; their remaining geometry belongs to the ttk theme. No radius scale has been authored.

## Components

### Buttons

Start is the only filled primary action and spans its panel. Stop is a separate secondary button immediately below it. Guide, recheck and open-local-result actions use secondary styling. Padding and active/disabled treatments are defined above; keyboard focus follows ttk behavior without a custom override.

Start requires readiness and idle state. During work, Start, recheck and the turn selector are disabled; Stop is enabled until stopping begins. The local-result action remains disabled until a record path arrives and resets when a new turn begins.

### Panels and status labels

White work panels are quiet, flat containers. Readiness checks use a bold category above smaller wrapped status and explanation. Current phase uses the headline role with explanatory body text below. Listening receives teal; other phases use ink. Stopping remains visible while already-started work settles.

### Turn selector

The compact readonly ttk combobox offers 1, 2, 5 or 10 turns, defaults to 1, and uses a character width of 6. It is disabled while busy; it is not a freeform text field.

### Result area

The empty state explains what will appear after speech. A transcript state displays recognized speech and processing text. Final results show the status, transcript when available, explanation and attempted/acknowledged step counts. Only `verified_match` uses teal; other result statuses use amber, while a session error event uses red.

The result body is a read-only, word-wrapped Tk Text widget with an arrow cursor and vertical scrollbar. Selection uses the selection token. The open-local-result button sits below it.

## Do's and Don'ts

- Do preserve the light palette, Segoe UI hierarchy and explicit state labels.
- Do let explanatory content wrap and long result content scroll.
- Do use disabled controls to reflect the controller's real availability.
- Don't turn pending or uncertain outcomes into visual success.
- Don't add decorative imagery or animation to this established control-desk world.
- Don't infer web styling, mobile behavior, custom radii or custom focus treatments from native ttk defaults.

Documentation scope: source-grounded native implementation. Visual review reported by the implementation team covers actual readiness/empty output and a simulated stopping state; other documented states are extracted from code, not claimed as visually exercised.
