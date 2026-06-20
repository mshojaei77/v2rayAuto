import re
import os
import asyncio
import sys
import logging
import argparse
import tempfile
import platform
import base64
import hashlib
import contextlib
import ipaddress
import json
import threading
import time
import functools
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
try:
    import fcntl
except ImportError:
    fcntl = None  # Windows doesn't have fcntl
try:
    import msvcrt
    WINDOWS_LOCKING = True
except ImportError:
    WINDOWS_LOCKING = False
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple, Dict, Any
from urllib.parse import urlparse
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from tqdm import tqdm
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import PeerChannel, InputMessagesFilterEmpty, Channel
import telethon.utils
import telethon.errors
from telethon.sessions import StringSession

# Load environment variables from .env file first
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Custom exceptions for better error handling
class SecurityError(Exception):
    """Custom exception for security-related errors."""
    pass

class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass

class ConfigProcessingError(Exception):
    """Custom exception for configuration processing errors."""
    pass

# --- Secure Configuration Management ---

def get_required_env_var(var_name: str) -> str:
    """
    Securely retrieve required environment variable with validation.
    
    Args:
        var_name: Name of the environment variable
        
    Returns:
        The environment variable value
        
    Raises:
        SecurityError: If variable is not set or invalid
    """
    value = os.environ.get(var_name)
    if not value or not value.strip():
        raise SecurityError(
            f"Required environment variable '{var_name}' is not set. "
            f"Please set it in your .env file or environment."
        )
    
    # Additional validation for sensitive variables
    if var_name == "TELEGRAM_API_ID":
        try:
            api_id = int(value)
            if api_id <= 0:
                raise SecurityError("TELEGRAM_API_ID must be a positive integer")
            return str(api_id)
        except ValueError:
            raise SecurityError("TELEGRAM_API_ID must be a valid integer")
    
    if var_name == "TELEGRAM_API_HASH":
        if len(value) < 32:  # Telegram API hashes are typically 32 characters
            raise SecurityError("TELEGRAM_API_HASH appears to be invalid (too short)")
        if not re.match(r'^[a-f0-9]+$', value):
            raise SecurityError("TELEGRAM_API_HASH must contain only hexadecimal characters")
    
    return value.strip()

def collect_credentials_securely(prompt: str = "", is_password: bool = False) -> str:
    """Prompt for a single credential securely.
    If is_password is True, use getpass to hide input; otherwise use input.
    """
    import getpass
    if is_password:
        return getpass.getpass(prompt)
    else:
        return input(prompt)

def secure_input_credentials() -> Tuple[str, str]:
    """
    Securely prompt for credentials using getpass to prevent exposure.
    
    Returns:
        Tuple of (phone_number, password) if 2FA is enabled
        
    Raises:
        SecurityError: If input validation fails
    """
    try:
        phone = input("Enter your phone number (with country code, e.g., +1234567890): ").strip()
        
        # Validate phone number format
        if not re.match(r'^\+\d{10,15}$', phone):
            raise SecurityError("Invalid phone number format. Use +countrycode followed by number")
        
        # Check if 2FA password is needed (we'll handle this during authentication)
        return phone, ""
        
    except KeyboardInterrupt:
        raise SecurityError("Authentication cancelled by user")
    except Exception as e:
        raise SecurityError(f"Failed to collect credentials securely: {e}")

@contextlib.contextmanager
def secure_file_lock(file_path: str):
    """Cross-platform file locking context manager."""
    lock_file_path = f"{file_path}.lock"
    
    try:
        # Create lock file
        lock_file = open(lock_file_path, 'w')
        
        try:
            if platform.system() != 'Windows':
                # Unix-like systems: use fcntl
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            else:
                # Windows: use msvcrt (import at runtime to avoid issues on non-Windows)
                import msvcrt
                while True:
                    try:
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except IOError:
                        time.sleep(0.1)
            
            yield
            
        finally:
            if platform.system() != 'Windows':
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            else:
                import msvcrt
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            
            lock_file.close()
            
    finally:
        # Clean up lock file
        try:
            os.remove(lock_file_path)
        except (OSError, FileNotFoundError):
            pass

def derive_encryption_key(password: bytes, salt: bytes) -> bytes:
    """Derive encryption key from password using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password))

def sanitize_v2ray_input(config: str) -> bool:
    """
    Sanitize V2Ray configuration input to prevent injection attacks.
    
    Args:
        config: Configuration string to validate
        
    Returns:
        True if input is safe, False otherwise
    """
    # Check for malicious patterns
    malicious_patterns = [
        r'javascript:',
        r'data:',
        r'file:',
        r'ftp:',
        r'<script',
        r'</script>',
        r'eval\(',
        r'exec\(',
        r'system\(',
        r'shell_exec\(',
        r'passthru\(',
        r'`.*`',  # Command substitution
        r'\$\(',  # Command substitution
        r'&&',    # Command chaining
        r'\|\|',  # Command chaining
        r';',     # Command separator (in suspicious contexts)
        r'\x00',  # Null bytes
        r'\.\./',  # Directory traversal
        r'\\\\',   # Windows path traversal
    ]
    
    config_lower = config.lower()
    for pattern in malicious_patterns:
        if re.search(pattern, config_lower, re.IGNORECASE):
            logger.warning(f"Malicious pattern detected: {pattern}")
            return False
    
    # Check for excessive length (potential DoS)
    if len(config) > 8192:  # 8KB limit
        logger.warning("Configuration exceeds maximum length")
        return False
    
    # Check for valid UTF-8 encoding
    try:
        config.encode('utf-8').decode('utf-8')
    except UnicodeError:
        logger.warning("Invalid UTF-8 encoding detected")
        return False
    
    return True

def validate_network_address(hostname: str) -> bool:
    """
    Validate network address (hostname or IP).
    
    Args:
        hostname: Hostname or IP address to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not hostname:
        return False
    
    try:
        # Try to parse as IP address
        ip = ipaddress.ip_address(hostname)
        
        # Block private/reserved IP ranges for security
        if ip.is_private or ip.is_reserved or ip.is_loopback:
            logger.warning(f"Blocked private/reserved IP: {hostname}")
            return False
        
        # Block multicast and link-local
        if ip.is_multicast or ip.is_link_local:
            logger.warning(f"Blocked multicast/link-local IP: {hostname}")
            return False
        
        return True
        
    except ValueError:
        # Not an IP, validate as hostname
        return validate_hostname(hostname)

def validate_hostname(hostname: str) -> bool:
    """
    Validate hostname according to RFC standards.
    
    Args:
        hostname: Hostname to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not hostname or len(hostname) > 253:
        return False
    
    # Check for valid hostname pattern
    hostname_pattern = re.compile(
        r'^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$'
    )
    
    if not hostname_pattern.match(hostname):
        return False
    
    # Additional security checks
    if '..' in hostname or hostname.startswith('.') or hostname.endswith('.'):
        return False
    
    return True

def validate_port_number(port: int) -> bool:
    """
    Validate port number.
    
    Args:
        port: Port number to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Valid port range: 1-65535
    # Block well-known system ports for security
    if not isinstance(port, int) or port < 1 or port > 65535:
        return False
    
    # Block some sensitive ports
    # blocked_ports = {22, 23, 25, 53, 80, 110, 143, 443, 993, 995}
    # if port in blocked_ports:
    #    logger.warning(f"Blocked sensitive port: {port}")
    #    return False
    
    return True

def validate_scheme_specific(parsed_url) -> bool:
    """
    Perform scheme-specific validation.
    
    Args:
        parsed_url: Parsed URL object
        
    Returns:
        True if valid, False otherwise
    """
    scheme = parsed_url.scheme.lower()
    
    if scheme in {'vmess', 'vless'}:
        # These should have proper base64 encoding or query parameters
        if not (parsed_url.query or '@' in parsed_url.netloc):
            return False
        
        # Validate base64 content if present
        if parsed_url.path and len(parsed_url.path) > 1:
            try:
                # Try to decode base64 path
                decoded = base64.b64decode(parsed_url.path[1:] + '==')
                # Check if it's valid JSON for vmess
                if scheme == 'vmess':
                    json.loads(decoded.decode('utf-8'))
            except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
                return False
    
    elif scheme == 'trojan':
        # Trojan should have password and host
        if '@' not in parsed_url.netloc:
            return False
        
        password_part = parsed_url.netloc.split('@')[0]
        if not password_part or len(password_part) < 8:
            return False
    
    elif scheme == 'ss':
        # Shadowsocks validation
        if '@' not in parsed_url.netloc:
            return False
        
        # Check for method and password encoding
        auth_part = parsed_url.netloc.split('@')[0]
        try:
            base64.b64decode(auth_part + '==')
        except ValueError:
            return False
    
    return True

def perform_security_checks(config: str, parsed_url) -> bool:
    """
    Perform additional security checks on configuration.
    
    Args:
        config: Original configuration string
        parsed_url: Parsed URL object
        
    Returns:
        True if secure, False otherwise
    """
    # Check for suspicious query parameters
    if parsed_url.query:
        query_params = parsed_url.query.lower()
        suspicious_params = ['exec', 'eval', 'system', 'shell', 'cmd']
        for param in suspicious_params:
            if param in query_params:
                logger.warning(f"Suspicious query parameter: {param}")
                return False
    
    # Check for excessive nesting or complexity
    if config.count('://') > 1:
        logger.warning("Multiple protocols detected")
        return False
    
    # Check for URL encoding attacks
    if '%' in config:
        try:
            from urllib.parse import unquote
            decoded = unquote(config)
            if decoded != config and not sanitize_v2ray_input(decoded):
                logger.warning("URL encoding attack detected")
                return False
        except Exception:
            return False
    
    return True

# --- Concurrency Control ---

class AtomicFileWriter:
    """Context manager for atomic file writing operations."""
    
    def __init__(self, file_path: str, encoding: str = 'utf-8'):
        """
        Initialize atomic file writer.
        
        Args:
            file_path: Target file path
            encoding: File encoding
        """
        self.file_path = Path(file_path)
        self.temp_path = self.file_path.with_suffix(self.file_path.suffix + '.tmp')
        self.encoding = encoding
        self.file_handle = None
        
    def __enter__(self):
        """Enter context and return file handle."""
        try:
            # Ensure parent directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Open temporary file for writing
            self.file_handle = open(self.temp_path, 'w', encoding=self.encoding)
            return self.file_handle
            
        except Exception as e:
            logger.error(f"Failed to open temporary file {self.temp_path}: {e}")
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and commit or rollback changes."""
        if self.file_handle:
            self.file_handle.close()
        
        if exc_type is None:
            # Success: atomically move temp file to target
            try:
                if platform.system() == 'Windows':
                    # Windows requires removing target first
                    if self.file_path.exists():
                        self.file_path.unlink()
                
                self.temp_path.replace(self.file_path)
                logger.debug(f"Atomically wrote file: {self.file_path}")
                
            except Exception as e:
                logger.error(f"Failed to commit atomic write: {e}")
                # Clean up temp file
                if self.temp_path.exists():
                    self.temp_path.unlink()
                raise
        else:
            # Error: clean up temp file
            if self.temp_path.exists():
                self.temp_path.unlink()
                logger.debug(f"Cleaned up temporary file: {self.temp_path}")

class ConcurrencyManager:
    """Manage concurrent access to shared resources."""
    
    def __init__(self):
        """Initialize concurrency manager."""
        self._locks = {}
        self._lock_manager_lock = threading.Lock()
    
    def get_file_lock(self, file_path: str) -> threading.Lock:
        """
        Get or create a lock for a specific file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Thread lock for the file
        """
        normalized_path = str(Path(file_path).resolve())
        
        with self._lock_manager_lock:
            if normalized_path not in self._locks:
                self._locks[normalized_path] = threading.Lock()
            return self._locks[normalized_path]
    
    @contextlib.contextmanager
    def acquire_file_lock(self, file_path: str, timeout: float = 30.0):
        """
        Acquire a file lock with timeout.
        
        Args:
            file_path: Path to the file
            timeout: Lock acquisition timeout in seconds
            
        Yields:
            None when lock is acquired
            
        Raises:
            TimeoutError: If lock cannot be acquired within timeout
        """
        file_lock = self.get_file_lock(file_path)
        
        if file_lock.acquire(timeout=timeout):
            try:
                yield
            finally:
                file_lock.release()
        else:
            raise TimeoutError(f"Could not acquire lock for {file_path} within {timeout} seconds")

# Global concurrency manager instance
_concurrency_manager = ConcurrencyManager()

def atomic_file_write(file_path: str, content: str, encoding: str = 'utf-8') -> None:
    """
    Write content to file atomically with concurrency control.
    
    Args:
        file_path: Target file path
        content: Content to write
        encoding: File encoding
        
    Raises:
        SecurityError: If path validation fails
        TimeoutError: If file lock cannot be acquired
        IOError: If file operation fails
    """
    # Validate path security
    secure_path_validation(file_path)
    
    # Acquire file lock and write atomically
    with _concurrency_manager.acquire_file_lock(file_path):
        with AtomicFileWriter(file_path, encoding) as f:
            f.write(content)

def atomic_file_read(file_path: str, encoding: str = 'utf-8') -> str:
    """
    Read file content with concurrency control.
    
    Args:
        file_path: Source file path
        encoding: File encoding
        
    Returns:
        File content
        
    Raises:
        SecurityError: If path validation fails
        TimeoutError: If file lock cannot be acquired
        IOError: If file operation fails
    """
    # Validate path security
    secure_path_validation(file_path)
    
    # Acquire file lock and read
    with _concurrency_manager.acquire_file_lock(file_path):
        return secure_file_read(file_path, encoding)

class RateLimiter:
    """Rate limiter for API calls and network operations."""
    
    def __init__(self, max_calls: int, time_window: float):
        """
        Initialize rate limiter.
        
        Args:
            max_calls: Maximum number of calls allowed
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
        self.lock = threading.Lock()
    
    def acquire(self, timeout: float = None) -> bool:
        """
        Acquire permission to make a call.
        
        Args:
            timeout: Maximum time to wait for permission
            
        Returns:
            True if permission granted, False if timeout
        """
        start_time = time.time()
        
        while True:
            with self.lock:
                now = time.time()
                
                # Remove old calls outside the time window
                self.calls = [call_time for call_time in self.calls 
                             if now - call_time < self.time_window]
                
                # Check if we can make a new call
                if len(self.calls) < self.max_calls:
                    self.calls.append(now)
                    return True
            
            # Check timeout
            if timeout is not None and time.time() - start_time > timeout:
                return False
            
            # Wait a bit before retrying
            time.sleep(0.1)
    
    @contextlib.contextmanager
    def limit(self, timeout: float = None):
        """
        Context manager for rate limiting.
        
        Args:
            timeout: Maximum time to wait for permission
            
        Yields:
            None when permission is granted
            
        Raises:
            TimeoutError: If permission cannot be acquired within timeout
        """
        if self.acquire(timeout):
            yield
        else:
            raise TimeoutError(f"Rate limit exceeded, could not acquire permission within {timeout} seconds")

# Global rate limiter for Telegram API calls
_telegram_rate_limiter = RateLimiter(max_calls=20, time_window=60.0)  # 20 calls per minute

def with_telegram_rate_limit(func):
    """Decorator to apply rate limiting to Telegram API calls."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        with _telegram_rate_limiter.limit(timeout=30.0):
            return await func(*args, **kwargs)
    return wrapper

# --- Configuration ---
try:
    API_ID = int(get_required_env_var("TELEGRAM_API_ID"))
    API_HASH = get_required_env_var("TELEGRAM_API_HASH")
except SecurityError as e:
    logger.error(f"Configuration error: {e}")
    sys.exit(1)

PHONE_NUMBER = os.environ.get("TELEGRAM_PHONE_NUMBER")  # Optional, if using user account
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

# Unified V2Ray pattern - more robust and comprehensive
V2RAY_PATTERN = re.compile(
    r'(?:vless|vmess|trojan|ss|ssr|hysteria|tuic|wireguard|hy2)://[^\s\n\r<>"\'\[\]{}|\\^`]+',
    re.IGNORECASE | re.MULTILINE
)

# List of popular telegram channels for V2Ray configs
POPULAR_CHANNELS = [
    "SOSkeyNET",
    "Spotify_Porteghali",
    "appsooner",
    "Golestan_VPN",
    "mitivpn",
    "FREE2CONFIG",
    "DeamNet_proxy",
    "PinkOrca",
    "Avkeys",
    "AR14N24B",
    "SOSkeyNET",
    "sudoflux",
    "xixv2ray",
    "malvpn1",
    "v2ray_tz",
    "v2rayenglish",
    "sogoandfuckyourlove",
    "vpnbaz",
    "meli_proxyy",
    "An0nymousTeam",
    "Outlinev2rayNG", 
    "redfree8",
    "UnlimitedDev",
    "appsooner",
    "proxy_kafee",
    "sinavm",
    "Artemisvpn1",
    "Porteqal3",
    "V2ray_Collector",
    "VIProxys",
    "prrofile_purple",
    "Fr33C0nfig",
    "Ln2ray",
    "lyravpn",
    "v2ray_free0",
    "vlesskeys",
    "V2RayRootFree",
    "VIVA_Proxy",
    "VPN_SOLVE",
    "CyberNigga2",
    "Prooofsor",
    "VoxSafe",
    "hormozvpn",
    "FREECONFIGSPLUS",
    "Spotify_Porteghali",
    "anty_filter",
    "proxylabra",
    "FireVPNTeam1",
    "NamiraNet",
    "gift_bazi_chanel",
    "hajmvpn",
    "Go_vpns",
    "Rayan_Config",
    "joinnasnet",
    "V2raybazi",
    "unlocked_worlld",
    "AzadNet",
    "godot404",
    "free_intnet",
    "mahsa_net",
    "NorthXRAY",
    "VPN_KING_V2RAY",
    "ghalagyann",
    "allworldcfg",
    "V2SayFree",
    "DarkVPNpro",
    "Khosrow_vpn",
    "Fserverd_vpn",
    "HerofVPN",
    "neteiran",
    "xsvpn_ch",
    "vpnjey",
    "safeNet4All",
    "Lx3vpn",
    "GetBreakNet",
    "V2rayAG",
    "powercodes",
    "V2ray_tci",
    "BESTIIVPN",
    "habsiop",
    "thunder_speed",
    "Freedom_Guard_Net",
    "FreeVPNHomes",
    "ElmmiumChannel",
    "Apk_Bad",
    "orange_vpns",
    "NoForcedHeaven",
    "golestan_vpn",
    "v2raygame",
    "oxnet_ir",
    "maxvpnxx",
    "soskeynet",
    "blackray",
    "clynoid",
    "YamYamProxy"
]

def validate_channel_name(channel: str) -> str:
    """
    Validate and sanitize channel name for security.
    
    Args:
        channel: Raw channel name input
        
    Returns:
        Sanitized channel name
        
    Raises:
        ValidationError: If channel name is invalid
    """
    if not channel or not isinstance(channel, str):
        raise ValidationError("Channel name cannot be empty")
    
    # Remove @ prefix and whitespace
    channel = channel.strip().lstrip('@')
    
    # Validate length
    if len(channel) < 3 or len(channel) > 32:
        raise ValidationError("Channel name must be between 3 and 32 characters")
    
    # Validate characters (alphanumeric, underscore, hyphen, dot only)
    if not re.match(r'^[a-zA-Z0-9_.-]+$', channel):
        raise ValidationError("Channel name contains invalid characters")
    
    return channel

def secure_path_validation(file_path: str, base_directory: str = None) -> Path:
    """Validate and sanitize file paths to prevent directory traversal attacks.
    
    Args:
        file_path: The file path to validate
        base_directory: Optional base directory to restrict access to
        
    Returns:
        Validated Path object
        
    Raises:
        ValidationError: If path is invalid or contains traversal attempts
    """
    try:
        # Convert to Path object and resolve
        path = Path(file_path).resolve()
        
        # Check for null bytes and other dangerous characters
        if '\x00' in str(path) or any(char in str(path) for char in ['<', '>', '|', '*', '?']):
            raise ValidationError(f"Invalid characters in path: {file_path}")
        
        # If base directory is specified, ensure path is within it
        if base_directory:
            base_path = Path(base_directory).resolve()
            try:
                path.relative_to(base_path)
            except ValueError:
                raise ValidationError(f"Path outside allowed directory: {file_path}")
        
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        return path
        
    except (OSError, ValueError) as e:
        raise ValidationError(f"Invalid file path: {file_path} - {str(e)}")


def secure_file_write(file_path: str, content: str, encoding: str = 'utf-8', 
                     base_directory: str = None) -> None:
    """Securely write content to a file with path validation.
    
    Args:
        file_path: Path to the file
        content: Content to write
        encoding: File encoding
        base_directory: Optional base directory restriction
        
    Raises:
        ValidationError: If path validation fails
        IOError: If file operations fail
    """
    validated_path = secure_path_validation(file_path, base_directory)
    
    # Use atomic write operation
    temp_path = validated_path.with_suffix(validated_path.suffix + '.tmp')
    
    try:
        with secure_file_lock(str(validated_path)):
            with open(temp_path, 'w', encoding=encoding) as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
            
            # Atomic move
            if os.name == 'nt':  # Windows
                if validated_path.exists():
                    validated_path.unlink()
            temp_path.replace(validated_path)
            
    except Exception as e:
        # Clean up temp file on error
        if temp_path.exists():
            temp_path.unlink()
        raise IOError(f"Failed to write file {file_path}: {str(e)}")


def secure_file_read(file_path: str, encoding: str = 'utf-8', 
                    base_directory: str = None) -> str:
    """Securely read content from a file with path validation.
    
    Args:
        file_path: Path to the file
        encoding: File encoding
        base_directory: Optional base directory restriction
        
    Returns:
        File content as string
        
    Raises:
        ValidationError: If path validation fails
        IOError: If file operations fail
    """
    validated_path = secure_path_validation(file_path, base_directory)
    
    if not validated_path.exists():
        raise IOError(f"File does not exist: {file_path}")
    
    try:
        with open(validated_path, 'r', encoding=encoding) as f:
            return f.read()
    except Exception as e:
        raise IOError(f"Failed to read file {file_path}: {str(e)}")



def encrypt_session_data(session_string: str, password: str) -> str:
    """Encrypt session string with password-derived key."""
    try:
        # Generate salt for key derivation
        salt = os.urandom(16)
        
        # Derive key from password
        key = derive_encryption_key(password.encode(), salt)
        fernet = Fernet(key)
        
        # Encrypt session string
        encrypted_data = fernet.encrypt(session_string.encode())
        
        # Combine salt and encrypted data
        combined_data = salt + encrypted_data
        return base64.b64encode(combined_data).decode()
    except Exception as e:
        raise SecurityError(f"Failed to encrypt session data: {e}")

def decrypt_session_data(encrypted_data: str, password: str) -> str:
    """Decrypt session string with password-derived key."""
    try:
        # Decode base64 data
        combined_data = base64.b64decode(encrypted_data.encode())
        
        # Extract salt and encrypted data
        salt = combined_data[:16]
        encrypted_bytes = combined_data[16:]
        
        # Derive key from password
        key = derive_encryption_key(password.encode(), salt)
        fernet = Fernet(key)
        
        # Decrypt session string
        decrypted_data = fernet.decrypt(encrypted_bytes)
        return decrypted_data.decode()
    except Exception as e:
        raise SecurityError(f"Failed to decrypt session data: {e}")

def secure_session_storage(session_file_path: str, session_string: str = None, password: str = None) -> Optional[str]:
    """Securely store or retrieve encrypted session data."""
    try:
        # Validate session file path
        session_dir = os.path.dirname(session_file_path) or '.'
        validated_path = secure_path_validation(session_file_path, session_dir)
        
        if session_string and password:
            # Store encrypted session
            encrypted_data = encrypt_session_data(session_string, password)
            
            with secure_file_lock(str(validated_path)):
                secure_file_write(str(validated_path), encrypted_data)
            
            # Set restrictive file permissions (owner read/write only)
            try:
                os.chmod(validated_path, 0o600)
            except (OSError, AttributeError):
                # Windows doesn't support chmod, use alternative method
                pass
            
            logger.info("Session data securely stored")
            return None
            
        elif password:
            # Retrieve and decrypt session
            if not os.path.exists(validated_path):
                return None
                
            with secure_file_lock(str(validated_path)):
                encrypted_data = secure_file_read(str(validated_path))
            
            return decrypt_session_data(encrypted_data, password)
            
        else:
            raise ValidationError("Password required for session operations")
            
    except Exception as e:
        logger.error(f"Session storage error: {e}")
        return None

def validate_v2ray_config(config: str) -> bool:
    """
    Validate V2Ray configuration string with comprehensive security checks.
    
    Args:
        config: V2Ray configuration string
        
    Returns:
        True if valid, False otherwise
        
    Raises:
        SecurityError: If malicious content is detected
    """
    if not config or not isinstance(config, str):
        return False
    
    # Input sanitization - check for malicious patterns
    if not sanitize_v2ray_input(config):
        return False
    
    try:
        # Parse URL to validate structure
        parsed = urlparse(config)
        
        # Check if scheme is supported
        supported_schemes = {'vless', 'vmess', 'trojan', 'ss', 'ssr', 'hysteria', 'tuic', 'wireguard', 'hy2'}
        if parsed.scheme.lower() not in supported_schemes:
            return False
        
        # Basic structure validation
        if not parsed.netloc:
            return False
        
        # Validate hostname/IP
        if not validate_network_address(parsed.hostname):
            return False
        
        # Validate port if present
        if parsed.port and not validate_port_number(parsed.port):
            return False
        
        # Scheme-specific validation
        if not validate_scheme_specific(parsed):
            return False
        
        # Additional security checks
        if not perform_security_checks(config, parsed):
            return False
        
        return True
        
    except Exception as e:
        logger.warning(f"Configuration validation error: {e}")
        return False

def extract_v2ray_configs(text: str) -> List[str]:
    """
    Extract and validate V2Ray configurations from text using unified approach.
    
    Args:
        text: Text to extract configurations from
        
    Returns:
        List of valid V2Ray configuration strings
    """
    if not text:
        return []
    
    # Use unified regex pattern
    matches = V2RAY_PATTERN.findall(text)
    
    # Validate each match
    valid_configs = []
    for match in matches:
        if validate_v2ray_config(match.strip()):
            valid_configs.append(match.strip())
    
    return valid_configs

@asynccontextmanager
async def file_lock(file_path: str):
    """
    Context manager for file locking to prevent race conditions.
    
    Args:
        file_path: Path to file to lock
    """
    lock_file = f"{file_path}.lock"
    lock_fd = None
    
    try:
        # Create lock file
        lock_fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        yield
    except OSError as e:
        if e.errno == 17:  # File exists
            raise ConfigProcessingError(f"Another process is updating {file_path}")
        raise
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
            try:
                os.unlink(lock_file)
            except OSError:
                pass

def split_configs_into_chunks(configs: List[str], chunk_size: int = 500) -> List[List[str]]:
    """
    Split configurations into chunks of specified size.
    
    Args:
        configs: List of configuration strings
        chunk_size: Maximum number of configs per chunk
        
    Returns:
        List of configuration chunks
    """
    if chunk_size <= 0:
        raise ValidationError("Chunk size must be positive")
    
    return [configs[i:i + chunk_size] for i in range(0, len(configs), chunk_size)]

def validate_chunks(chunks: List[List[str]], original_configs: List[str]) -> bool:
    """Validate that chunks contain unique configs without duplication"""
    print(f"Validating {len(chunks)} chunks...")
    
    # Collect all configs from chunks
    all_chunk_configs = []
    for i, chunk in enumerate(chunks, 1):
        print(f"  Chunk {i}: {len(chunk)} configs")
        all_chunk_configs.extend(chunk)
    
    # Check for duplicates within chunks
    unique_chunk_configs = set(all_chunk_configs)
    total_chunk_configs = len(all_chunk_configs)
    unique_count = len(unique_chunk_configs)
    
    print(f"  Total configs in chunks: {total_chunk_configs}")
    print(f"  Unique configs in chunks: {unique_count}")
    print(f"  Original configs count: {len(original_configs)}")
    
    if total_chunk_configs != unique_count:
        print(f"  ⚠️  WARNING: Found {total_chunk_configs - unique_count} duplicate configs across chunks!")
        return False
    
    if unique_count != len(original_configs):
        print(f"  ⚠️  WARNING: Chunk configs count ({unique_count}) doesn't match original ({len(original_configs)})!")
        return False
    
    print("  ✅ Chunk validation passed - no duplicates detected")
    return True

def save_config_file(filename, configs, profile_title):
    """Save configs to a file with metadata using atomic operations."""
    current_time = int(datetime.now().timestamp())
    future_time = current_time + (365 * 10 * 24 * 60 * 60)  # 10 years in future
    
    # Create content with metadata
    content_lines = [
        f"#profile-title: {profile_title}",
        "#profile-update-interval: 7",
        f"#subscription-userinfo: upload=0; download=0; total=10737418240000000; expire={future_time}",
        ""  # Empty line after metadata
    ]
    
    # Add all configs
    for config in tqdm(configs, desc="Writing configs", unit="link", leave=False):
        content_lines.append(config)
    
    # Use atomic file write for enhanced concurrency control
    content = '\n'.join(content_lines)
    atomic_file_write(filename, content)

def update_readme(channel_username, channel_url, num_links, output_filename, config_set=None, contributing_channels=None):
    """Update the README.md file with the subscription link"""
    readme_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.md")
    
    if not os.path.exists(readme_path):
        print(f"Warning: README.md not found at {readme_path}")
        return False
    
    try:
        # Validate and read the current README content securely
        readme_path = secure_path_validation(readme_path, os.path.dirname(readme_path))
        content = secure_file_read(readme_path)
        
        # Get the relative path for the raw link (convert backslashes to forward slashes for GitHub)
        rel_path = os.path.relpath(output_filename, os.path.dirname(readme_path)).replace('\\\\', '/')
        rel_path = rel_path.replace('\\', '/') # Ensure all backslashes are converted to forward slashes
        
        # Create the raw GitHub link
        raw_link = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{REPO_NAME}/refs/heads/main/{rel_path}"
        
        # Check if Telegram Channels section exists
        telegram_section = "## Telegram Channels"
        if telegram_section not in content:
            print(f"Warning: Telegram Channels section not found in README.md. Looking for: '{telegram_section}'")
            return False
        
        # Handle channel_entry differently based on whether it already has links
        # If channel_username contains markdown links [name](url), use it directly
        if "[" in channel_username and "](http" in channel_username:
            channel_entry = channel_username  # Already formatted with links
        else:
            # Otherwise create a link if URL is provided
            channel_entry = f"[{channel_username}]({channel_url})" if channel_url else channel_username
        
        # Content for the new row - proper table format with pipes and spacing
        # Define a more descriptive link text based on protocols found
        found_protocols = []
        if config_set:
            if any(link.startswith("vmess://") for link in config_set):
                found_protocols.append("vmess")
            if any(link.startswith("vless://") for link in config_set):
                found_protocols.append("vless")
            if any(link.startswith("trojan://") for link in config_set):
                found_protocols.append("trojan")
            if any(link.startswith("ss://") for link in config_set):
                found_protocols.append("ss")
            if any(link.startswith("hy2://") for link in config_set):
                found_protocols.append("hy2")
        
        # Combine protocols in the link text
        protocols_text = "_".join(found_protocols) if found_protocols else "configs"
        
        # Add contributing channels info if available
        channels_info = ""
        if contributing_channels and len(contributing_channels) > 1:
            # Show first few channels and total count if many channels
            if len(contributing_channels) <= 5:
                channels_info = f" <br/>*From: {', '.join(contributing_channels)}*"
            else:
                first_channels = ', '.join(contributing_channels[:3])
                channels_info = f" <br/>*From: {first_channels} +{len(contributing_channels)-3} more*"
        elif contributing_channels and len(contributing_channels) == 1:
            # For single channel, don't add redundant info if channel_entry already shows it
            if contributing_channels[0] not in str(channel_entry):
                channels_info = f" <br/>*From: {contributing_channels[0]}*"
        
        row_content = f"| {channel_entry} | [{protocols_text}_{num_links}]({raw_link}){channels_info} |"
        
        print(f"DEBUG: Preparing to update README with: {row_content}")
        
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
                print("DEBUG: Found Telegram Channels section")
                updated_lines.append(line)
                continue
            
            # If we're in the section and find a line starting with "| Channel", it's the table header
            if in_telegram_section and line.strip().startswith("| Channel"):
                table_header_found = True
                print("DEBUG: Found table header row")
                updated_lines.append(line)
                continue
            
            # After finding the header, look for the separator row (containing "|-")
            if in_telegram_section and table_header_found and not table_separator_found:
                if line.strip().startswith("|---") or line.strip().startswith("| ---"):
                    table_separator_found = True
                    print("DEBUG: Found table separator row")
                    updated_lines.append("| ------------------------- | ------------------------------------------------------------ |")
                    continue
                else:
                    # If header found but no separator, add one robustly
                    table_separator_found = True
                    print("DEBUG: No separator found, adding one")
                    updated_lines.append("| ------------------------- | ------------------------------------------------------------ |")
                    # Continue processing the current line after adding the separator
                    # Fall through to the next block to check if this line is the target channel
            
            # Now we're in the table body, check for existing entries
            if in_telegram_section and table_header_found and table_separator_found:
                # If we find a line with our channel entry, replace it
                if channel_entry in line and line.strip().startswith("|"):
                    print(f"DEBUG: Found and replacing existing channel: {line}")
                    updated_lines.append(row_content)
                    channel_found = True
                    continue
                # If line is empty or starts a new section, exit the table search
                elif not line.strip() or (line.strip() and not line.strip().startswith("|")):
                    # If we haven't found and replaced our channel yet, add it before exiting the section
                    if not channel_found:
                        # Insert the new row just before the line that breaks the table format
                        print(f"DEBUG: Adding new channel before leaving table: {row_content}")
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
            print(f"DEBUG: Adding new channel at end of file: {row_content}")
            updated_lines.append(row_content)
        
        # Write the updated content back to the README securely
        updated_content = "\n".join(updated_lines)
        secure_file_write(readme_path, updated_content)
        
        print(f"Updated README.md with new subscription link for {channel_username}")
        return True
    
    except Exception as e:
        print(f"Error updating README.md: {e}")
        if VERBOSE:
            import traceback
            traceback.print_exc()
        return False

def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and configure the command-line argument parser.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="Telegram V2Ray Configuration Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use popular channels with default settings
  python telgram2sub.py --popular
  
  # Scrape specific channels
  python telgram2sub.py --channels Spdnetpro,meli_proxyy --limit 100
  
  # Enable chunking for large outputs
  python telgram2sub.py --popular --chunking --limit 200
  
  # Verbose mode with custom channels
  python telgram2sub.py --channels "t.me/Spdnetpro,@meli_proxyy" --verbose
        """
    )
    
    # Channel selection (mutually exclusive)
    channel_group = parser.add_mutually_exclusive_group(required=False)
    channel_group.add_argument(
        '--popular', '-p',
        action='store_true',
        help='Use predefined list of popular Telegram channels'
    )
    channel_group.add_argument(
        '--channels', '-c',
        type=str,
        help='Comma-separated list of custom channel usernames (e.g., "Spdnetpro,meli_proxyy")'
    )
    
    # Optional arguments
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=100,
        metavar='N',
        help='Maximum number of messages to process per channel (default: 100, max: 10000)'
    )
    
    parser.add_argument(
        '--chunking', '-k',
        action='store_true',
        help='Enable chunking for large outputs (splits into multiple files)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging output'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        default=OUTPUT_DIR,
        metavar='DIR',
        help=f'Output directory for saved configurations (default: {OUTPUT_DIR})'
    )
    
    return parser


def parse_and_validate_arguments() -> Tuple[List[str], int, bool]:
    """
    Parse command-line arguments and validate them.
    If no arguments are provided, defaults to --popular with limit=100 and chunking=False.
    
    Returns:
        Tuple of (channels, history_limit, enable_chunking)
    """
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Set verbose mode globally
    global VERBOSE
    if args.verbose:
        VERBOSE = True
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")
    
    # Check if no arguments were provided (only script name)
    default_mode = False
    if len(sys.argv) == 1:
        default_mode = True
        logger.info("No arguments provided, running in default mode (popular channels, limit=100, chunking disabled)")
    
    # Determine channels based on arguments or default mode
    if default_mode or args.popular:
        channels = POPULAR_CHANNELS.copy()
        logger.info(f"Selected {len(channels)} popular channels")
    elif args.channels:
        # Parse custom channels
        raw_channels = [ch.strip() for ch in args.channels.split(',')]
        channels = []
        
        for channel in raw_channels:
            if not channel:
                continue
            try:
                # Extract clean username from various formats
                clean_name = channel
                if "t.me/" in channel:
                    clean_name = channel.split("t.me/")[-1].split("/")[0]
                elif channel.startswith('@'):
                    clean_name = channel[1:]
                
                validated_channel = validate_channel_name(clean_name)
                channels.append(validated_channel)
            except ValidationError as e:
                logger.warning(f"Skipping invalid channel '{channel}': {e}")
        
        if not channels:
            raise ValidationError("No valid channels provided")
        
        logger.info(f"Selected {len(channels)} custom channels: {', '.join(channels)}")
    else:
        # This case should not happen because if neither popular nor channels, default_mode would be True.
        # But for safety, fallback to popular.
        channels = POPULAR_CHANNELS.copy()
        logger.info("No channel selection made, falling back to popular channels")
    
    # Set history limit and chunking based on mode
    if default_mode:
        history_limit = 100
        enable_chunking = False
        logger.info("Default mode: limit=100, chunking disabled")
    else:
        # Validate provided limit
        if args.limit <= 0 or args.limit > 10000:
            raise ValidationError("History limit must be between 1 and 10000")
        history_limit = args.limit
        enable_chunking = args.chunking
        logger.info(f"Configuration: limit={history_limit}, chunking={enable_chunking}")
    
    # Update global output directory if specified
    global OUTPUT_DIR
    if args.output_dir != OUTPUT_DIR:
        OUTPUT_DIR = args.output_dir
        logger.info(f"Output directory set to: {OUTPUT_DIR}")
    
    return channels, history_limit, enable_chunking

async def main():
    """Main function orchestrating the entire scraping process."""
    try:
        logger.info("Starting Telegram V2Ray configuration scraper")
        
        # Parse and validate command-line arguments
        channels, history_limit, enable_chunking = parse_and_validate_arguments()
        
        # Determine output filename
        use_popular_channels = len(channels) > 1 and set(channels) == set(POPULAR_CHANNELS)
        
        if use_popular_channels:
            base_filename = "popular_channels"
        else:
            # Normalize channel names for filename
            normalized_names = []
            for channel in channels:
                # Extract clean username from various formats
                clean_name = channel
                if "t.me/" in channel:
                    clean_name = channel.split("t.me/")[-1].split("/")[0]
                elif channel.startswith('@'):
                    clean_name = channel[1:]
                
                # Validate and sanitize for filename
                clean_name = validate_channel_name(clean_name)
                normalized_names.append(clean_name)
            
            if len(normalized_names) == 1:
                base_filename = normalized_names[0]
            else:
                # Create combined filename with length limit
                combined_name = "_".join(sorted(normalized_names))
                if len(combined_name) > 100:
                    # Use hash for very long names
                    import hashlib
                    hash_suffix = hashlib.md5(combined_name.encode()).hexdigest()[:8]
                    base_filename = f"combined_{hash_suffix}"
                else:
                    base_filename = combined_name
        
        # Prepare secure output paths
        script_dir = Path(__file__).parent
        output_dir = script_dir.parent / OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_filename = output_dir / base_filename
    
        
        # Setup Telegram client with proper error handling
        async with create_telegram_client() as client:
            logger.info("Successfully connected to Telegram")
            
            # Process channels and extract configurations
            all_configs = []
            successful_channels = []
            
            for channel in channels:
                try:
                    logger.info(f"Processing channel: {channel}")
                    
                    # Get channel entity
                    try:
                        entity = await client.get_entity(channel)
                        if not isinstance(entity, Channel):
                            logger.warning(f"Skipping {channel}: not a channel")
                            continue
                    except ValueError as e:
                        logger.error(f"Channel {channel} not found: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"Error accessing channel {channel}: {e}")
                        continue
                    
                    # Extract configurations from channel
                    channel_configs = await extract_channel_configs(
                        client, entity, history_limit
                    )
                    
                    if channel_configs:
                        all_configs.extend(channel_configs)
                        successful_channels.append(channel)
                        logger.info(f"Extracted {len(channel_configs)} configs from {channel}")
                    else:
                        logger.warning(f"No valid configs found in {channel}")
                        
                except Exception as e:
                    logger.error(f"Error processing channel {channel}: {e}")
                    continue
            
            if not all_configs:
                logger.warning("No V2Ray configurations found in any channel")
                return
            
            logger.info(f"Total configurations extracted: {len(all_configs)}")
            
            # Save configurations with file locking
            await save_configurations(
                all_configs, output_filename, enable_chunking, 
                successful_channels, use_popular_channels
            )
            
            logger.info("Configuration extraction completed successfully")

    except SecurityError as e:
        logger.error(f"Security error: {e}")
        sys.exit(1)
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        sys.exit(1)
    except ConfigProcessingError as e:
        logger.error(f"Configuration processing error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if VERBOSE:
            import traceback
            traceback.print_exc()
        sys.exit(1)

@asynccontextmanager
async def create_telegram_client():
    """
    Create and manage Telegram client with secure session handling.
    
    Yields:
        TelegramClient: Authenticated Telegram client
    """
    client = None
    try:
        # Setup secure session management
        script_dir = Path(__file__).parent
        session_file_path = script_dir.parent / f"{SESSION_FILE}.encrypted"
        
        # Try to load encrypted session
        session_string = None
        if session_file_path.exists():
            try:
                # Get password for session decryption
                password = collect_credentials_securely("Enter session password: ", is_password=True)
                session_string = secure_session_storage(str(session_file_path), password=password)
                
                if session_string:
                    logger.info("Loaded encrypted session successfully")
                else:
                    logger.warning("Failed to decrypt session, will create new one")
            except Exception as e:
                logger.warning(f"Session decryption failed: {e}, will create new session")
        
        # Setup client configuration
        if session_string:
            client_kwargs = {
                'api_id': API_ID,
                'api_hash': API_HASH,
                'session': StringSession(session_string)
            }
        else:
            client_kwargs = {
                'api_id': API_ID,
                'api_hash': API_HASH,
                'session': SESSION_FILE
            }
        
        # Add proxy if enabled
        if PROXY_ENABLED and PROXY_SERVER and PROXY_PORT:
            try:
                proxy_port_int = int(PROXY_PORT)
                proxy_info = ('socks5', PROXY_SERVER, proxy_port_int)
                if PROXY_USERNAME and PROXY_PASSWORD:
                    client_kwargs['proxy'] = proxy_info + (True, PROXY_USERNAME, PROXY_PASSWORD)
                else:
                    client_kwargs['proxy'] = proxy_info
                logger.info(f"Using proxy: {PROXY_SERVER}:{PROXY_PORT}")
            except ValueError:
                raise ValidationError(f"Invalid PROXY_PORT '{PROXY_PORT}'. Must be an integer.")
        
        # Create client
        client = TelegramClient(**client_kwargs)
        client.flood_sleep_threshold = 60
        
        # Connect and authenticate
        await client.connect()
        
        if not await client.is_user_authorized():
            if not PHONE_NUMBER:
                raise ValidationError("Phone number required for authentication")
            
            await authenticate_client(client, PHONE_NUMBER)
        
        # Save encrypted session if new session was created
        if not session_string:
            try:
                new_session_string = StringSession.save(client.session)
                password = collect_credentials_securely("Create password for session encryption: ", is_password=True)
                secure_session_storage(str(session_file_path), new_session_string, password)
                logger.info("Session encrypted and saved securely")
            except Exception as e:
                logger.warning(f"Failed to save encrypted session: {e}")
        
        logger.info("Successfully authenticated with Telegram")
        yield client
        
    except Exception as e:
        logger.error(f"Client setup error: {e}")
        raise
    finally:
        if client and client.is_connected():
            await client.disconnect()
            logger.info("Disconnected from Telegram")

async def authenticate_client(client: TelegramClient, phone_number: str):
    """
    Handle Telegram client authentication with retry logic.
    
    Args:
        client: Telegram client instance
        phone_number: Phone number for authentication
    """
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            await client.send_code_request(phone_number)
            
            while True:
                code = input('Enter the verification code: ').strip()
                if not code:
                    continue
                
                try:
                    await client.sign_in(phone_number, code)
                    return  # Successfully authenticated
                    
                except SessionPasswordNeededError:
                    password = input('Two-step verification enabled. Enter password: ').strip()
                    if password:
                        await client.sign_in(password=password)
                        return
                    
                except telethon.errors.PhoneCodeInvalidError:
                    logger.warning("Invalid code. Please try again.")
                    continue
                    
                except telethon.errors.PhoneCodeExpiredError:
                    logger.warning("Code expired. Requesting new code...")
                    break  # Break inner loop to request new code
                    
        except telethon.errors.FloodWaitError as e:
            wait_time = e.seconds
            logger.warning(f"Flood wait: {wait_time} seconds")
            await asyncio.sleep(wait_time + 1)
            
        except Exception as e:
            logger.error(f"Authentication attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise SecurityError(f"Authentication failed after {max_retries} attempts")

@with_telegram_rate_limit
async def extract_channel_configs(client: TelegramClient, entity: Channel, history_limit: int) -> List[str]:
    """
    Extract V2Ray configurations from a Telegram channel.
    
    Args:
        client: Authenticated Telegram client
        entity: Channel entity
        history_limit: Maximum number of messages to process
        
    Returns:
        List of valid V2Ray configuration strings
    """
    configs = set()
    message_count = 0
    
    try:
        # Use progress bar for user feedback
        with tqdm(desc=f"Scanning {entity.username or entity.title}", 
                 unit="msg", total=history_limit) as pbar:
            
            async for message in client.iter_messages(entity, limit=history_limit):
                message_count += 1
                pbar.update(1)
                
                if message.text:
                    # Extract configurations from message text
                    found_configs = extract_v2ray_configs(message.text)
                    configs.update(found_configs)
                    
                    # Update progress bar with current count
                    if message_count % 50 == 0:
                        pbar.set_postfix({"configs": len(configs)})
                        
    except telethon.errors.FloodWaitError as e:
        logger.warning(f"Flood wait for {entity.username}: {e.seconds} seconds")
        await asyncio.sleep(e.seconds + 1)
        
    except Exception as e:
        logger.error(f"Error extracting from {entity.username}: {e}")
        
    return list(configs)

async def save_configurations(configs: List[str], output_filename: Path, 
                            enable_chunking: bool, successful_channels: List[str], 
                            use_popular_channels: bool):
    """
    Save configurations to file(s) with proper error handling and metadata.
    
    Args:
        configs: List of V2Ray configuration strings
        output_filename: Base output filename
        enable_chunking: Whether to split into multiple files
        successful_channels: List of successfully processed channels
        use_popular_channels: Whether popular channels were used
    """
    if not configs:
        logger.warning("No configurations to save")
        return
    
    # Remove duplicates and sort
    unique_configs = sorted(list(set(configs)))
    logger.info(f"Saving {len(unique_configs)} unique configurations")
    
    try:
        async with file_lock(str(output_filename)):
            if enable_chunking:
                await save_chunked_configs(
                    unique_configs, output_filename, successful_channels, use_popular_channels
                )
            else:
                await save_single_config_file(
                    unique_configs, output_filename, successful_channels, use_popular_channels
                )
                
    except ConfigProcessingError:
        raise
    except Exception as e:
        raise ConfigProcessingError(f"Failed to save configurations: {e}")

async def save_single_config_file(configs: List[str], output_filename: Path, 
                                 successful_channels: List[str], use_popular_channels: bool):
    """
    Save all configurations to a single file.
    
    Args:
        configs: List of configuration strings
        output_filename: Output filename
        successful_channels: List of successful channels
        use_popular_channels: Whether popular channels were used
    """
    # Create profile title
    if use_popular_channels:
        profile_title = "Popular Telegram Channels Collection"
    else:
        profile_title = f"Telegram Channels: {', '.join(successful_channels[:5])}"
        if len(successful_channels) > 5:
            profile_title += f" +{len(successful_channels) - 5} more"
    
    # Save file
    save_config_file(str(output_filename), configs, profile_title)
    logger.info(f"Saved {len(configs)} configurations to {output_filename}")
    
    # Update README
    if GITHUB_USERNAME and REPO_NAME:
        try:
            readme_path = str(output_filename.relative_to(output_filename.parent.parent))
            readme_path = readme_path.replace('\\', '/')
            
            if use_popular_channels:
                channel_entry = "Popular Channels"
                update_readme(channel_entry, "", len(configs), readme_path, configs, successful_channels)
            else:
                channel_links = [f"[{ch}](https://t.me/{ch})" for ch in successful_channels[:3]]
                if len(successful_channels) > 3:
                    channel_links.append(f"+{len(successful_channels) - 3} more")
                channel_entry = ", ".join(channel_links)
                update_readme(channel_entry, "", len(configs), readme_path, configs, successful_channels)
                
        except Exception as e:
            logger.warning(f"Failed to update README: {e}")

async def save_chunked_configs(configs: List[str], output_filename: Path, 
                             successful_channels: List[str], use_popular_channels: bool):
    """
    Save configurations split into multiple chunk files.
    
    Args:
        configs: List of configuration strings
        output_filename: Base output filename
        successful_channels: List of successful channels
        use_popular_channels: Whether popular channels were used
    """
    # Split into chunks
    chunks = split_configs_into_chunks(configs, 500)
    
    if not validate_chunks(chunks, configs):
        raise ConfigProcessingError("Chunk validation failed")
    
    logger.info(f"Splitting {len(configs)} configs into {len(chunks)} files")
    
    saved_files = []
    for i, chunk in enumerate(chunks, 1):
        chunk_filename = f"{output_filename}_{i}"
        
        # Create profile title for chunk
        if use_popular_channels:
            profile_title = f"Popular Channels Collection - Part {i}/{len(chunks)}"
        else:
            profile_title = f"Multi-Channel Collection - Part {i}/{len(chunks)}"
        
        # Save chunk
        save_config_file(chunk_filename, chunk, profile_title)
        saved_files.append(chunk_filename)
        logger.info(f"Saved chunk {i}/{len(chunks)} with {len(chunk)} configs")
    
    # Update README for chunks
    if GITHUB_USERNAME and REPO_NAME:
        try:
            for i, chunk_file in enumerate(saved_files, 1):
                readme_path = str(Path(chunk_file).relative_to(Path(chunk_file).parent.parent))
                readme_path = readme_path.replace('\\', '/')
                
                chunk_size = len(chunks[i-1])
                
                if use_popular_channels:
                    channel_entry = f"Popular Channels - Part {i}/{len(chunks)}"
                else:
                    channel_entry = f"Multi-Channel Collection - Part {i}/{len(chunks)}"
                
                update_readme(channel_entry, "", chunk_size, readme_path, chunks[i-1], successful_channels)
                
        except Exception as e:
            logger.warning(f"Failed to update README for chunks: {e}")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        if VERBOSE:
            import traceback
            traceback.print_exc()
        sys.exit(1)
