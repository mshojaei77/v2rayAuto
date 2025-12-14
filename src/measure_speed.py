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
    file_handler = logging.FileHandler(LOG_FILE, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)

    # Note: Console output is handled explicitly via print/tqdm to avoid interference with progress bars
    
    logger.addHandler(file_handler)
    
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
                    decoded = base64.urlsafe_b64decode(body).decode('utf-8')
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
                    user_info = base64.urlsafe_b64decode(user_info_b64).decode('utf-8')
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
    def link_to_outbound(link):
        link = link.strip()
        if link.startswith("vmess://"): return ConfigConverter.parse_vmess(link)
        elif link.startswith("vless://"): return ConfigConverter.parse_vless(link)
        elif link.startswith("trojan://"): return ConfigConverter.parse_trojan(link)
        elif link.startswith("ss://"): return ConfigConverter.parse_ss(link)
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
    
    for filename in files:
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
        configs = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
        headers = [line.strip() for line in lines if line.strip() and line.strip().startswith("#")]
        
        print(f"  Found {len(configs)} configs.")
        
        valid_results = []
        
        if configs:
            # Use tqdm for progress bar
            pbar = tqdm(configs, desc="  Testing", unit="cfg", ncols=100)
            
            for config in pbar:
                res = tester.test_config(config)
                
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
    
    logger.info("VERIFICATION SUMMARY COMPLETED")

if __name__ == "__main__":
    main()
