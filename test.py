#!/usr/bin/env python3

import subprocess
import time
import shutil
import sys

def main():
    cliclick_path = shutil.which("cliclick")
    if not cliclick_path:
        print("Error: 'cliclick' not found on PATH.")
        print("       Check that brew (or your install method) put cliclick in /usr/local/bin or /opt/homebrew/bin, etc.")
        sys.exit(1)
    print(f"'cliclick' found at: {cliclick_path}")

   
    move_cmd = "cliclick m:1,1"
    proc = subprocess.run(move_cmd, shell=True, capture_output=True)

    if proc.returncode != 0:
        print("Error moving mouse:")
        print(proc.stderr.decode("utf-8"))
    else:
        print("Mouse moved to (1, 1).")
    time.sleep(1)

    click_cmd = "cliclick c:1,1"
    print(f"Running: {click_cmd}")
    proc = subprocess.run(click_cmd, shell=True, capture_output=True)

    if proc.returncode != 0:
        print("Error clicking mouse:")
        print(proc.stderr.decode("utf-8"))
    else:
        print("Clicked at (1, 1).")

    print("Test complete.")

if __name__ == "__main__":
    main()
