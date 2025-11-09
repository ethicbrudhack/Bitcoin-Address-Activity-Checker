import os
import re
import time
import random
import sqlite3
import requests
from datetime import datetime, timedelta
from colorama import Fore, Style, init

init(autoreset=True)

# --- ŚCIEŻKI I PLIKI ---
DB_FILE = "generated_addresses1.db"
OUTPUT_FILE = "btc_active_addressesbrain0.txt"
ERRORS_FILE = "bledy_api0.txt"
CHECKPOINT_FILE = "checkpoint0.txt"

# --- API I KONFIGURACJA ---
MIN_DELAY = 1.0
COOLDOWN_MINUTES = 15  # po jakim czasie API może znów zostać włączone

# --- WZORZEC ADRESU BTC ---
BTC_REGEX = re.compile(r"\b(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b")

# --- USER AGENTS ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Opera/9.80 (Windows NT 6.1; WOW64) Presto/2.12.388 Version/12.18",
]

# --- API PROVIDERS ---
# --- API PROVIDERS (rozszerzone) ---
API_PROVIDERS = [
    # --- Blockstream ---
    {
        "name": "Blockstream",
        "url_template": "https://blockstream.info/api/address/{}",
        "get_txcount": lambda d: d.get("chain_stats", {}).get("tx_count", 0),
        "get_balance": lambda d: (d.get("chain_stats", {}).get("funded_txo_sum", 0)
                                  - d.get("chain_stats", {}).get("spent_txo_sum", 0)) / 1e8
    },
    # --- Blockchain.info ---
    {
        "name": "Blockchain.info",
        "url_template": "https://blockchain.info/rawaddr/{}",
        "get_txcount": lambda d: d.get("n_tx", 0),
        "get_balance": lambda d: d.get("final_balance", 0) / 1e8
    },
    # --- BlockCypher ---
    {
        "name": "BlockCypher",
        "url_template": "https://api.blockcypher.com/v1/btc/main/addrs/{}",
        "get_txcount": lambda d: d.get("n_tx", 0),
        "get_balance": lambda d: d.get("final_balance", 0) / 1e8
    },
    # --- SoChain ---
    {
        "name": "SoChain",
        "url_template": "https://sochain.com/api/v2/get_address_balance/BTC/{}",
        "get_txcount": lambda d: 0,
        "get_balance": lambda d: float(d.get("data", {}).get("confirmed_balance", 0.0))
    },
    # --- Bitaps ---
    {
        "name": "Bitaps",
        "url_template": "https://api.bitaps.com/btc/v1/blockchain/address/state/{}",
        "get_txcount": lambda d: d.get("data", {}).get("txs_out", 0),
        "get_balance": lambda d: float(d.get("data", {}).get("balance", 0)) / 1e8
    },
    # --- Blockchair ---
    {
        "name": "Blockchair",
        "url_template": "https://api.blockchair.com/bitcoin/dashboards/address/{}",
        "get_txcount": lambda d: next(iter(d["data"].values()))["address"]["transaction_count"],
        "get_balance": lambda d: next(iter(d["data"].values()))["address"]["balance"] / 1e8
    },
    # --- BTC.com ---
    {
        "name": "BTC.com",
        "url_template": "https://chain.api.btc.com/v3/address/{}",
        "get_txcount": lambda d: d.get("data", {}).get("tx_count", 0),
        "get_balance": lambda d: d.get("data", {}).get("balance", 0) / 1e8
    },
    # --- Blockonomics ---
    {
        "name": "Blockonomics",
        "url_template": "https://www.blockonomics.co/api/balance?addr={}",
        "get_txcount": lambda d: 0,
        "get_balance": lambda d: float(list(d["response"].values())[0]["confirmed"]) / 1e8 if "response" in d else 0
    },
    # --- Bitquery ---
    {
        "name": "Bitquery",
        "url_template": "https://graphql.bitquery.io/?query={{bitcoin{{address(address:\"{}\"){{balance}}}}}}",
        "get_txcount": lambda d: 0,
        "get_balance": lambda d: float(d.get("data", {}).get("bitcoin", [{}])[0].get("address", [{}])[0].get("balance", 0))
    },
    # --- Mempool.space ---
    {
        "name": "Mempool",
        "url_template": "https://mempool.space/api/address/{}",
        "get_txcount": lambda d: d.get("chain_stats", {}).get("tx_count", 0),
        "get_balance": lambda d: (d.get("chain_stats", {}).get("funded_txo_sum", 0)
                                  - d.get("chain_stats", {}).get("spent_txo_sum", 0)) / 1e8
    },
    # --- Smartbit ---
    {
        "name": "Smartbit",
        "url_template": "https://api.smartbit.com.au/v1/blockchain/address/{}",
        "get_txcount": lambda d: d.get("address", {}).get("total.transaction_count", 0),
        "get_balance": lambda d: d.get("address", {}).get("total.balance", 0) / 1e8
    },
    # --- Esplora (Blockstream mirror) ---
    {
        "name": "Esplora",
        "url_template": "https://mempool.emzy.de/api/address/{}",
        "get_txcount": lambda d: d.get("chain_stats", {}).get("tx_count", 0),
        "get_balance": lambda d: (d.get("chain_stats", {}).get("funded_txo_sum", 0)
                                  - d.get("chain_stats", {}).get("spent_txo_sum", 0)) / 1e8
    },
    # --- CryptoID ---
    {
        "name": "CryptoID",
        "url_template": "https://chainz.cryptoid.info/btc/api.dws?q=getbalance&a={}",
        "get_txcount": lambda d: 0,
        "get_balance": lambda d: float(d) if isinstance(d, (int, float, str)) else 0
    },
    # --- BitIndex ---
    {
        "name": "BitIndex",
        "url_template": "https://api.bitindex.network/api/v3/main/addr/{}",
        "get_txcount": lambda d: d.get("txApperances", 0),
        "get_balance": lambda d: d.get("balanceSat", 0) / 1e8
    },
    # --- Whatsonchain (BSV-compatible, fallback only) ---
    {
        "name": "Whatsonchain",
        "url_template": "https://api.whatsonchain.com/v1/bsv/main/address/{}/balance",
        "get_txcount": lambda d: 0,
        "get_balance": lambda d: float(d.get("confirmed", 0)) / 1e8
    },
]


# --- GLOBALNY STAN ---
DISABLED_APIS = {}  # {name: datetime_odblokowania}


# --------------------------
# Pomocnicze funkcje
# --------------------------

def log_error(msg):
    with open(ERRORS_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {msg}\n")


def disable_api_temporarily(api_name, reason):
    until = datetime.now() + timedelta(minutes=COOLDOWN_MINUTES)
    DISABLED_APIS[api_name] = until
    print(Fore.RED + f"    🚫 API {api_name} wyłączone do {until.strftime('%H:%M:%S')} ({reason})", flush=True)
    log_error(f"DISABLED {api_name} until {until} ({reason})")


def get_active_apis():
    now = datetime.now()
    active = []
    for api in API_PROVIDERS:
        if api["name"] in DISABLED_APIS:
            if now >= DISABLED_APIS[api["name"]]:
                print(Fore.YELLOW + f"    ✅ API {api['name']} ponownie aktywne", flush=True)
                del DISABLED_APIS[api["name"]]
                active.append(api)
        else:
            active.append(api)
    return active


def load_checkpoint():
    if not os.path.exists(CHECKPOINT_FILE):
        return 0
    try:
        return int(open(CHECKPOINT_FILE, "r", encoding="utf-8").read().strip() or 0)
    except Exception:
        return 0


def save_checkpoint(idx):
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        f.write(str(idx))


# --------------------------
# Sieć / API
# --------------------------

def request_with_backoff(url, api_name, max_retries=3):
    wait = 1.5
    for attempt in range(max_retries):
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        try:
            resp = requests.get(url, timeout=12, headers=headers)
            if resp.status_code == 200:
                return resp.json(), 200
            elif resp.status_code == 429:
                disable_api_temporarily(api_name, "HTTP 429 (ban)")
                return None, 429
            elif 500 <= resp.status_code < 600:
                disable_api_temporarily(api_name, f"HTTP {resp.status_code}")
                return None, resp.status_code
            else:
                log_error(f"HTTP{resp.status_code} {api_name}")
        except requests.RequestException as e:
            disable_api_temporarily(api_name, f"connection error {e}")
            log_error(f"REQERR {api_name} -> {e}")
            return None, None
        time.sleep(wait)
        wait *= 2
    return None, None


def check_address(address):
    apis = get_active_apis()
    if not apis:
        print(Fore.RED + "    ❌ Brak aktywnych API, czekam 2 minuty...", flush=True)
        time.sleep(120)
        return None, None, None

    random.shuffle(apis)
    for api in apis:
        url = api["url_template"].format(address)
        print(Style.DIM + f"    → sprawdzam przez {api['name']}...", flush=True)
        data, status = request_with_backoff(url, api["name"])
        if not data:
            continue
        try:
            txcount = api["get_txcount"](data)
            balance = api["get_balance"](data)
        except Exception:
            txcount, balance = 0, 0.0
        return txcount, balance, api["name"]
    return None, None, None


# --------------------------
# Główna pętla
# --------------------------

def main():
    if not os.path.exists(DB_FILE):
        print(Fore.RED + f"[🚫] Brak bazy {DB_FILE}")
        return

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM generated")
    total = cur.fetchone()[0]
    start_idx = load_checkpoint()

    print(Fore.YELLOW + f"[ℹ] Znaleziono {total} adresów BTC w bazie. Start od {start_idx}.\n")

    cur.execute("SELECT address FROM generated LIMIT -1 OFFSET ?", (start_idx,))
    rows = cur.fetchall()

    for idx, (addr,) in enumerate(rows, start=start_idx):
        print(Fore.CYAN + f"[{idx+1}/{total}] Sprawdzam: {addr}")

        txcount, balance, api_name = check_address(addr)

        if txcount is None:
            print(Fore.RED + f"    ⚠️ Nie udało się pobrać danych dla {addr}\n", flush=True)
            log_error(f"ALL_FAILED {addr}")
        elif txcount == 0 and balance == 0:
            print(Style.DIM + f"    0 — brak transakcji / saldo 0 BTC ({api_name})\n", flush=True)
        else:
            print(Fore.GREEN + f"    💰 {balance:.8f} BTC — {txcount} tx ({api_name})\n", flush=True)
            with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                f.write(f"{addr}  |  {balance:.8f} BTC  |  {txcount} tx  |  API:{api_name}\n")

        save_checkpoint(idx + 1)
        print(Style.DIM + f"    (checkpoint zapisany: {idx+1})", flush=True)

        delay = MIN_DELAY + random.uniform(0.0, 2.0)
        print(Style.DIM + f"    ⏳ Odczekuję {delay:.1f}s...\n", flush=True)
        time.sleep(delay)

    conn.close()
    print(Fore.GREEN + "[🏁] Skończono. Wszystkie adresy BTC sprawdzone!")


if __name__ == "__main__":
    main()
