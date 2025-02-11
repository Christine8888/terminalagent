#!/usr/bin/env python3

import os
import base64
import shlex
import shutil
import httpx
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import uuid4
import base64
import io
from PIL import Image
import subprocess
import time
import yaml

# anthropic import
from anthropic import Anthropic, APIError
from anthropic.types.beta import (
    BetaMessage,
    BetaMessageParam,
    BetaToolResultBlockParam,
)

## CONFIG
CONFIG_PATH = "config.yml"
with open(CONFIG_PATH) as f:
    dict = yaml.safe_load(f)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", dict["anthropic_api_key"])
MODEL_NAME = "claude-3-5-sonnet-20241022"
COMPUTER_USE_BETA_FLAG = "computer-use-2024-10-22"
PROMPT_CACHING_BETA_FLAG = "prompt-caching-2024-07-31"

DISPLAY_WIDTH = 3456 
DISPLAY_HEIGHT = 2234

def trim_conversation(conversation: List[BetaMessageParam], keep_imgs: int = 3) -> List[BetaMessageParam]:
    image_positions = []
    
    for msg_idx, msg in enumerate(conversation):
        for content_idx, content in enumerate(msg['content']):
            if content['type'] == "image":
                image_positions.append((msg_idx, content_idx))
    
    images_to_keep = set(tuple(pos) for pos in image_positions[-keep_imgs:])
    
    trimmed_conversation = []
    
    for msg_idx, msg in enumerate(conversation):
        new_content = []
        
        for content_idx, content in enumerate(msg['content']):
            if content['type'] != "image" or (msg_idx, content_idx) in images_to_keep:
                new_content.append(content)
        
        if new_content:
            new_msg = msg.copy()
            new_msg['content'] = new_content
            trimmed_conversation.append(new_msg)
    
    return trimmed_conversation

# computer tool
def get_computer_tool() -> Dict[str, Any]:
    return {
        "type": "computer_20241022",
        "name": "computer",
        "display_width_px": DISPLAY_WIDTH,
        "display_height_px": DISPLAY_HEIGHT,
        "display_number": None, 
    }

def run_shell(cmd: str, timeout: float = 120.0) -> (int, str, str):
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
    x = int(x * 1.25)
    y = int(y * 1.25)
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

def key_press_mac(key: str) -> (int, str, str):
    # press some key
    
    # compounding
    if "+" in key:
        parts = key.split("+")
        if len(parts) == 2: # 2 part modifier
            modifier, main_key = parts
            modifier = modifier.lower().strip()
            main_key = main_key.lower().strip()
            
            rc1 = subprocess.run(f"cliclick kd:{modifier}", shell=True, capture_output=True)
            rc2 = subprocess.run(f"cliclick kp:{main_key}", shell=True, capture_output=True)
            rc3 = subprocess.run(f"cliclick ku:{modifier}", shell=True, capture_output=True)
            
            stdout = rc1.stdout + rc2.stdout + rc3.stdout
            stderr = rc1.stderr + rc2.stderr + rc3.stderr
            combined_out = stdout.decode(errors="replace")
            combined_err = stderr.decode(errors="replace")
            
            # return errors
            return (rc1.returncode or rc2.returncode or rc3.returncode, combined_out, combined_err)
        else:
            return (1, "", f"Invalid chord format: {key}")
    
    # single key handling
    text_lower = key.lower()
    mapping = {
        "return": "return",
        "enter": "return",
        "tab": "tab",
        "escape": "esc",
        "esc": "esc",
        "up": "arrow-up",
        "down": "arrow-down",
        "left": "arrow-left",
        "right": "arrow-right",
    }
    if text_lower in mapping:
        cmd_key = mapping[text_lower]
    else:
        cmd_key = text_lower
    
    cmd = f"cliclick kp:{cmd_key}"
    proc = subprocess.run(cmd, shell=True, capture_output=True)
    rc = proc.returncode or 0
    return (rc, proc.stdout.decode(errors="replace"), proc.stderr.decode(errors="replace"))


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
        "is_error": bool(error_text),
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

# agent loop
def run_agent_loop(user_instructions: str) -> None:
    system_prompt_text = """you are an assistant with access to a mac desktop environment via the 'computer' tool.\n"
        "actions:\n"
        "  - key: press a key or chord.\n"
        "  - type: type a string of text.\n"
        "  - cursor_position: get the current (x, y) coordinate.\n"
        "  - mouse_move: move cursor to (x, y).\n"
        "  - left_click: click left mouse at cursor.\n"
        "  - left_click_drag: click-drag from cursor to (x, y).\n"
        "  - right_click: right-click at cursor.\n"
        "  - middle_click: middle-click at cursor.\n"
        "  - double_click: double-click at cursor.\n"
        "  - screenshot: take a screenshot.\n"
        "1) follow instructions.\n"
        "2) if a step fails, adapt.\n"
        "3) provide text explanations as you go.\n"
        "4) always verify success with a screenshot.\n"""

    system_prompt = (system_prompt_text + "\n" + "USER INSTRUCTIONS: " + user_instructions)

    print(system_prompt)

    conversation: List[BetaMessageParam] = [
        {
            "role": "user",
            "content": [{"type": "text", "text": user_instructions}],
        }
    ]

    anthro = Anthropic(api_key=ANTHROPIC_API_KEY)
    beta_flags = [COMPUTER_USE_BETA_FLAG, PROMPT_CACHING_BETA_FLAG]

    while True:
        # attempt API call
        conversation = trim_conversation(conversation)
        try:
            system_block = {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
            response = anthro.beta.messages.create(
                model=MODEL_NAME,
                messages=conversation,
                system=[system_block],
                tools=[get_computer_tool()],
                max_tokens=1024,
                betas=beta_flags,
            )
            
        except APIError as e:
            print("api error:", e)
            return

        # add to conversation
        msg_obj: BetaMessage = response
        conversation.append({"role": "assistant", "content": msg_obj.model_dump()["content"],})

        # find tool use
        tool_uses = []
        for block in response.content:
            if block.type == "tool_use":
                tool_uses.append(block)
            elif block.type == "text":
                print(block.text)

        # user interaction
        if not tool_uses:
            final_text_parts = [block.text for block in msg_obj.content if block.type == "text"]
            print("===== message from claude =====")
            print("\n".join(final_text_parts))

            # ask user if they want to continue or exit
            user_input = input("\nYou: ").strip()
            if user_input.lower() in {"exit", "quit"}:
                print("exiting the conversation.")
                break

            conversation.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_input}
                ],
            })
            continue

        # if there are tool uses, handle them
        tool_result_blocks = []
        for tool_use_block in tool_uses:
            if tool_use_block.name == "computer":
                tool_use_input = tool_use_block.input
                tool_use_input["id"] = tool_use_block.id
                tool_result = handle_computer_tool_use(tool_use_input)
                tool_result_blocks.append(tool_result)
            else:
                tool_result_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_block.id,
                    "content": [{"type": "text", "text": f"unknown tool: {tool_use_block.name}"}],
                    "is_error": True,
                })

        conversation.append({
            "role": "user",
            "content": tool_result_blocks,
        })

# entry point
def main():
    instructions = (
        """Execute the following steps in the browser:
        1. Click on the Payments Tab.
        2. Click the "New Payment Request Button"
        3. Click on "Student Reimbursement"
        4. Switch back to the FX Reimbursements 24-25 Tab
        5. Locate the @stanford.edu email in the form response. The username that comes before the @ is the SUNet ID.
        6. Make note of the answer to "What FX project or team is this for?" as the "Project Name"
        7. Scroll down a full screen using function key + down arrow. Click on the document uploaded under "Itemized receipt upload". This will open a new tab.
        8. Download the document. This will open a new tab.
        9. Switch back to the FX Reimbursements 24-25 Tab.
        9. Click on the document uploaded under "Credit card or bank receipt upload". This will open a new tab.
        10. Download the document. This will open a new tab.
        11. Switch back to the FX Reimbursements 24-25 Tab.
        12. Make note of the Vendor name and Description of purchase. 
        13. Scroll down using function key + down arrow. Make note of the Total amount and Date of purchase. If you cannot see the total amount, scroll down more.
        14. Navigate back to the Payment Details tab.
        15. Fill in the Payee SUNet ID field with the SUNet ID you found in step 5.
        16. Fill in the Summary Description with the Project Name and Description of purchase.
        17. Double click on Document Date.
        18. Navigate to the correct calendar date.
        19. Click on Document Type.
        20. Select "Receipt" as the Document Type.
        21. Click the Paperclip icon.
        22. Upload the 2 downloaded documents.
        23. Click "OK" 
        24. Click on and fill in the Vendor name field.
        25. Click on and fill in the Amount field.
        26. Click "Save" in the top right corner.
        """
    )
    run_agent_loop(instructions)

if __name__ == "__main__":
    main()