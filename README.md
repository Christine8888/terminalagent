# terminalagent

Basic implementation of [Claude Computer Use](https://docs.anthropic.com/en/docs/build-with-claude/computer-use)

- Loop runs directly in terminal (*no sandboxing*, be careful, but it can work with everything on your desktop)
- Tools (clicking, dragging, keyboard, screenshot) implemented with cliclick and pyautogui
- Specify tasks directly in the terminal, or call the agent loop from a script with instructions



TO USE:
- Install required packages from requirements.txt and cliclick with Homebrew
- Create a config.yml file with your Anthropic API token
- Set the API token field and screen resolution in agent.py
- Run agent.py in a terminal
