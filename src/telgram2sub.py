import re
import os
import asyncio
import sys
from datetime import datetime, timedelta, timezone # Added timezone
from dotenv import load_dotenv
from tqdm import tqdm
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError
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

# Proxy settings (optional, set these in .env if needed)
PROXY_ENABLED = os.environ.get("PROXY_ENABLED", "False").lower() == "true"
PROXY_SERVER = os.environ.get("PROXY_SERVER")
PROXY_PORT = os.environ.get("PROXY_PORT")
PROXY_USERNAME = os.environ.get("PROXY_USERNAME")
PROXY_PASSWORD = os.environ.get("PROXY_PASSWORD")

# Regex to find vless and vmess links (captures the whole link)
V2RAY_REGEX = r"(vless|vmess)://[^\s\"\'<>)\[\]]+"

# Additional simple patterns as backup
VLESS_PATTERN = "vless://"
VMESS_PATTERN = "vmess://"

def update_readme(channel_username, channel_url, num_links, output_filename):
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
        rel_path = os.path.relpath(output_filename, os.path.dirname(readme_path)).replace('\\\\', '/')
        
        # Create the raw GitHub link
        raw_link = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{REPO_NAME}/main/{rel_path}"
        
        # Check if Telegram Channels section exists
        telegram_section = "### Telegram Channels"
        if telegram_section not in content:
            print("Warning: Telegram Channels section not found in README.md")
            return False
        
        # Check if this channel already exists in the table
        channel_entry = f"[{channel_username}]({channel_url})"
        
        # Content for the new row - proper table format with pipes and spacing
        row_content = f"| {channel_entry} | [vmess_vless_{num_links}]({raw_link}) |"
        
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
                    # If header found but no separator, add one robustly
                    table_separator_found = True
                    updated_lines.append("| ------------------------- | ------------------------------------------------------------ |")
                    # Continue processing the current line after adding the separator
                    # Fall through to the next block to check if this line is the target channel
            
            # Now we're in the table body, check for existing entries
            if in_telegram_section and table_header_found and table_separator_found:
                # If we find a line with our channel entry, replace it
                if channel_entry in line and line.strip().startswith("|"):
                    updated_lines.append(row_content)
                    channel_found = True
                    continue
                # If line is empty or starts a new section, exit the table search
                elif not line.strip() or (line.strip() and not line.strip().startswith("|")):
                    # If we haven't found and replaced our channel yet, add it before exiting the section
                    if not channel_found:
                        # Insert the new row just before the line that breaks the table format
                        updated_lines.append(row_content)
                        channel_found = True
                    updated_lines.append(line)
                    in_telegram_section = False # Exit the section
                    continue
            
            # Add all other lines unchanged
            updated_lines.append(line)
        
        # If we went through all lines and the table was at the end of the file, and we haven't added the channel yet
        if in_telegram_section and table_header_found and table_separator_found and not channel_found:
            # Add the row at the end of the list (effectively at the end of the file/section)
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
    channels_input_str = input(f"Enter Telegram channel links/usernames (comma-separated, e.g., @channel1, t.me/channel2). Press Enter for default '{DEFAULT_CHANNEL}': ") or DEFAULT_CHANNEL
    
    # Split the input string by commas and strip whitespace
    channel_identifiers = [ch.strip() for ch in channels_input_str.split(',') if ch.strip()]
    
    if not channel_identifiers:
        print("Error: No valid channel identifiers provided.")
        return

    # --- Ask for date limit ---
    days_limit = 0 # Default to all history
    while True:
        days_limit_str = input("Enter the number of days of history to fetch (e.g., 7). Press Enter or 0 for all history: ")
        if not days_limit_str or days_limit_str == '0':
            days_limit = 0
            print("Fetching all message history.")
            break
        try:
            days_limit = int(days_limit_str)
            if days_limit < 0:
                print("Please enter a non-negative number or 0.")
            else:
                print(f"Fetching messages from the last {days_limit} days.")
                break
        except ValueError:
            print("Invalid input. Please enter a number.")

    # --- Determine output filename based on input identifiers ---
    normalized_usernames = []
    for identifier in channel_identifiers:
        username = identifier # Default if no specific format found
        if "t.me/" in identifier:
            username = identifier.split("t.me/")[-1].split("/")[0]
        elif identifier.startswith('@'):
            username = identifier[1:]
        normalized_usernames.append(username)

    if len(normalized_usernames) == 1:
        base_filename = normalized_usernames[0]
    else:
        # Sort and join for multiple channels
        base_filename = "_".join(sorted(normalized_usernames))
        # Optional: Add prefix or limit length if filename becomes too long
        # base_filename = "combined_" + base_filename # Example prefix
        # if len(base_filename) > 100: # Example length limit
        #     import hashlib
        #     base_filename = hashlib.md5(base_filename.encode()).hexdigest()

    # --- Prepare output directory and file path ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, '..', OUTPUT_DIR)
    # Define output filename based on normalized channel username(s) (no extension)
    output_filename = os.path.join(output_path, base_filename)
    
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
            print("Found saved session string, attempting to use it...")
            with open(session_string_file, 'r') as f:
                session_string = f.read().strip()
        except Exception as e:
            print(f"Could not load saved session string: {e}")
    
    # --- Connect to Telegram ---
    # Determine the best session to use
    # Prioritize session string if available and valid
    use_session_string = False
    temp_client = None
    if session_string:
        try:
            temp_client = TelegramClient(StringSession(session_string), api_id_input, api_hash_input)
            await temp_client.connect()
            if await temp_client.is_user_authorized():
                use_session_string = True
                print("Session string is valid.")
            else:
                 print("Session string is invalid or expired.")
                 session_string = None # Clear invalid string
            await temp_client.disconnect()
        except Exception as e:
            print(f"Error validating session string: {e}. Falling back to session file/login.")
            session_string = None # Clear invalid string
        finally:
            if temp_client and temp_client.is_connected():
                await temp_client.disconnect()

    # Create client with proxy if enabled
    if use_session_string:
        print("Using validated session string.")
        client_kwargs = {
            'session': StringSession(session_string),
            'api_id': api_id_input,
            'api_hash': api_hash_input,
        }
    else:
        session_file_exists = os.path.exists(session_filepath + ".session")
        print(f"Using session file: {SESSION_FILE}" + (" (existing)" if session_file_exists else " (new will be created)"))
        client_kwargs = {
            'session': session_filepath, # Just provide the base name
            'api_id': api_id_input,
            'api_hash': api_hash_input,
        }

    # Add proxy if enabled
    if PROXY_ENABLED and PROXY_SERVER and PROXY_PORT:
        print(f"Using proxy: {PROXY_SERVER}:{PROXY_PORT}")
        try:
            proxy_port_int = int(PROXY_PORT)
            # Telethon proxy format depends on socks type, assuming socks5
            # Check telethon docs if using http proxy
            proxy_info = ('socks5', PROXY_SERVER, proxy_port_int)
            if PROXY_USERNAME and PROXY_PASSWORD:
                 client_kwargs['proxy'] = proxy_info + (True, PROXY_USERNAME, PROXY_PASSWORD) # Use tuple for auth
            else:
                 client_kwargs['proxy'] = proxy_info
        except ValueError:
            print(f"Error: Invalid PROXY_PORT '{PROXY_PORT}'. Must be an integer.")
            return
        except Exception as e:
            print(f"Error setting up proxy: {e}")
            return

    # Create the client with more robust settings
    client = TelegramClient(**client_kwargs)
    client.flood_sleep_threshold = 60  # Raise the threshold to avoid flood wait errors
    
    try:
        print("Connecting to Telegram...")
        await client.connect()
        
        # Ensure you're authorized
        if not await client.is_user_authorized():
            print("Authorization required.")
            if not phone_input:
                print("Phone number not provided in .env")
                phone_input = input("Enter your phone number (with country code, e.g., +1234567890): ")

            try:
                await client.send_code_request(phone_input)
                while True: # Loop until successful login or error
                    code = input('Enter the code you received: ')
                    try:
                        await client.sign_in(phone_input, code)
                        break # Signed in successfully
                    except telethon.errors.SessionPasswordNeededError:
                        password = input('Two-step verification enabled. Please enter your password: ')
                        try:
                           await client.sign_in(password=password)
                           break # Signed in with password successfully
                        except Exception as pw_error:
                           print(f"Password sign-in failed: {pw_error}")
                           # Decide if retry is needed or exit
                           retry = input("Retry password? (y/n): ").lower()
                           if retry != 'y': return
                    except telethon.errors.PhoneCodeInvalidError:
                        print("Invalid code. Please try again.")
                        # Loop continues to ask for code
                    except telethon.errors.PhoneCodeExpiredError:
                        print("Code expired. Requesting a new code...")
                        await client.send_code_request(phone_input) # Request new code
                        # Loop continues to ask for code
                    except telethon.errors.FloodWaitError as flood_error:
                         print(f"Flood wait error: trying again in {flood_error.seconds} seconds.")
                         await asyncio.sleep(flood_error.seconds + 1)
                         # Loop continues
                    except Exception as login_err:
                        print(f"Sign-in failed: {login_err}")
                        if client.is_connected(): await client.disconnect()
                        return # Exit on other errors

            except telethon.errors.FloodWaitError as flood_error:
                 print(f"Flood wait error on sending code: trying again in {flood_error.seconds} seconds.")
                 await asyncio.sleep(flood_error.seconds + 1)
                 # Consider adding retry logic here if needed
                 return
            except Exception as e:
                print(f"Authorization process failed: {e}")
                if client.is_connected(): await client.disconnect()
                return

        print("Successfully authorized and connected!")
        
        # Save session string for future use if not already using one
        if not use_session_string:
            try:
                # Force saving as StringSession
                session_str = StringSession.save(client.session)
                with open(session_string_file, 'w') as f:
                    f.write(session_str)
                print(f"Session string saved for future use in {session_string_file}")
            except Exception as e:
                print(f"Could not save session string: {e}")

        # Calculate cutoff date if a limit is set
        cutoff_date = None
        if days_limit > 0:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_limit)
            print(f"Fetching messages since {cutoff_date.strftime('%Y-%m-%d %H:%M:%S %Z')}...")

        # --- Loop through each channel identifier (from input) ---
        total_messages_scanned_all_channels = 0
        successful_channels_processed = [] # Keep track of channels we actually get data from

        for channel_input in channel_identifiers: # Iterate through original identifiers
            # Normalize again to get username for processing this specific channel
            current_channel_username = channel_input # Default
            if "t.me/" in channel_input:
                current_channel_username = channel_input.split("t.me/")[-1].split("/")[0]
            elif channel_input.startswith('@'):
                current_channel_username = channel_input[1:]
            # else: use channel_input as is

            print(f"\n--- Processing Channel: {current_channel_username} ---")

            try:
                # Get channel entity
                entity = await client.get_entity(current_channel_username)
                print(f"Accessing channel: {entity.title}")
                # Only add if entity lookup was successful
                if current_channel_username not in successful_channels_processed:
                     successful_channels_processed.append(current_channel_username)

                # --- Iterate through messages for this channel ---
                print("Reading messages...")
                channel_messages_scanned = 0

                # Initialize progress bar for this channel
                progress_desc = f"Scanning {current_channel_username}"
                if days_limit > 0:
                     progress_desc += f" (last {days_limit} days)"
                # Use total=None if date limited, as we don't know the total count beforehand
                # Re-initialize progress bar for each channel
                progress = tqdm(desc=progress_desc, unit="msg", total=None if days_limit > 0 else 0, leave=False) # leave=False for nested loops

                # Use client.iter_messages for simpler iteration and date filtering
                # reverse=False gets messages from newest to oldest
                async for message in client.iter_messages(entity, limit=None, reverse=False):
                    # Ensure message date is timezone-aware (Telethon usually provides UTC)
                    msg_date = message.date
                    if msg_date.tzinfo is None:
                         # If for some reason tzinfo is missing, assume UTC
                         msg_date = msg_date.replace(tzinfo=timezone.utc)

                    # Stop if message is older than the cutoff date
                    if cutoff_date and msg_date < cutoff_date:
                        print(f"\nReached date limit ({days_limit} days) for {current_channel_username}. Stopping scan for this channel.")
                        break # Exit the loop for this channel

                    progress.update(1)
                    channel_messages_scanned += 1
                    total_messages_scanned_all_channels += 1

                    if message.message: # Check if the message has text content
                        # Print message for debugging if verbose is enabled
                        if VERBOSE and channel_messages_scanned % 50 == 0:
                            print(f"\n{current_channel_username} - Message {channel_messages_scanned} (Date: {msg_date.strftime('%Y-%m-%d')})") # Removed content print

                        # Method 1: Use regex to find all V2Ray links
                        try:
                            # Find all matches using the comprehensive regex
                            # Make sure the regex matches the full vless/vmess link
                            full_matches = re.findall(V2RAY_REGEX, message.message) 
                            for config in full_matches:
                                # Combine the protocol and the rest of the link if regex captures parts
                                # Assuming V2RAY_REGEX captures the whole link directly now
                                full_link = config # If regex captures the whole link
                                # Example if regex captured ('vless', '://...'): full_link = config[0] + config[1]
                                if full_link not in found_configs:
                                    if VERBOSE:
                                        print(f"Found via regex: {full_link[:30]}...") # Print truncated config
                                    found_configs.add(full_link)
                        except Exception as e:
                            # Only log regex errors if verbose, as they can be noisy
                            if VERBOSE:
                               print(f"Minor error during regex matching in {current_channel_username}: {e}")

                        # Backup Method: Simple String Search (less reliable but catches edge cases)
                        msg_text = message.message
                        protocols = [VLESS_PATTERN, VMESS_PATTERN]
                        for protocol in protocols:
                            start_index = 0
                            while True:
                                start_index = msg_text.find(protocol, start_index)
                                if start_index == -1:
                                    break # No more occurrences of this protocol

                                # Find the end of the link (delimiters)
                                end_index = start_index + len(protocol)
                                while end_index < len(msg_text) and msg_text[end_index] not in " \\t\\n\\r\\\"'<>)[]":
                                    end_index += 1

                                link = msg_text[start_index:end_index]

                                # Basic validation and check for uniqueness
                                if link.startswith(protocol) and link not in found_configs:
                                    if VERBOSE:
                                         print(f"Found via backup search: {link[:30]}...")
                                    found_configs.add(link)

                                # Move start_index past the end of the found link
                                start_index = end_index

                    # Display count of found links periodically in the progress bar
                    if channel_messages_scanned % 100 == 0:
                        progress.set_postfix({"Links found (total)": len(found_configs)}, refresh=False)

                # Ensure final postfix update and close progress bar for the channel
                progress.set_postfix({"Links found (total)": len(found_configs)}, refresh=True)
                progress.close()
                print(f"Finished scanning {current_channel_username}. Scanned {channel_messages_scanned} messages.")

            except ValueError as ve:
                print(f"Error: Could not find the channel '{current_channel_username}'. Make sure the link/username is correct. Skipping.")
                if VERBOSE: print(f"Details: {ve}")
                continue # Skip to the next channel identifier
            except telethon.errors.ChannelPrivateError:
                 print(f"Error: Cannot access channel '{current_channel_username}'. It might be private or you are not a member. Skipping.")
                 continue # Skip to the next channel identifier
            except telethon.errors.UsernameNotOccupiedError:
                 print(f"Error: The username '{current_channel_username}' does not seem to exist. Skipping.")
                 continue # Skip to the next channel identifier
            except Exception as e:
                print(f"An unexpected error occurred while fetching messages from {current_channel_username}: {str(e)}")
                import traceback
                if VERBOSE:
                    traceback.print_exc()
                print(f"Skipping channel {current_channel_username} due to error.")
                continue # Skip to the next channel identifier

        # --- Save combined configs to file (using the pre-calculated filename) ---
        print(f"\nTotal messages scanned across all channels: {total_messages_scanned_all_channels}")
        
        if not successful_channels_processed:
            print("No channels were processed successfully.")
        elif not found_configs:
             # Check if any configs were found even if channels were processed
             print(f"No V2Ray configurations found across the successfully processed channels: {'/'.join(successful_channels_processed)}")
        else: # Found configs and at least one channel was successful
            print(f"Found {len(found_configs)} unique V2Ray configurations in total from: {'/'.join(successful_channels_processed)}.")

            # Use tqdm for the file write operation
            print(f"Saving configurations to {output_filename}...")
            # Sort the list before writing
            sorted_configs = sorted(list(found_configs))
            with open(output_filename, 'w', encoding='utf-8') as f:
                for config in tqdm(sorted_configs, desc="Writing to file", unit="link"):
                    f.write(config + '\n')

            print(f"Saved configurations to '{output_filename}'")

            # --- Update the README --- 
            # Use the base_filename determined earlier for the path
            readme_output_path = os.path.join(OUTPUT_DIR, base_filename).replace('\\', '/') 

            if GITHUB_USERNAME and REPO_NAME:
                if len(channel_identifiers) == 1:
                    # Use the single original (normalized) username for the README entry
                    # Ensure base_filename reflects the single channel processed
                    readme_channel_name = base_filename 
                    channel_url = f"https://t.me/{readme_channel_name}"
                    print(f"Attempting to update README for the single channel: {readme_channel_name}...")
                    update_readme(readme_channel_name, channel_url, len(found_configs), readme_output_path)
                else: # Multiple input channels
                    # Use a descriptive name including the successfully processed channels
                    # Sort the list of successful channels for consistent naming
                    processed_channel_list = ", ".join(sorted(successful_channels_processed))
                    readme_channel_name = f"Combined: {processed_channel_list}"
                    print(f"Attempting to update README for combined channels ({base_filename})...")
                    # Pass empty string for URL as it doesn't point to a single channel
                    update_readme(readme_channel_name, "", len(found_configs), readme_output_path)
            else:
                print("Skipping README update because GITHUB_USERNAME or REPO_NAME is not set.")
    except telethon.errors.RPCError as rpc_error:
        print(f"Telegram RPC Error: {rpc_error}")
        if "FLOOD_WAIT" in str(rpc_error):
             wait_time = int(re.search(r'(\d+)', str(rpc_error)).group(1))
             print(f"Flood wait requested. Please wait {wait_time} seconds before trying again.")
        # Add handling for other specific RPC errors if needed
    except Exception as e:
        error_msg = str(e)
        print(f"Connection or setup error: {error_msg}")

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
        # Use asyncio.run() which handles loop creation/management
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Fatal error in script execution: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) # Exit with error code
