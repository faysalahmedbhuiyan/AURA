"""
AURA Backend — Computer Control Package.

Package: app.computer_control
Phase: Tier 4-A3 — Windows Computer Control

SAFETY RULES (non-negotiable):
    - HIGH RISK actions (shell commands, file delete) → confirmed=True required
    - LOW RISK actions (screenshot, clipboard read, window list) → no confirmation
    - Every action is logged with timestamp
    - User can disable computer control entirely via settings

Supported controllers:
    WindowController    — list, focus, minimize, maximize windows
    ClipboardController — read and write clipboard
    ScreenshotController— capture screen, OCR text extraction
    ShellController     — run PowerShell/CMD (HIGH RISK, approval required)
    BrowserController   — open URLs in default browser
"""