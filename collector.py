import urllib.parse
import requests
from github import Github
from collections import OrderedDict

def push_to_github(file_path, content, repo_name, branch_name, github_token):
    g = Github(github_token)
    repo = g.get_user().get_repo(repo_name)
    
    try:
        file = repo.get_contents(file_path, ref=branch_name)
        repo.update_file(file_path, "Update config file", content, file.sha, branch=branch_name)
    except:
        repo.create_file(file_path, "Create config file", content, branch=branch_name)

def find_country_code(link):
    try:
        parsed_link = urllib.parse.urlparse(link)
        fragment = parsed_link.fragment

        if fragment:
            decoded_fragment = urllib.parse.unquote(fragment)
            country_code = decoded_fragment.split('%')[-1][:2]

            if country_code.isalpha() and len(country_code) == 2:
                return country_code.upper()

    except Exception as e:
        print(f"Error: {e}")

    return None

def extract_v2ray_configs(subscription_link):
    response = requests.get(subscription_link).text
    config_links = set(response.split("\n"))
    return config_links

def generate_file_content(subscription_links):
    file_content = OrderedDict((config_type, set()) for config_type in ["vmess", "ss", "vless", "trojan", "tuic", "hysteria", "hy2", "socks5", "ssr"])
    country_mappings = OrderedDict({
        "country1": {"US", "GB", "CA"},
        "country2": {"DE", "FR", "NL", "FI"},
        "country3": {"IR", "RELAY"}
    })

    for subscription_link in set(subscription_links):
        config_links = extract_v2ray_configs(subscription_link)
        for config_link in config_links:
            if config_link:
                prefix = config_link.split("://")[0]
                country_code = find_country_code(config_link)

                if prefix in file_content:
                    file_content[prefix].add(config_link)

                for country_key, country_codes in country_mappings.items():
                    if country_code in country_codes:
                        file_content[country_key].add(config_link)

    return file_content

github_token = "your_github_token"  # Replace with your GitHub token
subscription_links = [
    "https://raw.githubusercontent.com/MrMohebi/xray-proxy-grabber-telegram/master/collected-proxies/row-url/actives.txt",
    "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/splitted/subscribe",
    # ... (add other subscription links)
]

raw_file_content = generate_file_content(subscription_links)

for config_type, content_set in raw_file_content.items():
    file_path = config_type
    repo_name = 'v2rayAuto'
    branch_name = 'main'
    content = "\n".join(content_set)
    push_to_github(file_path, content, repo_name, branch_name, github_token)
