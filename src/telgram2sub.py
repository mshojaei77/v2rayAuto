import re
import os
import asyncio
import sys
import datetime
from dotenv import load_dotenv
from tqdm import tqdm
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import PeerChannel, InputMessagesFilterEmpty
import telethon.utils
import telethon.errors
from telethon.sessions import StringSession

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
VERBOSE = False  # Set to True to see detailed output
SESSION_FILE = "telegram_session"  # Fixed session name for persistence
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME", "mshojaei77")  # GitHub username for raw links
REPO_NAME = os.environ.get("REPO_NAME", "v2rayAuto")  # Repository name
DEFAULT_DAYS_LIMIT = int(os.environ.get("DAYS_LIMIT", "7"))  # Default to extract links from last 7 days

# Proxy settings (optional, set these in .env if needed)
PROXY_ENABLED = os.environ.get("PROXY_ENABLED", "False").lower() == "true"
PROXY_SERVER = os.environ.get("PROXY_SERVER")
PROXY_PORT = os.environ.get("PROXY_PORT")
PROXY_USERNAME = os.environ.get("PROXY_USERNAME")
PROXY_PASSWORD = os.environ.get("PROXY_PASSWORD")

# Regex to find vless and vmess links
V2RAY_REGEX = r"(vless|vmess)://[^\s\"\'<>)]+"

# Additional simple patterns as backup
VLESS_PATTERN = "vless://"
VMESS_PATTERN = "vmess://"

def update_readme(channel_username, channel_url, num_links, output_filename, days_limit=0):
    """Update the README.md file with the subscription link"""
    readme_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.md")
    
    if not os.path.exists(readme_path):
        print(f"Warning: README.md not found at {readme_path}")
        return False
    
    try:
        # Read the current README content
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Get the relative path for the raw link (convert backslashes to forward slashes for GitHub)
        rel_path = os.path.relpath(output_filename, os.path.dirname(readme_path)).replace('\\', '/')
        
        # Create the raw GitHub link
        raw_link = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{REPO_NAME}/main/{rel_path}"
        
        # Check if Telegram Channels section exists
        telegram_section = "### Telegram Channels"
        if telegram_section not in content:
            print("Warning: Telegram Channels section not found in README.md")
            return False
        
        # Check if this channel already exists in the table
        channel_entry = f"[{channel_username}]({channel_url})"
        
        # Format the time limit info for display
        time_info = f" (last {days_limit} days)" if days_limit > 0 else ""
        
        # Content for the new row - proper table format with pipes and spacing
        row_content = f"| {channel_entry} | [vmess_vless_{num_links}{time_info}]({raw_link}) |"
        
        # If the channel already exists in the README, update its row
        lines = content.split("\n")
        updated_lines = []
        in_telegram_section = False
        table_header_found = False
        table_separator_found = False
        channel_found = False
        
        for line in lines:
            # Check if we're in the Telegram Channels section
            if telegram_section in line:
                in_telegram_section = True
                updated_lines.append(line)
                continue
            
            # If we're in the section and find a line starting with "| Channel", it's the table header
            if in_telegram_section and line.strip().startswith("| Channel"):
                table_header_found = True
                updated_lines.append(line)
                continue
            
            # After finding the header, look for the separator row (containing "|-")
            if in_telegram_section and table_header_found and not table_separator_found:
                if line.strip().startswith("|---") or line.strip().startswith("| ---"):
                    table_separator_found = True
                    updated_lines.append("| ------------------------- | ------------------------------------------------------------ |")
                    continue
                else:
                    # If header found but no separator, add one
                    table_separator_found = True
                    updated_lines.append("| ------------------------- | ------------------------------------------------------------ |")
            
            # Now we're in the table body, check for existing entries
            if in_telegram_section and table_header_found and table_separator_found:
                # If we find a line with our channel, replace it
                if channel_entry in line:
                    updated_lines.append(row_content)
                    channel_found = True
                    continue
                # If line is empty or starts new section, exit the table
                elif not line.strip() or (line.strip() and not line.strip().startswith("|")):
                    # If we haven't found and replaced our channel yet, add it here
                    if not channel_found:
                        updated_lines.append(row_content)
                        channel_found = True
                    updated_lines.append(line)
                    in_telegram_section = False  # Exit the section
                    continue
            
            # Add all other lines unchanged
            updated_lines.append(line)
        
        # If we went through all lines and never found a place to add our channel
        if in_telegram_section and table_header_found and table_separator_found and not channel_found:
            # Add before the last line if we're still in the table section
            updated_lines.append(row_content)
        
        # Write the updated content back to the README
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(updated_lines))
        
        print(f"Updated README.md with new subscription link for {channel_username}")
        return True
    
    except Exception as e:
        print(f"Error updating README.md: {e}")
        if VERBOSE:
            import traceback
            traceback.print_exc()
        return False

async def main():
    """Main function to connect, scrape, and save configs."""

    api_id_input = API_ID or input("Enter your API ID: ")
    api_hash_input = API_HASH or input("Enter your API Hash: ")
    phone_input = PHONE_NUMBER # Can be None if using a bot token

    # Get channel link/username with default value
    channel_input = input(f"Enter the Telegram channel link (or press Enter for default '{DEFAULT_CHANNEL}'): ") or DEFAULT_CHANNEL
    
    # Get time limit
    days_limit_input = input(f"Enter days limit (how many days back to extract links, default {DEFAULT_DAYS_LIMIT}, 0 for no limit): ")
    days_limit = int(days_limit_input) if days_limit_input.strip() else DEFAULT_DAYS_LIMIT
    
    if days_limit > 0:
        # Create UTC-aware datetime for comparison
        time_limit = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_limit)
        print(f"Extracting links from messages newer than {time_limit.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    else:
        time_limit = None
        print("No time limit applied - extracting links from all messages")
    
    # Handle different input formats for channel
    if "t.me/" in channel_input:
        channel_username = channel_input.split("t.me/")[-1].split("/")[0]
    elif channel_input.startswith('@'):
        channel_username = channel_input[1:]  # Remove @ symbol
    else:
        channel_username = channel_input

    # --- Prepare output directory and file path ---
    # Get the absolute path of the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Construct the path to the output directory (one level up from src)
    output_path = os.path.join(script_dir, '..', OUTPUT_DIR)
    
    # Add date suffix to filename for time-limited extractions
    if days_limit > 0:
        date_suffix = f"_last{days_limit}days"
        # Construct the full path for the output file (without extension)
        output_filename = os.path.join(output_path, f"{channel_username}{date_suffix}")
    else:
        # Construct the full path for the output file (without extension)
        output_filename = os.path.join(output_path, f"{channel_username}")
    
    # Use a fixed session file path for persistence
    session_filepath = os.path.join(script_dir, '..', SESSION_FILE)

    # Create output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)

    found_configs = set() # Use a set to store unique configs

    # Try to load saved session string if it exists
    session_string_file = os.path.join(script_dir, '..', f"{SESSION_FILE}.string")
    session_string = None
    if os.path.exists(session_string_file):
        try:
            print("Found saved session, attempting to use it...")
            with open(session_string_file, 'r') as f:
                session_string = f.read().strip()
        except Exception as e:
            print(f"Could not load saved session: {e}")
    
    # --- Connect to Telegram ---
    # Determine the best session to use
    use_session_file = os.path.exists(session_filepath) or os.path.exists(f"{session_filepath}.session")
    use_session_string = session_string is not None
    
    # Create client with proxy if enabled
    if use_session_string:
        print("Using saved session string...")
        client_kwargs = {
            'session': StringSession(session_string),
            'api_id': api_id_input,
            'api_hash': api_hash_input,
        }
    else:
        print(f"Using session file: {SESSION_FILE}" + (" (existing)" if use_session_file else " (new)"))
        client_kwargs = {
            'session': session_filepath,
            'api_id': api_id_input,
            'api_hash': api_hash_input,
        }
    
    # Add proxy if enabled
    if PROXY_ENABLED and PROXY_SERVER and PROXY_PORT:
        print(f"Using proxy: {PROXY_SERVER}:{PROXY_PORT}")
        proxy_port = int(PROXY_PORT) if PROXY_PORT else 1080
        client_kwargs['proxy'] = (PROXY_SERVER, proxy_port)
        if PROXY_USERNAME and PROXY_PASSWORD:
            client_kwargs['proxy_auth'] = (PROXY_USERNAME, PROXY_PASSWORD)
    
    # Create the client with more robust settings
    client = TelegramClient(**client_kwargs)
    client.flood_sleep_threshold = 60  # Raise the threshold to avoid flood wait errors
    
    try:
        print("Connecting to Telegram...")
        await client.connect()
        
        # Ensure you're authorized
        if not await client.is_user_authorized():
            if not phone_input:
                print("Phone number not provided in .env")
                phone_input = input("Enter your phone number (with country code, e.g., +1234567890): ")

            try:
                await client.send_code_request(phone_input)
                code = input('Enter the code you received: ')
                try:
                    await client.sign_in(phone_input, code)
                except telethon.errors.SessionPasswordNeededError:
                    password = input('Two-step verification enabled. Please enter your password: ')
                    await client.sign_in(password=password)
                except telethon.errors.PhoneCodeInvalidError:
                    print("Invalid code. Please try again.")
                    return
                except telethon.errors.PhoneCodeExpiredError:
                    print("Code expired. Please try again.")
                    return
                except telethon.errors.ResendCodeRequest:
                    print("Requesting a new code...")
                    await client.send_code_request(phone_input, force_sms=True)
                    code = input('Enter the new code you received: ')
                    await client.sign_in(phone_input, code)
            except Exception as e:
                print(f"Authorization failed: {e}")
                if client.is_connected():
                    await client.disconnect()
                return
        
        print("Successfully authorized and connected!")
        
        # Save session string for future use
        if not session_string:
            try:
                if isinstance(client.session, StringSession):
                    session_str = client.session.save()
                    with open(session_string_file, 'w') as f:
                        f.write(session_str)
                    print(f"Session saved for future use")
                else:
                    # Session file is already persistent, no need to save string
                    print("Using persistent session file")
            except Exception as e:
                print(f"Could not save session: {e}")
                
        try:
            # Get channel entity
            entity = await client.get_entity(channel_username)
            print(f"Accessing channel: {entity.title}")

            # --- Iterate through messages ---
            print("Reading messages (this might take a while for large channels)...")
            offset_id = 0
            limit = 200  # Increased batch size for faster processing
            total_messages = 0
            total_count_limit = 0  # Fetch all messages (no limit)
            
            # Keep track of filtered messages
            filtered_count = 0
            
            # Try to get message count for progress bar
            try:
                # This is an approximation and may not be accurate for all channels
                message_count = await client.get_messages(entity, limit=1)
                if message_count and hasattr(message_count[0], 'id'):
                    message_count = message_count[0].id
                    print(f"Estimated message count: {message_count}")
                else:
                    message_count = 2000  # Default estimation if can't determine
            except:
                message_count = 2000  # Default estimation if can't determine
                
            # Initialize progress bar
            progress = tqdm(total=message_count, desc="Scanning messages", unit="msg")
            
            while True:
                try:
                    # Use offset_date parameter for time filtering
                    history = await client(GetHistoryRequest(
                        peer=entity,
                        offset_id=offset_id,
                        offset_date=time_limit.replace(tzinfo=None) if time_limit else None,  # Make timezone-naive for Telethon
                        add_offset=0,
                        limit=limit,
                        max_id=0,
                        min_id=0,
                        hash=0
                    ))
                except Exception as e:
                    print(f"Error getting message history: {e}")
                    print("Continuing with messages collected so far...")
                    break

                if not history.messages:
                    break # No more messages

                messages = history.messages
                batch_messages = len(messages)
                progress.update(batch_messages)
                
                for message in messages:
                    total_messages += 1
                    
                    # Skip messages older than the time limit (double check)
                    # This is a backup check since we're already using offset_date
                    if time_limit and message.date < time_limit.replace(tzinfo=None):
                        filtered_count += 1
                        if VERBOSE:
                            print(f"Skipping message from {message.date.strftime('%Y-%m-%d %H:%M:%S')} (older than {days_limit} days)")
                        continue
                        
                    if message.message: # Check if the message has text content
                        # Print message for debugging if verbose is enabled
                        if VERBOSE and total_messages % 50 == 0:
                            print(f"\nMessage {total_messages}:\n{message.message[:200]}...\n")
                            
                        # Method 1: Use regex to find all V2Ray links
                        try:
                            full_matches = re.findall(V2RAY_REGEX, message.message)
                            for match in full_matches:
                                # If match is a tuple (from capturing groups)
                                if isinstance(match, tuple):
                                    config = match[0] + "://" + match[1] if len(match) > 1 else match[0]
                                else:
                                    config = match
                                
                                if config not in found_configs:
                                    if VERBOSE:
                                        print(f"Found via regex: {config[:30]}...") # Print truncated config
                                    else:
                                        # Only print every 25th link to avoid cluttering the console
                                        if len(found_configs) % 25 == 0:
                                            print(f"Found {len(found_configs)} links so far...")
                                    found_configs.add(config)
                        except Exception as e:
                            print(f"Error in regex matching: {e}")
                        
                        # Method 2: Manual search for links (backup)
                        msg_text = message.message
                        
                        # Check for vless links
                        vless_start = msg_text.find(VLESS_PATTERN)
                        while vless_start != -1:
                            # Find the end of the link
                            vless_end = vless_start
                            while vless_end < len(msg_text) and msg_text[vless_end] not in " \t\n\r\"'<>)":
                                vless_end += 1
                            
                            # Extract the link
                            vless_link = msg_text[vless_start:vless_end]
                            if vless_link not in found_configs:
                                if VERBOSE:
                                    print(f"Found via direct search: {vless_link[:30]}...") # Print truncated
                                found_configs.add(vless_link)
                            
                            # Look for the next occurrence
                            vless_start = msg_text.find(VLESS_PATTERN, vless_end)
                        
                        # Check for vmess links
                        vmess_start = msg_text.find(VMESS_PATTERN)
                        while vmess_start != -1:
                            # Find the end of the link
                            vmess_end = vmess_start
                            while vmess_end < len(msg_text) and msg_text[vmess_end] not in " \t\n\r\"'<>)":
                                vmess_end += 1
                            
                            # Extract the link
                            vmess_link = msg_text[vmess_start:vmess_end]
                            if vmess_link not in found_configs:
                                if VERBOSE:
                                    print(f"Found via direct search: {vmess_link[:30]}...") # Print truncated
                                found_configs.add(vmess_link)
                            
                            # Look for the next occurrence
                            vmess_start = msg_text.find(VMESS_PATTERN, vmess_end)

                offset_id = messages[-1].id
                
                # Display count of found links periodically
                if len(found_configs) % 50 == 0 and len(found_configs) > 0:
                    progress.set_postfix({
                        "Links found": len(found_configs),
                        "Time filtered": filtered_count
                    })
                
                if total_count_limit != 0 and total_messages >= total_count_limit:
                    print(f"Reached message limit of {total_count_limit}.")
                    break # Stop if message limit is reached
            
            # Show final counts
            print(f"Total messages scanned: {total_messages}")
            print(f"Messages filtered by date: {filtered_count}")
            print(f"Messages within time limit: {total_messages - filtered_count}")
            
            # Close progress bar
            progress.close()

            # --- Save configs to file ---
            if found_configs:
                print(f"\nFound {len(found_configs)} unique V2Ray configurations.")
                
                # Use tqdm for the file write operation
                print("Saving configurations...")
                with open(output_filename, 'w', encoding='utf-8') as f:
                    for config in tqdm(sorted(list(found_configs)), desc="Writing to file", unit="link"):
                        f.write(config + '\n')
                        
                print(f"Saved configurations to '{output_filename}'")
                
                # Get the channel URL
                channel_url = f"https://t.me/{channel_username}"
                
                # Update the README.md file
                update_readme(channel_username, channel_url, len(found_configs), output_filename, days_limit)
            else:
                print("No V2Ray configurations found in this channel.")

        except ValueError as ve:
            print(f"Error: Could not find the channel '{channel_username}'. Make sure the link/username is correct.")
            print(f"Details: {ve}")
        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
            import traceback
            if VERBOSE:
                traceback.print_exc()

    except Exception as e:
        error_msg = str(e)
        print(f"Connection error: {error_msg}")
        
        # Provide more helpful error message for common issues
        if "can't compare offset-naive and offset-aware datetimes" in error_msg:
            print("\nThis is a timezone issue. The fix has been applied in the latest version.")
            print("Please run the script again.")
        
        import traceback
        if VERBOSE:
            traceback.print_exc()
    
    finally:
        # Make sure we disconnect properly
        if 'client' in locals() and client.is_connected():
            await client.disconnect()
            print("Disconnected from Telegram.")

if __name__ == '__main__':
    try:
        # Force asyncio to use the current event loop or create a new one
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
