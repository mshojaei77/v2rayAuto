import re
import os
import asyncio
from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import PeerChannel

# Load environment variables from .env file first
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# --- Configuration ---
# Get these from https://my.telegram.org/apps
# It's recommended to use environment variables or a config file for sensitive data
API_ID = os.environ.get("TELEGRAM_API_ID")
API_HASH = os.environ.get("TELEGRAM_API_HASH")
PHONE_NUMBER = os.environ.get("TELEGRAM_PHONE_NUMBER") # Optional, if using user account
OUTPUT_DIR = "telegram"
DEFAULT_CHANNEL = "t.me/Spdnetpro"  # Default channel to scrape

# Regex to find vless and vmess links
V2RAY_REGEX = r"(vless|vmess)://[A-Za-z0-9+/=_\\-]+[^\s]*"

async def main():
    """Main function to connect, scrape, and save configs."""

    api_id_input = API_ID or input("Enter your API ID: ")
    api_hash_input = API_HASH or input("Enter your API Hash: ")
    phone_input = PHONE_NUMBER # Can be None if using a bot token

    # Get channel link/username with default value
    channel_input = input(f"Enter the Telegram channel link (or press Enter for default '{DEFAULT_CHANNEL}'): ") or DEFAULT_CHANNEL
    if "t.me/" in channel_input:
        channel_username = channel_input.split("/")[-1]
    else:
        channel_username = channel_input

    # --- Prepare output directory and file path ---
    # Get the absolute path of the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Construct the path to the output directory (one level up from src)
    output_path = os.path.join(script_dir, '..', OUTPUT_DIR)
    # Construct the full path for the output file
    output_filename = os.path.join(output_path, f"{channel_username}.txt")
    session_filepath = os.path.join(script_dir, '..', f"{channel_username}_session")

    # Create output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)

    found_configs = set() # Use a set to store unique configs

    # --- Connect to Telegram ---
    # Use a session file (in root dir) to avoid logging in every time
    async with TelegramClient(session_filepath, api_id_input, api_hash_input) as client:
        print(f"Connecting to Telegram...")

        # Ensure you're authorized
        if not await client.is_user_authorized():
            await client.connect()
            if not phone_input:
                 # If using bot token, this part is usually not needed unless it's the first run
                 print("Bot token detected or phone number not provided.")
                 # Depending on bot setup, authorization might happen differently or be pre-configured.
                 # For user accounts, phone number is typically required for the first login.
                 phone_input = input("Enter your phone number (needed for first login): ")

            if phone_input:
                 try:
                     await client.send_code_request(phone_input)
                     code = input('Enter the code you received: ')
                     await client.sign_in(phone_input, code)
                 except SessionPasswordNeededError:
                     password = input('Two-step verification enabled. Please enter your password: ')
                     await client.sign_in(password=password)
            else:
                 print("Cannot proceed without phone number for user account or proper bot token setup.")
                 return # Exit if authorization cannot proceed

        print("Successfully connected.")

        try:
            # Get channel entity
            entity = await client.get_entity(channel_username)
            print(f"Accessing channel: {entity.title}")

            # --- Iterate through messages ---
            print("Reading messages (this might take a while for large channels)...")
            offset_id = 0
            limit = 100 # Process messages in batches
            total_messages = 0
            total_count_limit = 0 # Set to 0 to fetch all messages, or a number to limit

            while True:
                history = await client(GetHistoryRequest(
                    peer=entity,
                    offset_id=offset_id,
                    offset_date=None,
                    add_offset=0,
                    limit=limit,
                    max_id=0,
                    min_id=0,
                    hash=0
                ))

                if not history.messages:
                    break # No more messages

                messages = history.messages
                for message in messages:
                    total_messages += 1
                    if message.message: # Check if the message has text content
                        # Find all V2Ray links in the message text
                        full_matches = re.findall(V2RAY_REGEX, message.message)
                        for config in full_matches:
                            if config not in found_configs:
                                print(f"Found: {config[:30]}...") # Print truncated config
                                found_configs.add(config)

                offset_id = messages[-1].id
                print(f"Processed {total_messages} messages...")

                if total_count_limit != 0 and total_messages >= total_count_limit:
                    print(f"Reached message limit of {total_count_limit}.")
                    break # Stop if message limit is reached

            # --- Save configs to file ---
            if found_configs:
                print(f"\nFound {len(found_configs)} unique V2Ray configurations.")
                with open(output_filename, 'w', encoding='utf-8') as f:
                    for config in sorted(list(found_configs)): # Sort for consistency
                        f.write(config + '\n')
                print(f"Saved configurations to '{output_filename}'")
            else:
                print("No V2Ray configurations found in this channel.")

        except ValueError:
            print(f"Error: Could not find the channel '{channel_username}'. Make sure the link/username is correct.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    # Run the asynchronous main function
    # In environments like Jupyter notebooks, you might need asyncio.run() instead
    # Or handle the event loop differently depending on the context.
    # For simple script execution, this should work.
    # Check if an event loop is already running (e.g., in Spyder/IPython)
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
             # If a loop is running (like in Jupyter), create a task
             loop.create_task(main())
             # Note: In a notebook, you might need to await this task explicitly
             # or manage the cell execution until the task completes.
        else:
             # If no loop is running, start a new one
             asyncio.run(main())
    except RuntimeError:
         # No running event loop, start a new one
         asyncio.run(main())
