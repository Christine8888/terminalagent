#!/usr/bin/env python3

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import uuid4
from PIL import Image
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