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
import pyautogui
import yaml
import tool

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

def print_conversation(conversation: List[BetaMessageParam]):
    for msg in conversation:
        for content in msg['content']:
            if content['type'] == 'text':
                print(content['text'])
            elif content['type'] == 'image':
                print(f"image")
            else:
                print(f"unknown content type: {content['type']}")

def trim_conversation(conversation: List[BetaMessageParam], keep_imgs: int = 5) -> List[BetaMessageParam]:
    image_positions = []

   # some images are nested in tool_result content
    for msg_idx, msg in enumerate(conversation):
        for content_idx, content in enumerate(msg['content']):
            if content['type'] == "image":
                image_positions.append((msg_idx, content_idx))
            elif content['type'] == "tool_result":
                
                if isinstance(content.get('content'), list):
                    for nested_content in content['content']:
                        if nested_content.get('type') == "image":
                            image_positions.append((msg_idx, content_idx))
                            break  
    
    images_to_keep = set(tuple(pos) for pos in image_positions[-keep_imgs:])
    
    trimmed_conversation = []
    
    for msg_idx, msg in enumerate(conversation):
        new_content = []
        
        for content_idx, content in enumerate(msg['content']):
            position = (msg_idx, content_idx)
            if content['type'] in ["text", "tool_use"]:
                new_content.append(content)
            elif content['type'] == "image" and position in images_to_keep:
                new_content.append(content)
            elif content['type'] == "tool_result":
                if position in images_to_keep:
                    new_content.append(content)
                else:
                    # remove images from tool_result content
                    if isinstance(content.get('content'), list):
                        filtered_content = [
                            item for item in content['content'] 
                            if item.get('type') != "image"
                        ]
                        if filtered_content:  # Only add if there's remaining content
                            new_content_item = content.copy()
                            new_content_item['content'] = filtered_content
                            new_content.append(new_content_item)
                    else:
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
        "  - scroll: scroll a pixel amount, can be positive or negative.\n"
        "1) follow instructions.\n"
        "2) if a step fails, adapt.\n"
        "3) provide text explanations as you go.\n"
        "4) always verify success with a screenshot.\n"""

    system_prompt = (system_prompt_text + "\n" + "USER INSTRUCTIONS: " + user_instructions)

    conversation: List[BetaMessageParam] = [
        {
            "role": "user",
            "content": [{"type": "text", "text": "Follow the given instructions."}],
        }
    ]

    anthro = Anthropic(api_key=ANTHROPIC_API_KEY)
    beta_flags = [COMPUTER_USE_BETA_FLAG, PROMPT_CACHING_BETA_FLAG]

    while True:
        # attempt API call
        conversation = trim_conversation(conversation)
        # print_conversation(conversation)
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
                tool_result = tool.handle_computer_tool_use(tool_use_input)
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
    main_instructions = """You are in Row 51 of the FX Reimbursements 24-25 Google Sheet. You have access to a Payments tab in the browser.
        Only record values from a box that you have selected. Do not look at any other rows. Do not use Alt Tab.
        Check every step before proceeding. If a step fails, try to fix it and do not move on.
        Execute the following steps in the browser. """
    
    fillout_instructions = main_instructions + """
        SETTING UP THE PAYMENT REQUEST:
        1. Locate the @stanford.edu email under Email Address. The username that comes before the @ is the SUNet ID. It should contain mostly letters.
        2. Find the "Project Name" column. Remember this as the project name
        3. Click on the Payments Tab.
        4. Click the "New Payment Request Button"
        5. Click on "Student Reimbursement"
        6. Fill in the Payee SUNet ID field with the SUNet ID you found in step 5.
        7. Fill in the Summary Description with the Project Name (Column E) and Description of purchase (Column F).
        8. Click the "Next" button in the top right"""

    fillout_instructions_2 = main_instructions + """
        FILLING OUT THE PAYMENT REQUEST:
        1. Switch back to the FX Reimbursements 24-25 Tab.
        2. Move several columns to the right using the right arrow key, until you are in the Amount column. Make note of the Description of purchase, Vendor name, Total amount and Date of purchase.
        3. Navigate back to the Payment Details tab.
        4. Double click on the date box, below the Document Date header.
        5. First click the year field (2025), then select the correct year from the dropdown.
        6. Then click the month field (February), then select the correct month from the dropdown.
        7. Then select the correct day from the calendar.
        8. Click on the text box under "Document Type".
        9. Type the letter "R" in the text box.
        10. Click on the text box in the "Vendor" column. Type in the Vendor name.
        11. Click on the text box in the "Amount" column and type in the Amount.
        12. Double click on the text box in the "Account" field.
        13. Click on "The Stanford Fund Partnership".
        14. Click "Save" in the top right corner."""


    document_instructions = """
        You are in Row 51 of the FX Reimbursements 24-25 Google Sheet.
        Only record values from a box that you have selected. Do not look at any other rows. Do not use Alt Tab.
        Check every step before proceeding. If a step fails, try to fix it and do not move on.
        Execute the following steps in the browser:

        DOWNLOADING THE DOCUMENTS:
        1. Switch back to the FX Reimbursements 24-25 Google Sheet tab
        2. Go one column to the right, so that you are in the column labeled "Itemized receipt upload". Click on the link. This will open a pop-up.
        3. Click on the image in the pop-up. This will open a new tab.
        4. Wait for the document to load.
        5. Click the download icon.
        6. Wait for the document to download. Remember the document name.
        7. Switch back to the FX Reimbursements 24-25 Tab.
        8. Use the right arrow key to move to Column H. This is the column labeled "Credit card or bank statement". Click on the link. This will open a pop-up.
        9. Click on the image in the pop-up. This will open a new tab.
        10. Wait for the document to load.
        11. Click the download icon.
        12. Wait for the document to download. Remember the document name.

        UPLOADING DOCUMENTS:
        13. Click the Paperclip icon.
        14. Click inside the large white blank rectangle.
        15. A file explorer will pop up. Look in the file explorer for the first document you downloaded.
        16. Click on the document and make sure it is highlighted blue.
        17. Press the blue "Open" button in the bottom right corner.
        18. Click the white rectangle again.
        19. Look in the file explorer for the second document you downloaded.
        20. Click on the document and make sure it is highlighted blue.
        21. Click the blue "Open" button in the bottom right corner.
        22. Wait for the documents to upload.
        23. Click the "OK" button in the bottom right corner.
        24. Click "Save" in the top right corner.
        """
    # instructions = (
    #     """
    #     Ask the user any clarifying questions when needed. Check every step before proceeding.

    #     Execute the following steps in the browser:
    #     1. Click on the Payments Tab.
    #     2. Click the "New Payment Request Button"
    #     3. Click on "Student Reimbursement"
    #     4. Switch back to the FX Reimbursements 24-25 Tab
    #     5. Locate the @stanford.edu email in the form response. The username that comes before the @ is the SUNet ID. It should contain mostly letters.
    #     6. Find the answer to "What FX project or team is this for?" and remember this as the project name
    #     7. Scroll down a full screen using the space key. Click on the document uploaded under "Itemized receipt upload". This will open a new tab.
    #     8. Download the document. This will open a new tab.
    #     9. Switch back to the FX Reimbursements 24-25 Tab.
    #     9. Click on the document uploaded under "Credit card or bank receipt upload". This will open a new tab.
    #     10. Download the document. This will open a new tab.
    #     11. Switch back to the FX Reimbursements 24-25 Tab.
    #     12. Make note of the Vendor name and Description of purchase. 
    #     13. Scroll down a full screen using the space key. Make note of the Total amount and Date of purchase. If you cannot see the total amount, scroll down more.
    #     14. Navigate back to the Payment Details tab.
    #     15. Fill in the Payee SUNet ID field with the SUNet ID you found in step 5.
    #     16. Fill in the Summary Description with the Project Name and Description of purchase.
    #     17. Double click on Document Date.
    #     18. Navigate to the correct calendar date.
    #     19. Click on Document Type.
    #     20. Select "Receipt" as the Document Type.
    #     21. Click the Paperclip icon.
    #     22. Upload the 2 downloaded documents.
    #     23. Click "OK" 
    #     24. Click on and fill in the Vendor name field.
    #     25. Click on and fill in the Amount field.
    #     26. Click "Save" in the top right corner.
    #     """
    # )
    run_agent_loop(fillout_instructions)
    run_agent_loop(fillout_instructions_2)
    run_agent_loop(document_instructions)

if __name__ == "__main__":
    main()