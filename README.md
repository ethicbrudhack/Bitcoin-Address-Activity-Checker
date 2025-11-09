🪙 Bitcoin Address Activity Checker (Untested Prototype)

⚠️ Educational / Research Use Only
This script is for learning and testing only — it checks Bitcoin addresses from a local database against multiple public blockchain APIs to determine whether they are active or have a non-zero balance.

⚠️ This script is experimental and untested. It may contain bugs or produce incorrect data.
Use at your own risk, and never for scanning or analyzing wallets you do not own.

📘 Overview

btc_active_address_checker.py connects to a local SQLite database of generated Bitcoin addresses, retrieves each one, and queries multiple public blockchain APIs (Blockstream, Blockchain.info, BlockCypher, Mempool.space, etc.) to check if the address:

has any transactions, and

holds a non-zero BTC balance.

It then writes all active results to an output file and saves progress in a checkpoint file, allowing the script to resume later.

This is useful for educational testing, API benchmarking, or exploring blockchain activity patterns — not for searching or probing other people’s wallets.

⚙️ Features

Queries multiple blockchain APIs for redundancy and reliability.

Automatically disables (“cooldowns”) failing APIs for 15 minutes after rate-limits or errors.

Logs and resumes progress via checkpoint files.

Saves results to text files and errors to a separate log.

Randomized request headers and delays to avoid triggering rate-limits.

Detects Bitcoin addresses using a built-in regex.

🧠 How It Works

Load the database
Opens generated_addresses1.db, reads all Bitcoin addresses from the generated table.

Checkpoint system
Reads checkpoint0.txt to continue where the previous session stopped.

Iterate through addresses
For each address:

Selects an available API provider from API_PROVIDERS.

Sends an HTTP GET request to check the address.

Extracts the number of transactions and balance using provider-specific JSON parsing.

Saves the result or error log.

Waits 1–3 seconds before the next request.

Error handling and cooldowns

APIs returning HTTP 429 or 5xx errors are disabled for 15 minutes (COOLDOWN_MINUTES).

Errors are logged in bledy_api0.txt.

Output
Active addresses (balance > 0 or transactions > 0) are appended to btc_active_addressesbrain0.txt.

🧩 Configuration
Variable	Description	Default
DB_FILE	SQLite file containing Bitcoin addresses (table generated.address)	generated_addresses1.db
OUTPUT_FILE	File to save addresses with non-zero activity	btc_active_addressesbrain0.txt
ERRORS_FILE	Log file for API errors	bledy_api0.txt
CHECKPOINT_FILE	Saves current progress index	checkpoint0.txt
MIN_DELAY	Minimum delay between API requests (seconds)	1.0
COOLDOWN_MINUTES	Time to temporarily disable failing APIs	15
🧰 Requirements

Install dependencies:

pip install requests colorama


You will also need a local SQLite database with a table similar to:

CREATE TABLE generated (address TEXT PRIMARY KEY);


Each record should contain one valid Bitcoin address.

▶️ Usage

Run the script directly:

python3 btc_active_address_checker.py


Example console output:

[ℹ] Found 1200 BTC addresses in database. Starting from 0.

[1/1200] Checking: 1KFHE7w8BhaENAswwryaoccDb6qcT6DbYY
    → checking via Blockstream...
    💰 0.12450000 BTC — 6 tx (Blockstream)
    (checkpoint saved: 1)
    ⏳ Waiting 2.3s...


Results with positive balances are written to btc_active_addressesbrain0.txt.

⚠️ Disclaimer

This script uses public APIs that may impose rate-limits or block requests.

It is untested, may contain logic errors, and should not be relied upon for accurate balances.

The balance and transaction data fetched are for educational exploration only.

Do not use this code to monitor, scrape, or probe third-party wallets.

The author(s) assume no responsibility for any misuse, data inaccuracies, or rate-limiting bans.

🧪 Educational Use Cases

Learn how to interface with public Bitcoin APIs.

Compare API reliability, latency, and JSON formats.

Understand address activity and balance structures.

Practice handling rate-limits and API backoff systems.

🚧 Known Limitations

Untested / unstable — expect exceptions or incomplete data.

Some APIs may return inconsistent or outdated results.

Frequent API calls may trigger bans or rate-limits.

Works only with Bitcoin mainnet addresses.

No asynchronous I/O — all requests are sequential.

🪪 License

MIT License — free for educational and research use, provided “as is” without warranty of any kind.
If you reuse or modify this code, please include the educational disclaimer and respect each API’s terms of service.

BTC donation address: bc1q4nyq7kr4nwq6zw35pg0zl0k9jmdmtmadlfvqhr
