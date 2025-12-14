import os
import json
import base64
import re
import sys
import platform
import subprocess
import time
import requests
import zipfile
import io
import shutil
import logging
from urllib.parse import urlparse, parse_qs, unquote
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

# Configuration
XRAY_CORE_URL_WIN = "https://github.com/XTLS/Xray-core/releases/download/v1.8.4/Xray-windows-64.zip"
XRAY_CORE_URL_LINUX = "https://github.com/XTLS/Xray-core/releases/download/v1.8.4/Xray-linux-64.zip"
CORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")
INPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "telegram")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "telegram_verified")
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "speed_test.log")
PROCESSED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "processed_configs.txt")
PROCESSED_FILES_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "processed_files.txt")

LATENCY_TEST_URL = "http://www.google.com/generate_204"
SPEED_TEST_URL = "http://speedtest.tele2.net/1MB.zip"
LOCAL_PORT = 10808
TIMEOUT = 5

# Setup Logging
def setup_logging():
    # Create logger
    logger = logging.getLogger("SpeedTester")
    logger.setLevel(logging.DEBUG)
    
    # Check if handlers already exist to avoid duplicate logs if function is called multiple times
    if logger.handlers:
        return logger

    # File Handler - Detailed logs (DEBUG level) including failures and reasons
    # Use mode='a' (append) to preserve history for resume functionality
    file_handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)

    # Note: Console output is handled explicitly via print/tqdm to avoid interference with progress bars
    
    logger.addHandler(file_handler)
    
    # Add separator for new run
    logger.info("-" * 50)
    logger.info(f"NEW RUN STARTED AT {datetime.now()}")
    logger.info("-" * 50)
    
    return logger

logger = setup_logging()

class XrayManager:
    def __init__(self):
        self.system = platform.system()
        self.core_path = os.path.join(CORE_DIR, "xray.exe" if self.system == "Windows" else "xray")
        
    def check_core(self):
        if not os.path.exists(self.core_path):
            msg = f"Xray core not found at {self.core_path}. Downloading..."
            print(msg)
            logger.info(msg)
            self.download_core()
            
    def download_core(self):
        os.makedirs(CORE_DIR, exist_ok=True)
        url = XRAY_CORE_URL_WIN if self.system == "Windows" else XRAY_CORE_URL_LINUX
        msg = f"Downloading from {url}..."
        print(msg)
        logger.info(msg)
        try:
            r = requests.get(url, stream=True)
            z = zipfile.ZipFile(io.BytesIO(r.content))
            z.extractall(CORE_DIR)
            print("Download complete.")
            logger.info("Download complete.")
            
            if self.system != "Windows":
                os.chmod(self.core_path, 0o755)
        except Exception as e:
            err_msg = f"Failed to download core: {e}"
            print(err_msg)
            logger.critical(err_msg, exc_info=True)
            sys.exit(1)

class ConfigConverter:
    @staticmethod
    def parse_vmess(link):
        try:
            if not link.startswith("vmess://"): return None
            b64 = link[8:]
            b64 += "=" * ((4 - len(b64) % 4) % 4)
            data = json.loads(base64.b64decode(b64).decode('utf-8'))
            
            outbound = {
                "protocol": "vmess",
                "settings": {
                    "vnext": [{
                        "address": data.get("add"),
                        "port": int(data.get("port")),
                        "users": [{
                            "id": data.get("id"),
                            "alterId": int(data.get("aid", 0)),
                            "security": data.get("scy", "auto"),
                            "level": 8
                        }]
                    }]
                },
                "streamSettings": {
                    "network": data.get("net", "tcp"),
                    "security": data.get("tls", ""),
                }
            }
            if data.get("net") == "ws":
                outbound["streamSettings"]["wsSettings"] = {
                    "path": data.get("path", "/"),
                    "headers": {"Host": data.get("host", "")}
                }
            elif data.get("net") == "grpc":
                 outbound["streamSettings"]["grpcSettings"] = {
                    "serviceName": data.get("path", "")
                }
            if data.get("tls") == "tls":
                outbound["streamSettings"]["tlsSettings"] = {
                    "serverName": data.get("sni") or data.get("host") or data.get("add"),
                    "allowInsecure": True
                }
            return outbound
        except Exception as e:
            logger.debug(f"Error parsing VMess link: {e} | Link: {link[:50]}...")
            return None

    @staticmethod
    def parse_vless(link):
        try:
            if not link.startswith("vless://"): return None
            uri = urlparse(link)
            if "@" not in uri.netloc: return None
            user_info, host_port = uri.netloc.split("@", 1)
            uuid = user_info
            if ":" in host_port:
                host, port = host_port.rsplit(":", 1)
                port = int(port)
            else:
                host = host_port
                port = 443
            params = parse_qs(uri.query)
            
            outbound = {
                "protocol": "vless",
                "settings": {
                    "vnext": [{
                        "address": host,
                        "port": port,
                        "users": [{"id": uuid, "encryption": "none", "level": 0}]
                    }]
                },
                "streamSettings": {
                    "network": params.get("type", ["tcp"])[0],
                    "security": params.get("security", ["none"])[0]
                }
            }
            if outbound["streamSettings"]["security"] == "tls":
                outbound["streamSettings"]["tlsSettings"] = {
                    "serverName": params.get("sni", [host])[0],
                    "allowInsecure": True
                }
                if "fp" in params: outbound["streamSettings"]["tlsSettings"]["fingerprint"] = params["fp"][0]
            
            net = outbound["streamSettings"]["network"]
            if net == "ws":
                outbound["streamSettings"]["wsSettings"] = {
                    "path": params.get("path", ["/"])[0],
                    "headers": {"Host": params.get("host", [host])[0]}
                }
            elif net == "grpc":
                 outbound["streamSettings"]["grpcSettings"] = {"serviceName": params.get("serviceName", [""])[0]}
            return outbound
        except Exception as e:
            logger.debug(f"Error parsing VLESS link: {e} | Link: {link[:50]}...")
            return None

    @staticmethod
    def parse_trojan(link):
        try:
            if not link.startswith("trojan://"): return None
            uri = urlparse(link)
            if "@" not in uri.netloc: return None
            password, host_port = uri.netloc.split("@", 1)
            if ":" in host_port:
                host, port = host_port.rsplit(":", 1)
                port = int(port)
            else:
                host = host_port
                port = 443
            params = parse_qs(uri.query)
            
            outbound = {
                "protocol": "trojan",
                "settings": {"servers": [{"address": host, "port": port, "password": password, "level": 0}]},
                "streamSettings": {
                    "network": params.get("type", ["tcp"])[0],
                    "security": params.get("security", ["tls"])[0]
                }
            }
            if outbound["streamSettings"]["security"] == "tls":
                outbound["streamSettings"]["tlsSettings"] = {
                    "serverName": params.get("sni", [host])[0],
                    "allowInsecure": True
                }
            net = outbound["streamSettings"]["network"]
            if net == "ws":
                outbound["streamSettings"]["wsSettings"] = {
                    "path": params.get("path", ["/"])[0],
                    "headers": {"Host": params.get("host", [host])[0]}
                }
            elif net == "grpc":
                 outbound["streamSettings"]["grpcSettings"] = {"serviceName": params.get("serviceName", [""])[0]}
            return outbound
        except Exception as e:
            logger.debug(f"Error parsing Trojan link: {e} | Link: {link[:50]}...")
            return None

    @staticmethod
    def parse_ss(link):
        try:
            if not link.startswith("ss://"): return None
            body = link[5:]
            if "#" in body: body = body.split("#", 1)[0]
            if "@" not in body:
                try:
                    body += "=" * ((4 - len(body) % 4) % 4)
                    decoded = base64.urlsafe_b64decode(body).decode('utf-8', errors='ignore')
                    method_pass, host_port = decoded.rsplit("@", 1)
                    method, password = method_pass.split(":", 1)
                    host, port = host_port.rsplit(":", 1)
                    port = int(port)
                except Exception as e:
                    logger.debug(f"Error parsing SS link (simple format): {e}")
                    return None
            else:
                user_info_b64, host_port = body.split("@", 1)
                try:
                    user_info_b64 += "=" * ((4 - len(user_info_b64) % 4) % 4)
                    user_info = base64.urlsafe_b64decode(user_info_b64).decode('utf-8', errors='ignore')
                    method, password = user_info.split(":", 1)
                except Exception as e:
                    logger.debug(f"Error parsing SS link (user_info decode): {e}")
                    return None
                host, port = host_port.rsplit(":", 1)
                port = int(port)
            
            return {
                "protocol": "shadowsocks",
                "settings": {"servers": [{"address": host, "port": port, "method": method, "password": password, "level": 0}]},
                "streamSettings": {"network": "tcp"}
            }
        except Exception as e:
            logger.debug(f"Error parsing SS link: {e} | Link: {link[:50]}...")
            return None

    @staticmethod
    def parse_hy2(link):
        try:
            if not link.startswith("hy2://"): return None
            # hy2://user@host:port?params#tag
            from urllib.parse import urlparse, parse_qs
            
            # Handle potential encoding issues in the link itself if needed, but usually it's standard URL
            parsed = urlparse(link)
            if not parsed.hostname or not parsed.port:
                return None
            
            auth = parsed.username
            if not auth:
                # Sometimes auth is in the netloc before @ but urlparse handles it usually
                pass
                
            params = parse_qs(parsed.query)
            
            # Extract params
            sni = params.get("sni", [""])[0]
            insecure = params.get("insecure", ["0"])[0] == "1"
            obfs = params.get("obfs", [""])[0]
            obfs_password = params.get("obfs-password", [""])[0]
            
            # Construct Xray config
            outbound = {
                "protocol": "hysteria2",
                "settings": {
                    "servers": [{
                        "address": parsed.hostname,
                        "port": parsed.port,
                        "auth": auth,
                    }]
                },
                "streamSettings": {
                    "network": "udp",
                    "security": "tls",
                    "tlsSettings": {
                        "serverName": sni,
                        "allowInsecure": insecure
                    }
                }
            }
            
            if obfs == "salamander":
                outbound["settings"]["servers"][0]["obfs"] = {
                    "type": "salamander",
                    "password": obfs_password
                }
                
            return outbound
        except Exception as e:
            logger.debug(f"Error parsing Hysteria2 link: {e} | Link: {link[:50]}...")
            return None

    @staticmethod
    def link_to_outbound(link):
        link = link.strip()
        if link.startswith("vmess://"): return ConfigConverter.parse_vmess(link)
        elif link.startswith("vless://"): return ConfigConverter.parse_vless(link)
        elif link.startswith("trojan://"): return ConfigConverter.parse_trojan(link)
        elif link.startswith("ss://"): return ConfigConverter.parse_ss(link)
        elif link.startswith("hy2://") or link.startswith("hysteria2://"): return ConfigConverter.parse_hy2(link.replace("hysteria2://", "hy2://"))
        logger.debug(f"Unsupported protocol or invalid link format: {link[:50]}...")
        return None

    @staticmethod
    def generate_config(outbound, log_level="none"):
        return {
            "log": {"loglevel": log_level},
            "inbounds": [{"port": LOCAL_PORT, "protocol": "http", "settings": {"timeout": 0}}],
            "outbounds": [outbound]
        }

class SpeedTester:
    def __init__(self):
        self.xray = XrayManager()
        self.xray.check_core()
        
    def test_config(self, link):
        outbound = ConfigConverter.link_to_outbound(link)
        if not outbound: 
            return None
            
        config = ConfigConverter.generate_config(outbound)
        # Use unique config file for each test
        config_path = os.path.join(CORE_DIR, f"config_{int(time.time()*1000)}_{os.getpid()}.json")
        
        try:
            with open(config_path, 'w') as f: json.dump(config, f)
        except Exception as e:
            logger.error(f"Failed to write config file {config_path}: {e}")
            return None
            
        proc = None
        result = None
        
        try:
            # Start Xray core
            # Capture stderr to log startup errors if needed
            proc = subprocess.Popen(
                [self.xray.core_path, "-c", config_path], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.PIPE
            )
            
            # Allow Xray time to initialize
            time.sleep(1.5) 
            
            if proc.poll() is not None:
                # Process exited prematurely
                stderr = proc.stderr.read().decode('utf-8', errors='ignore')
                logger.debug(f"Xray core exited prematurely. Stderr: {stderr}")
                return None

            proxies = {
                "http": f"http://127.0.0.1:{LOCAL_PORT}", 
                "https": f"http://127.0.0.1:{LOCAL_PORT}"
            }
            
            # 1. Latency Test
            try:
                start_time = time.time()
                requests.get(LATENCY_TEST_URL, proxies=proxies, timeout=TIMEOUT)
                latency = (time.time() - start_time) * 1000
            except requests.exceptions.Timeout:
                logger.debug("Latency test timed out.")
                return None
            except requests.exceptions.ConnectionError:
                logger.debug("Latency test connection refused/failed.")
                return None
            except Exception as e:
                logger.debug(f"Latency test failed: {e}")
                return None
            
            # 2. Speed Test (only if latency pass)
            speed_mbps = 0.0
            try:
                start_dl = time.time()
                r_speed = requests.get(SPEED_TEST_URL, proxies=proxies, timeout=10, stream=True)
                size_downloaded = 0
                # Download up to 1MB or until timeout
                for chunk in r_speed.iter_content(chunk_size=8192):
                    size_downloaded += len(chunk)
                    if size_downloaded >= 1024 * 1024: break # Stop at 1MB
                
                dl_time = time.time() - start_dl
                if dl_time > 0:
                    speed_mbps = (size_downloaded * 8) / (dl_time * 1000 * 1000) # bits per second / 1M
            except Exception as e:
                logger.debug(f"Speed test failed (Latency passed): {e}")
                # We don't fail the whole config if speed test fails, just report 0 speed
                
            result = {'latency': latency, 'speed': speed_mbps}
            
        except Exception as e:
            logger.debug(f"Unexpected error during test execution: {e}", exc_info=True)
            
        finally:
            if proc:
                proc.terminate()
                try: 
                    proc.wait(timeout=1)
                except subprocess.TimeoutExpired: 
                    proc.kill()
                # Close stderr pipe
                if proc.stderr:
                    proc.stderr.close()
                    
            if os.path.exists(config_path): 
                try:
                    os.remove(config_path)
                except:
                    pass
            
        return result

def import_history_from_log(seen_configs):
    """
    Parse the existing log file to find configs that were already tested
    but might not be in the processed_configs.txt file (e.g. from runs before resume feature).
    """
    if not os.path.exists(LOG_FILE):
        return

    print("Checking log file for previously tested configs...")
    new_found = []
    
    try:
        with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                config = None
                # Check for PASS logs: "... - PASS | speed | latency | config"
                if " - PASS | " in line:
                    parts = line.split(" | ")
                    if len(parts) >= 4:
                        config = parts[-1].strip()
                # Check for FAIL logs: "... - FAIL | config"
                elif " - FAIL | " in line:
                    parts = line.split(" | ")
                    if len(parts) >= 2:
                        config = parts[-1].strip()
                
                if config and config not in seen_configs:
                    seen_configs.add(config)
                    new_found.append(config)
        
        if new_found:
            print(f"  Imported {len(new_found)} configs from history log.")
            logger.info(f"Imported {len(new_found)} configs from history log.")
            
            # Append to processed file so we don't have to parse log next time
            try:
                with open(PROCESSED_FILE, 'a', encoding='utf-8') as pf:
                    for c in new_found:
                        pf.write(c + "\n")
            except Exception as e:
                logger.error(f"Failed to save imported configs to resume file: {e}")
        else:
            print("  No new configs found in log history.")
            
    except Exception as e:
        logger.error(f"Failed to import from log file: {e}")

def import_history_from_verified(seen_configs):
    """
    Recover previously verified (passed) configs from the output directory.
    This helps recover state if the log file was deleted or truncated.
    """
    if not os.path.exists(OUTPUT_DIR):
        return

    print("Checking verified output files for previously passed configs...")
    new_found = []
    
    try:
        files = [f for f in os.listdir(OUTPUT_DIR) if os.path.isfile(os.path.join(OUTPUT_DIR, f))]
        for filename in files:
            filepath = os.path.join(OUTPUT_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        config = line.strip()
                        if config and not config.startswith("#") and config not in seen_configs:
                            seen_configs.add(config)
                            new_found.append(config)
            except Exception as e:
                logger.error(f"Failed to read verified file {filename}: {e}")

        if new_found:
            print(f"  Imported {len(new_found)} passed configs from verified output.")
            logger.info(f"Imported {len(new_found)} passed configs from verified output.")
            
            # Append to processed file
            try:
                with open(PROCESSED_FILE, 'a', encoding='utf-8') as pf:
                    for c in new_found:
                        pf.write(c + "\n")
            except Exception as e:
                logger.error(f"Failed to save verified configs to resume file: {e}")
        else:
            print("  No new passed configs found in verified output.")
            
    except Exception as e:
        logger.error(f"Failed to import from verified directory: {e}")

def main():
    if not os.path.exists(INPUT_DIR):
        print(f"Error: Input directory not found: {INPUT_DIR}")
        logger.error(f"Input directory not found: {INPUT_DIR}")
        return
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    tester = SpeedTester()
    files = [f for f in os.listdir(INPUT_DIR) if os.path.isfile(os.path.join(INPUT_DIR, f))]
    
    total_configs = 0
    total_verified = 0
    max_speed = 0.0
    min_speed = float('inf')
    
    print(f"Starting verification...")
    print(f"Input: {INPUT_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Log File: {LOG_FILE}")
    print(f"Resume File: {PROCESSED_FILE}")
    
    seen_configs = set()
    
    # Load previously processed configs for resume capability
    if os.path.exists(PROCESSED_FILE):
        try:
            with open(PROCESSED_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        seen_configs.add(stripped)
            print(f"Loaded {len(seen_configs)} previously processed configs from resume file.")
            logger.info(f"Loaded {len(seen_configs)} previously processed configs from resume file.")
        except Exception as e:
            logger.error(f"Failed to load resume file: {e}")
            
    # Import history from log file (migration/backfill)
    import_history_from_log(seen_configs)
    
    # Import history from verified output (recovery of passed configs)
    import_history_from_verified(seen_configs)
    
    # Load list of fully processed files to skip them
    processed_files = set()
    if os.path.exists(PROCESSED_FILES_LOG):
        try:
            with open(PROCESSED_FILES_LOG, 'r', encoding='utf-8') as f:
                processed_files = {line.strip() for line in f if line.strip()}
            print(f"Loaded {len(processed_files)} fully processed files.")
        except Exception as e:
            logger.error(f"Failed to load processed files log: {e}")
            
    # Open resume file for appending new processed configs
    try:
        resume_file = open(PROCESSED_FILE, 'a', encoding='utf-8')
    except Exception as e:
        logger.error(f"Failed to open resume file for writing: {e}")
        resume_file = None

    for filename in files:
        if filename in processed_files:
            print(f"\nSkipping {filename} (already fully processed).")
            continue
            
        filepath = os.path.join(INPUT_DIR, filename)
        out_filepath = os.path.join(OUTPUT_DIR, filename)
        
        print(f"\nProcessing {filename}...")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            err_msg = f"Failed to read file {filename}: {e}"
            print(f"  {err_msg}")
            logger.error(err_msg)
            continue
        
        # Parse configs and preserve headers
        raw_configs = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
        headers = [line.strip() for line in lines if line.strip() and line.strip().startswith("#")]
        
        # Deduplicate
        configs = []
        duplicates_count = 0
        for config in raw_configs:
            if config not in seen_configs:
                configs.append(config)
                seen_configs.add(config)
            else:
                duplicates_count += 1
        
        print(f"  Found {len(raw_configs)} configs ({len(configs)} new, {duplicates_count} duplicates/processed).")
        if duplicates_count > 0:
            logger.info(f"Removed {duplicates_count} duplicates/processed from {filename}")
        
        valid_results = []
        
        if configs:
            # Use tqdm for progress bar
            pbar = tqdm(configs, desc="  Testing", unit="cfg", ncols=100)
            
            for config in pbar:
                res = tester.test_config(config)
                
                # Mark as processed immediately to support resume
                if resume_file:
                    try:
                        resume_file.write(config + "\n")
                        resume_file.flush()
                    except Exception as e:
                        logger.error(f"Failed to write to resume file: {e}")
                
                if res:
                    # Format output
                    speed_str = f"{res['speed']:.2f} Mbps"
                    latency_str = f"{res['latency']:.0f}ms"
                    short_config = config[:30] + "..." if len(config) > 30 else config
                    
                    # Log to terminal (above progress bar)
                    tqdm.write(f"  [PASS] {speed_str:<10} | {latency_str:<6} | {short_config}")
                    
                    # Log to file
                    logger.info(f"PASS | {speed_str} | {latency_str} | {config}")
                    
                    valid_results.append({'line': config, 'result': res})
                    
                    # Update stats
                    total_verified += 1
                    if res['speed'] > max_speed: max_speed = res['speed']
                    if res['speed'] < min_speed: min_speed = res['speed']
                else:
                    logger.debug(f"FAIL | {config}")
            
            pbar.close()
            
        total_configs += len(configs)
        
        # Filter and Sort
        # Sort by Speed (Descending) then Latency (Ascending)
        valid_results.sort(key=lambda x: (-x['result']['speed'], x['result']['latency']))
        
        # Save if we have valid configs
        if valid_results:
            try:
                with open(out_filepath, 'w', encoding='utf-8') as f:
                    for h in headers: f.write(h + "\n")
                    for c in valid_results: f.write(c['line'] + "\n")
                
                msg = f"Saved {len(valid_results)} configs to {out_filepath}"
                print(f"  {msg}")
                logger.info(msg)
            except Exception as e:
                err_msg = f"Failed to save results to {out_filepath}: {e}"
                print(f"  {err_msg}")
                logger.error(err_msg)
        else:
            msg = f"No working configs for {filename}, skipping save."
            print(f"  {msg}")
            logger.info(msg)
            
        # Mark file as fully processed
        try:
            with open(PROCESSED_FILES_LOG, 'a', encoding='utf-8') as f:
                f.write(filename + "\n")
        except Exception as e:
            logger.error(f"Failed to mark file {filename} as processed: {e}")

    # Final Report
    if min_speed == float('inf'): min_speed = 0.0
    
    print("\n" + "="*50)
    print("VERIFICATION SUMMARY")
    print("="*50)
    print(f"Total Configs Scanned: {total_configs}")
    print(f"Working Configs:       {total_verified}")
    print(f"Success Rate:          {(total_verified/total_configs*100) if total_configs > 0 else 0:.1f}%")
    print(f"Max Speed:             {max_speed:.2f} Mbps")
    print(f"Min Speed (of working):{min_speed:.2f} Mbps")
    print(f"Verified files saved to: {OUTPUT_DIR}")
    print(f"Detailed logs saved to:  {LOG_FILE}")
    print("="*50)
    
    if resume_file:
        resume_file.close()
        
    logger.info("VERIFICATION SUMMARY COMPLETED")

if __name__ == "__main__":
    main()
