import re
import os
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from tqdm import tqdm
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import PeerChannel
import telethon.utils
import telethon.errors
from telethon.sessions import StringSession

# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Configuration from environment variables
API_ID = os.environ.get("TELEGRAM_API_ID")
API_HASH = os.environ.get("TELEGRAM_API_HASH")
PHONE_NUMBER = os.environ.get("TELEGRAM_PHONE_NUMBER")
OUTPUT_DIR = "telegram"
VERBOSE = False  # Set to True for detailed output
SESSION_FILE = "telegram_session"  # Fixed session name for persistence
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME", "mshojaei77")
REPO_NAME = os.environ.get("REPO_NAME", "v2rayAuto")

# Proxy settings
PROXY_ENABLED = os.environ.get("PROXY_ENABLED", "False").lower() == "true"
PROXY_SERVER = os.environ.get("PROXY_SERVER")
PROXY_PORT = os.environ.get("PROXY_PORT")
PROXY_USERNAME = os.environ.get("PROXY_USERNAME")
PROXY_PASSWORD = os.environ.get("PROXY_PASSWORD")

# Regex patterns
V2RAY_REGEX = r"(vless|vmess|trojan|ss|hy2)://[^\s]+"
VLESS_PATTERN = "vless://"
VMESS_PATTERN = "vmess://"
TROJAN_PATTERN = "trojan://"
SS_PATTERN = "ss://"
HY2_PATTERN = "hy2://"
PROFILE_TITLE_REGEX = r"#profile-title:\s*\[(.*?)\]"

def validate_config_link(link):
    """Basic validation - just ensure it starts with one of the protocols"""
    protocols = [VLESS_PATTERN, VMESS_PATTERN, TROJAN_PATTERN, SS_PATTERN, HY2_PATTERN]
    for protocol in protocols:
        if link.startswith(protocol) and len(link) > len(protocol) + 5:  # At least 5 chars more than protocol
            return True
    return False

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
        
        # Get the relative path for the raw link
        rel_path = os.path.relpath(output_filename, os.path.dirname(readme_path)).replace('\\', '/')
        
        # Create the raw GitHub link
        raw_link = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{REPO_NAME}/refs/heads/main/{rel_path}"
        
        # Check if Telegram Channels section exists
        telegram_section = "### Telegram Channels"
        if telegram_section not in content:
            print("Warning: Telegram Channels section not found in README.md")
            return False
        
        # Check if this channel already exists in the table
        channel_entry = f"[{channel_username}]({channel_url})"
        
        # Content for the new row
        row_content = f"| {channel_entry} | [vmess_vless_{num_links}]({raw_link}) |"
        
        # Update the README file with the new information
        lines = content.split("\n")
        updated_lines = []
        in_telegram_section = False
        table_header_found = False
        table_separator_found = False
        channel_found = False
        
        for line in lines:
            if telegram_section in line:
                in_telegram_section = True
                updated_lines.append(line)
                continue
            
            if in_telegram_section and line.strip().startswith("| Channel"):
                table_header_found = True
                updated_lines.append(line)
                continue
            
            if in_telegram_section and table_header_found and not table_separator_found:
                if line.strip().startswith("|---") or line.strip().startswith("| ---"):
                    table_separator_found = True
                    updated_lines.append("| ------------------------- | ------------------------------------------------------------ |")
                    continue
                else:
                    table_separator_found = True
                    updated_lines.append("| ------------------------- | ------------------------------------------------------------ |")
            
            if in_telegram_section and table_header_found and table_separator_found:
                if channel_entry in line and line.strip().startswith("|"):
                    updated_lines.append(row_content)
                    channel_found = True
                    continue
                elif not line.strip() or (line.strip() and not line.strip().startswith("|")):
                    if not channel_found:
                        updated_lines.append(row_content)
                        channel_found = True
                    updated_lines.append(line)
                    in_telegram_section = False
                    continue
            
            updated_lines.append(line)
        
        if in_telegram_section and table_header_found and table_separator_found and not channel_found:
            updated_lines.append(row_content)
        
        # Write the updated content back to the README
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(updated_lines))
        
        print(f"Updated README.md with subscription link for {channel_username}")
        return True
    
    except Exception as e:
        print(f"Error updating README.md: {e}")
        if VERBOSE:
            import traceback
            traceback.print_exc()
        return False

def extract_channels_from_profile_title(file_path):
    """Extract channel names from profile-title in the file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find profile-title line
        match = re.search(PROFILE_TITLE_REGEX, content)
        if match:
            channels_str = match.group(1)
            # Split by commas and clean up
            channels = [ch.strip() for ch in channels_str.split(',')]
            return channels
        return []
    except Exception as e:
        print(f"Error extracting channels from {file_path}: {e}")
        return []

def read_existing_configs(file_path):
    """Read existing V2Ray configs from a file"""
    configs = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if (line.startswith(VLESS_PATTERN) or line.startswith(VMESS_PATTERN) or 
                    line.startswith(TROJAN_PATTERN) or line.startswith(SS_PATTERN) or 
                    line.startswith(HY2_PATTERN)) and validate_config_link(line):
                    configs.add(line)
        return configs
    except Exception as e:
        print(f"Error reading configs from {file_path}: {e}")
        return set()

def get_metadata_from_file(file_path):
    """Extract metadata from subscription file"""
    metadata = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    metadata.append(line.rstrip('\n'))
                else:
                    break
        return metadata
    except Exception as e:
        print(f"Error extracting metadata from {file_path}: {e}")
        return []

async def fetch_configs_from_channel(client, channel_name, days=7):
    """Fetch V2Ray configs from a Telegram channel for the specified days"""
    configs = set()
    
    try:
        # Calculate cutoff date
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get channel entity
        print(f"Accessing channel: {channel_name}")
        entity = await client.get_entity(channel_name)
        
        # Iterate through messages
        print(f"Reading messages from {channel_name} (last {days} days)...")
        progress = tqdm(desc=f"Scanning {channel_name}", unit="msg", leave=False)
        
        async for message in client.iter_messages(entity, limit=None, reverse=False):
            # Check message date
            msg_date = message.date
            if msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=timezone.utc)
            
            # Stop if message is older than cutoff date
            if msg_date < cutoff_date:
                break
            
            progress.update(1)
            
            if message.message:
                # Use regex to find V2Ray links
                try:
                    full_matches = re.findall(V2RAY_REGEX, message.message)
                    for config in full_matches:
                        if validate_config_link(config) and config not in configs:
                            configs.add(config)
                except Exception as e:
                    if VERBOSE:
                        print(f"Error during regex matching in {channel_name}: {e}")
                
                # Backup method: String search with simplified extraction
                msg_text = message.message
                protocols = [VLESS_PATTERN, VMESS_PATTERN, TROJAN_PATTERN, SS_PATTERN, HY2_PATTERN]
                for protocol in protocols:
                    start_index = 0
                    while True:
                        start_index = msg_text.find(protocol, start_index)
                        if start_index == -1:
                            break
                        
                        # Find the end of the link at the first whitespace
                        end_index = len(msg_text)
                        for i in range(start_index, len(msg_text)):
                            if msg_text[i].isspace():
                                end_index = i
                                break
                        
                        # Extract the complete link up to whitespace
                        link = msg_text[start_index:end_index]
                        
                        # Basic validation and add if unique
                        if validate_config_link(link) and link not in configs:
                            configs.add(link)
                        
                        start_index = end_index + 1
        
        progress.close()
        print(f"Found {len(configs)} configs from {channel_name}")
        return configs
    
    except Exception as e:
        print(f"Error fetching configs from {channel_name}: {e}")
        if VERBOSE:
            import traceback
            traceback.print_exc()
        return set()

async def process_subscription_file(client, file_path, days=7):
    """Process a single subscription file"""
    print(f"\nProcessing file: {file_path}")
    
    # Extract channel names from profile-title
    channels = extract_channels_from_profile_title(file_path)
    if not channels:
        print(f"No channels found in {file_path}, skipping")
        return
    
    print(f"Found channels: {', '.join(channels)}")
    
    # Read existing configs
    existing_configs = read_existing_configs(file_path)
    print(f"Found {len(existing_configs)} existing configs")
    
    # Get metadata (comments, etc.)
    metadata = get_metadata_from_file(file_path)
    
    # Fetch new configs from each channel
    all_new_configs = set()
    for channel in channels:
        channel_configs = await fetch_configs_from_channel(client, channel, days)
        all_new_configs.update(channel_configs)
    
    # Combine existing and new configs
    combined_configs = existing_configs.union(all_new_configs)
    
    # Update file if new configs were found
    if len(combined_configs) > len(existing_configs):
        print(f"Adding {len(combined_configs) - len(existing_configs)} new configs to {file_path}")
        
        # Update subscription-userinfo with new timestamp if present
        updated_metadata = []
        for line in metadata:
            if line.startswith("#subscription-userinfo:"):
                current_time = int(datetime.now().timestamp())
                future_time = current_time + (365 * 10 * 24 * 60 * 60)  # 10 years in future
                updated_metadata.append(f"#subscription-userinfo: upload=0; download=0; total=10737418240000000; expire={future_time}")
            else:
                updated_metadata.append(line)
        
        # Write updated file
        with open(file_path, 'w', encoding='utf-8') as f:
            # Write metadata
            for line in updated_metadata:
                f.write(line + '\n')
            
            # Write all configs
            sorted_configs = sorted(list(combined_configs))
            for config in sorted_configs:
                f.write(config + '\n')
        
        # Update README if only one channel
        if len(channels) == 1:
            channel_name = channels[0]
            channel_url = f"https://t.me/{channel_name}"
            rel_path = os.path.relpath(file_path, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))).replace('\\', '/')
            update_readme(channel_name, channel_url, len(combined_configs), rel_path)
    else:
        print(f"No new configs found for {file_path}")

async def main():
    """Main function to scan directory and update subscription files"""
    # Get Telegram API credentials
    api_id_input = API_ID or input("Enter your API ID: ")
    api_hash_input = API_HASH or input("Enter your API Hash: ")
    phone_input = PHONE_NUMBER
    
    # Get number of days to fetch
    days_input = input("Enter the number of days of history to fetch (default: 7): ")
    try:
        days = int(days_input) if days_input.strip() else 7
        if days <= 0:
            print("Days must be greater than 0. Using default (7).")
            days = 7
    except ValueError:
        print("Invalid input. Using default (7 days).")
        days = 7
    
    print(f"Will fetch messages from the last {days} days.")
    
    # Path to telegram directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    telegram_dir = os.path.join(script_dir, '..', OUTPUT_DIR)
    
    if not os.path.exists(telegram_dir):
        print(f"Telegram directory not found: {telegram_dir}")
        return
    
    # Get session file path
    session_filepath = os.path.join(script_dir, '..', SESSION_FILE)
    
    # Try to load saved session string
    session_string_file = os.path.join(script_dir, '..', f"{SESSION_FILE}.string")
    session_string = None
    if os.path.exists(session_string_file):
        try:
            print("Found saved session string, attempting to use it...")
            with open(session_string_file, 'r') as f:
                session_string = f.read().strip()
        except Exception as e:
            print(f"Could not load saved session string: {e}")
    
    # Determine which session to use
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
                session_string = None
            await temp_client.disconnect()
        except Exception as e:
            print(f"Error validating session string: {e}. Falling back to session file/login.")
            session_string = None
        finally:
            if temp_client and temp_client.is_connected():
                await temp_client.disconnect()
    
    # Create client with appropriate session
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
            'session': session_filepath,
            'api_id': api_id_input,
            'api_hash': api_hash_input,
        }
    
    # Add proxy if enabled
    if PROXY_ENABLED and PROXY_SERVER and PROXY_PORT:
        print(f"Using proxy: {PROXY_SERVER}:{PROXY_PORT}")
        try:
            proxy_port_int = int(PROXY_PORT)
            proxy_info = ('socks5', PROXY_SERVER, proxy_port_int)
            if PROXY_USERNAME and PROXY_PASSWORD:
                client_kwargs['proxy'] = proxy_info + (True, PROXY_USERNAME, PROXY_PASSWORD)
            else:
                client_kwargs['proxy'] = proxy_info
        except ValueError:
            print(f"Error: Invalid PROXY_PORT '{PROXY_PORT}'. Must be an integer.")
            return
        except Exception as e:
            print(f"Error setting up proxy: {e}")
            return
    
    # Create the client
    client = TelegramClient(**client_kwargs)
    client.flood_sleep_threshold = 60
    
    try:
        print("Connecting to Telegram...")
        await client.connect()
        
        # Ensure authorization
        if not await client.is_user_authorized():
            print("Authorization required.")
            if not phone_input:
                print("Phone number not provided in .env")
                phone_input = input("Enter your phone number (with country code, e.g., +1234567890): ")
            
            try:
                await client.send_code_request(phone_input)
                while True:
                    code = input('Enter the code you received: ')
                    try:
                        await client.sign_in(phone_input, code)
                        break
                    except telethon.errors.SessionPasswordNeededError:
                        password = input('Two-step verification enabled. Please enter your password: ')
                        try:
                            await client.sign_in(password=password)
                            break
                        except Exception as pw_error:
                            print(f"Password sign-in failed: {pw_error}")
                            retry = input("Retry password? (y/n): ").lower()
                            if retry != 'y':
                                return
                    except telethon.errors.PhoneCodeInvalidError:
                        print("Invalid code. Please try again.")
                    except telethon.errors.PhoneCodeExpiredError:
                        print("Code expired. Requesting a new code...")
                        await client.send_code_request(phone_input)
                    except telethon.errors.FloodWaitError as flood_error:
                        print(f"Flood wait error: trying again in {flood_error.seconds} seconds.")
                        await asyncio.sleep(flood_error.seconds + 1)
                    except Exception as login_err:
                        print(f"Sign-in failed: {login_err}")
                        if client.is_connected():
                            await client.disconnect()
                        return
            
            except telethon.errors.FloodWaitError as flood_error:
                print(f"Flood wait error on sending code: trying again in {flood_error.seconds} seconds.")
                await asyncio.sleep(flood_error.seconds + 1)
                return
            except Exception as e:
                print(f"Authorization process failed: {e}")
                if client.is_connected():
                    await client.disconnect()
                return
        
        print("Successfully authorized and connected!")
        
        # Save session string if not already using one
        if not use_session_string:
            try:
                session_str = StringSession.save(client.session)
                with open(session_string_file, 'w') as f:
                    f.write(session_str)
                print(f"Session string saved for future use in {session_string_file}")
            except Exception as e:
                print(f"Could not save session string: {e}")
        
        # Scan telegram directory for subscription files
        subscription_files = []
        for filename in os.listdir(telegram_dir):
            file_path = os.path.join(telegram_dir, filename)
            if os.path.isfile(file_path):
                subscription_files.append(file_path)
        
        if not subscription_files:
            print(f"No subscription files found in {telegram_dir}")
            return
        
        print(f"Found {len(subscription_files)} subscription files to process")
        
        # Process each subscription file
        for file_path in subscription_files:
            await process_subscription_file(client, file_path, days)
        
        print("\nAll subscription files have been processed!")
    
    except telethon.errors.RPCError as rpc_error:
        print(f"Telegram RPC Error: {rpc_error}")
        if "FLOOD_WAIT" in str(rpc_error):
            wait_time = int(re.search(r'(\d+)', str(rpc_error)).group(1))
            print(f"Flood wait requested. Please wait {wait_time} seconds before trying again.")
    
    except Exception as e:
        print(f"Connection or setup error: {e}")
        if VERBOSE:
            import traceback
            traceback.print_exc()
    
    finally:
        # Disconnect from Telegram
        if 'client' in locals() and client.is_connected():
            await client.disconnect()
            print("Disconnected from Telegram.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Fatal error in script execution: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 