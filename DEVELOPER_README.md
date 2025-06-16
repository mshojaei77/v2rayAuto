# Developer Guide: V2rayAuto

This document provides instructions for developers on how to use and maintain the scripts in this project. For user-facing information, see `README.md`.

## Project Overview

This project consists of several scripts designed to automatically collect, process, and serve V2Ray configuration links. The workflow is as follows:
1.  **Collection**: Scripts scrape configurations from public sources and Telegram channels.
2.  **Processing**: The collected configurations are de-duplicated, categorized, and stored in subscription files within the repository.
3.  **Serving**: A Cloudflare Worker aggregates these subscription files into a single link for use in V2Ray clients.

## Initial Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/mshojaei77/v2rayAuto.git
    cd v2rayAuto
    ```

2.  **Install dependencies:**
    This project uses `uv` for package management.
    ```bash
    pip install uv
    uv pip install -r requirements.txt
    ```

3.  **Create `.env` file:**
    Create a `.env` file in the root directory. Populate it with your credentials:
    ```
    # GitHub Personal Access Token with repo scope
    GITHUB_TOKEN="ghp_..."
    GITHUB_USERNAME="your_github_username"
    REPO_NAME="your_repo_name" # e.g., v2rayAuto

    # Telegram API Credentials from my.telegram.org
    TELEGRAM_API_ID="1234567"
    TELEGRAM_API_HASH="your_api_hash"
    TELEGRAM_PHONE_NUMBER="+1234567890"

    # Optional: Proxy for Telegram connection
    PROXY_ENABLED="False"
    PROXY_SERVER="your_proxy_server"
    PROXY_PORT="your_proxy_port"
    PROXY_USERNAME=""
    PROXY_PASSWORD=""
    ```

## Python Scripts (`src/`)

This section details the Python scripts located in the `src/` directory.

### `src/collector.py`

*   **What it does:** This script fetches V2Ray configurations from a hardcoded list of public subscription links. It then categorizes the links by protocol (VMess, VLESS, Trojan, etc.), removes duplicates, and pushes the categorized subscription files to the `subs/` directory in the GitHub repository.

*   **How to use:**
    - Ensure your `GITHUB_TOKEN` is set in the `.env` file.
    - Run the script from the root directory:
      ```bash
      python src/collector.py
      ```

*   **When to use:** Run this script when you want to perform a full refresh of all configurations from the public sources defined in `subscription_links`. This is a resource-intensive operation and should be run periodically (e.g., once a day) to update the base configurations.

### `src/telgram2sub.py`

*   **What it does:** This interactive script scrapes V2Ray configurations from one or more specified Telegram channels. It creates a new, combined subscription file in the `telegram/` directory and updates the main `README.md` to include a link to this new file.

*   **How to use:**
    - Ensure your Telegram API credentials (`TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_PHONE_NUMBER`) are set in the `.env` file.
    - Run the script from the root directory:
      ```bash
      python src/telgram2sub.py
      ```
    - The script will prompt you to enter the Telegram channel(s) and the number of days of message history to scrape.

*   **When to use:** Use this script to add a *new* subscription feed from one or more Telegram channels that are not yet being tracked. It's for bootstrapping new channel sources.

### `src/update_subscriptions.py`

*   **What it does:** This script automatically updates the existing subscription files in the `telegram/` directory. It reads each file, identifies the source Telegram channels from the `#profile-title` metadata, and fetches the latest configs from those channels for a specified number of recent days. It then adds any new, unique configs to the existing files.

*   **How to use:**
    - Ensure your Telegram API credentials are set in the `.env` file.
    - Run the script from the root directory:
      ```bash
      python src/update_subscriptions.py
      ```
    - It will prompt for the number of days of history to check for updates (e.g., the last 7 days).

*   **When to use:** This script is meant to be run regularly (e.g., via a GitHub Action or cron job) to keep the Telegram-sourced subscriptions fresh. It ensures that the files in `telegram/` are continuously updated with new configurations from their source channels.

## JavaScript Worker (`src/`)

### `src/worker.js`

*   **What it does:** This is a Cloudflare Worker script that acts as a subscription aggregator. It fetches multiple subscription files from the repository, merges them into a single list, removes duplicate configurations, and serves them to the end-user. This provides a stable, single endpoint for V2Ray clients.

*   **How to use:**
    1.  Modify the `subscriptionLinks` array in the script to point to the raw GitHub URLs of the subscription files you want to aggregate (e.g., files from `subs/` and `telegram/`).
    2.  Deploy the script to your Cloudflare Workers account.

*   **When to use:** This is the serving layer of the project. After the Python scripts have updated the configuration files and pushed them to GitHub, this worker provides the final, aggregated subscription link that users will add to their V2Ray clients. 