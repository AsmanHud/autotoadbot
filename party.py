import argparse
from pyrogram import Client
import json
import time

with open("data.json", "r") as f:
    data = json.load(f)

accounts = data["accounts"]

parser = argparse.ArgumentParser()
parser.add_argument("account_names", nargs="+")
args = parser.parse_args()

for account_name in args.account_names:
    with Client(
        "frogbot_" + account_name,
        accounts[account_name]["api_id"],
        accounts[account_name]["api_hash"],
    ) as app:
        app.send_message(data["chat_id"], "Жабу на тусу")

    time.sleep(3)


"""
python party.py account_name1 account_name2 account_name3...
"""
