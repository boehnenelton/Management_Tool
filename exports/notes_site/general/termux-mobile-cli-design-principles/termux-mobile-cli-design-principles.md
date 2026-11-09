#termux #mobile #cli
# Termux Mobile CLI Design Principles
# General

### Viewport & TUI Laws
When authoring CLI applications on Android Termux:
1. Enforce **57-column viewport discipline** for mobile portrait mode.
2. Avoid curses/ncurses raw terminal traps.
3. Use Truecolor `#DE2626` with ANSI Red fallback per Policy Section 8.1.

