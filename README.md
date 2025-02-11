# terminalagent

Basic implementation of [Claude Computer Use](https://docs.anthropic.com/en/docs/build-with-claude/computer-use)

- Loop runs directly in terminal (*no sandboxing*, be careful, but it can work with everything on your desktop)
- Tools (clicking, dragging, keyboard, screenshot) implemented with cliclick and pyautogui
- Specify tasks directly in the terminal, or call the agent loop from a script with instructions