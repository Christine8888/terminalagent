#!/usr/bin/env python3

import base64
import shlex
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import uuid4
import base64
import io
from PIL import Image
import subprocess
import time
import pyautogui

# anthropic import
from anthropic import Anthropic, APIError
from anthropic.types.beta import (
    BetaMessage,
    BetaMessageParam,
    BetaToolResultBlockParam,
)

VERBOSE = True
# on my computer I have to adjust Claude's coordiantes?? to get the correct position
OFFSET = 1.25

def run_shell(cmd: str, timeout: float = 120.0) -> (int, str, str):
    if VERBOSE:
        print(f"running: {cmd}")
    try:
        proc = subprocess.run(
            cmd, shell=True, capture_output=True, timeout=timeout
        )
        rc = proc.returncode or 0
        stdout = proc.stdout.decode(errors="replace")
        stderr = proc.stderr.decode(errors="replace")
        return rc, stdout, stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"command {cmd} timed out"

def compress_screenshot(png_b64_data: str, quality=50) -> str:
    # compress screenshot to jpeg
    png_bytes = base64.b64decode(png_b64_data)
    img = Image.open(io.BytesIO(png_bytes))
    
    # Store original dimensions
    original_width, original_height = img.size
    
    if img.mode == "RGBA":
        # Convert to RGB while maintaining dimensions
        img = img.convert("RGB")
    
    img = img.resize((original_width, original_height), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    compressed_data = buf.getvalue()
    return base64.b64encode(compressed_data).decode("utf-8")

# screenshot tool
def screenshot_mac() -> Optional[str]:
    output_dir = Path("/tmp/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = output_dir / f"screenshot_{uuid4().hex}.png"

    cmd = f"screencapture -x {shlex.quote(str(screenshot_path))}"
    rc, out, err = run_shell(cmd)
    if rc != 0 or not screenshot_path.is_file():
        return None

    return base64.b64encode(screenshot_path.read_bytes()).decode("utf-8")

# mouse movement and click tools
def mouse_move_mac(x: int, y: int) -> (int, str, str):
    # this is so stupid lmao
    x = int(x * OFFSET)
    y = int(y * OFFSET)
    cmd = f"cliclick m:{x},{y}"
    return run_shell(cmd)

def left_click_drag_mac(x_end: int, y_end: int) -> (int, str, str):
    rc, out, err = run_shell("cliclick p")
    if rc != 0 or not out.strip():
        return (rc, "", f"could not get current mouse position: {err or out}")

    current_pos = out.strip()
    if "," not in current_pos:
        return (rc, "", f"unexpected format: {current_pos}")
    x_start_str, y_start_str = current_pos.split(",", 1)
    try:
        x_start = int(x_start_str)
        y_start = int(y_start_str)
    except ValueError as ve:
        return (rc, "", f"could not parse coords: {ve}")

    dd_cmd = f"cliclick dd:{x_start},{y_start}"
    rc2, out2, err2 = run_shell(dd_cmd)
    m_cmd = f"cliclick m:{x_end},{y_end}"
    rc3, out3, err3 = run_shell(m_cmd)
    du_cmd = f"cliclick du:{x_end},{y_end}"
    rc4, out4, err4 = run_shell(du_cmd)

    full_out = f"{out2}\n{err2}\n{out3}\n{err3}\n{out4}\n{err4}"
    final_rc = rc2 or rc3 or rc4
    return final_rc, full_out, ""

def get_pos():
    rc, out, err = run_shell("cliclick p")
    if rc != 0 or not out.strip():
        return (rc, "", f"could not get current position: {err or out}")
    x_str, y_str = out.strip().split(",", 1)
    return x_str, y_str

def left_click_mac_current() -> (int, str, str):
    x_str, y_str = get_pos()
    cmd = f"cliclick c:{x_str},{y_str}"
    return run_shell(cmd)

def right_click_mac_current() -> (int, str, str):
    x_str, y_str = get_pos()
    cmd = f"cliclick rc:{x_str},{y_str}"
    return run_shell(cmd)

def middle_click_mac_current() -> (int, str, str):
    x_str, y_str = get_pos()
    cmd = f"cliclick c:{x_str},{y_str}"
    return run_shell(cmd)

def double_click_mac_current() -> (int, str, str):
    x_str, y_str = get_pos()
    cmd = f"cliclick dc:{x_str},{y_str}"
    return run_shell(cmd)

def get_cursor_position_mac() -> (int, str, str):
    return run_shell("cliclick p")

def type_text_mac(text: str) -> (int, str, str):
    chunk_size = 50
    all_out = []
    all_err = []
    rc_accum = 0
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        cmd = f"cliclick t:{shlex.quote(chunk)}"
        rc, out, err = run_shell(cmd)
        rc_accum = rc_accum or rc
        if out:
            all_out.append(out)
        if err:
            all_err.append(err)
    return rc_accum, "\n".join(all_out), "\n".join(all_err)

def scroll_mac(pixels: int) -> (int, str, str):
    num_presses = abs(pixels) // 25
    key = "arrow-down" if pixels > 0 else "arrow-up"
    cmd = "cliclick " + " ".join([f"kp:{key} w:50"] * num_presses)
    
    return run_shell(cmd)

def key_press_mac(key: str) -> (int, str, str):
    if VERBOSE:
        print(f"pressing: {key}")
    # Map keys to PyAutoGUI format
    key_mapping = {
        "return": "enter",
        "escape": "esc",
        "arrow-down": "down",
        "arrow-up": "up",
        "arrow-left": "left",
        "arrow-right": "right",
        "page-down": "pagedown",
        "page-up": "pageup",
        "control": "ctrl",
        "cmd": "command",
        "option": "alt",
    }
    
    try:
        # Split the input string and remove whitespace
        keys = [k.strip().lower() for k in key.split("+")]
        
        # If it's a single key, use press() as before
        if len(keys) == 1:
            pyautogui.press(key_mapping.get(keys[0], keys[0]))
        # If it's a key combination, use keyDown() and keyUp()
        else:
            # Map each key in the combination
            mapped_keys = [key_mapping.get(k, k) for k in keys]
            
            # Hold down all keys in sequence
            for k in mapped_keys:
                pyautogui.keyDown(k)
                
            # Release all keys in reverse order
            for k in reversed(mapped_keys):
                pyautogui.keyUp(k)
            
        return 0, "", ""
    except Exception as e:
        return 1, "", str(e)

def return_action(tool_use_id: str, output_text: str, error_text: str, img: str):
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": [
            {
                "type": "text",
                "text": ("RESULT: " + output_text + "\n" + error_text + "\n").strip()
            },
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": img or ""
                }
            }
        ],
    }
    

# main computer use loop
def handle_computer_tool_use(tool_input: Dict[str, Any]) -> BetaToolResultBlockParam:
    action = tool_input.get("action")
    text = tool_input.get("text")
    coord = tool_input.get("coordinate")
    tool_use_id = tool_input.get("id", "missing_id")

    output_text = ""
    error_text = ""

    def do_screenshot():
        img = screenshot_mac()
        if not img:
            return None, "[error] screenshot failed"
        compressed_img = compress_screenshot(img, quality=50)
        return compressed_img, ""

    if action == "mouse_move":
        if not isinstance(coord, list) or len(coord) != 2:
            error_text += "[error] 'mouse_move' requires a 2-element list\n"
        else:
            x, y = coord
            rc, out, err = mouse_move_mac(x, y)
            if out: output_text += out
            if err: error_text += err
            
            img, shot_err = do_screenshot()
            if shot_err: error_text += shot_err
    
    elif action == "left_click_drag":
        if not isinstance(coord, list) or len(coord) != 2:
            error_text += "[error] 'left_click_drag' requires 2-element list\n"
        else:
            x_end, y_end = coord
            rc, out, err = left_click_drag_mac(x_end, y_end)
            if out: output_text += out
            if err: error_text += err
            
            img, shot_err = do_screenshot()
            if shot_err: error_text += shot_err
            
    elif action == "screenshot":
        img, shot_err = do_screenshot()
        if shot_err: error_text += shot_err

    elif action == "cursor_position":
        rc, out, err = get_cursor_position_mac()
        if out: output_text += out
        if err: error_text += err
        
        img, shot_err = do_screenshot()
        if shot_err: error_text += shot_err

    elif action == "left_click":
        rc, out, err = left_click_mac_current()
        if out: output_text += out
        if err: error_text += err   
        time.sleep(2)
        img, shot_err = do_screenshot()
        if shot_err: error_text += shot_err

    elif action == "right_click":
        rc, out, err = right_click_mac_current()
        if out: output_text += out
        if err: error_text += err
        
        img, shot_err = do_screenshot()
        if shot_err: error_text += shot_err

    elif action == "middle_click":
        rc, out, err = middle_click_mac_current()
        if out: output_text += out
        if err: error_text += err
        
        img, shot_err = do_screenshot()
        if shot_err: error_text += shot_err

    elif action == "double_click":
        rc, out, err = double_click_mac_current()
        if out: output_text += out
        if err: error_text += err
        
        img, shot_err = do_screenshot()
        if shot_err: error_text += shot_err

    elif action == "key":
        if not isinstance(text, str):
            error_text += "[error] 'key' must have 'text'\n"
        else:
            rc, out, err = key_press_mac(text)
            if out: output_text += out
            if err: error_text += err
            
            img, shot_err = do_screenshot()
            if shot_err: error_text += shot_err

    elif action == "type":
        if not isinstance(text, str):
            error_text += "[error] 'type' must have 'text'\n"
        else:
            rc, out, err = type_text_mac(text)
            if out: output_text += out
            if err: error_text += err
            
            img, shot_err = do_screenshot()
            if shot_err: error_text += shot_err

    elif action == "scroll":
        if not isinstance(text, int):
            error_text += "[error] 'scroll' must have 'text'\n"
        else:
            rc, out, err = scroll_mac(text)
            if out: output_text += out
            if err: error_text += err
    else:
        # no recognized action
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": [
                {"type": "text", "text": f"[error] unrecognized action: {action}"}
            ],
            "is_error": True
        }

    return return_action(tool_use_id, output_text, error_text, img)