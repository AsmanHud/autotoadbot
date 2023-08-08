# v2.1 STABLE
# - Manual entering of delta values

# v2.2
# - Entering of delta values is now automated
# - Main delay between messages is increased from 1 minute to 2 minutes
# NOTES:
# x) parse_delta does not parse correctly different states of the Жаба инфо
# x) Improve overall code structure (redundancy and etc):
# x) Get rid of unnecesary time.sleeps and add where it could be necessary
# x) Get rid of slowed_accounts restriction (or apply it to all accounts)
# x) Figure out if you can delete all planned messages (target them specifically)

# To-do list
# - [x] Reinitialize rostikalt2 (Серик)
# - [x] Rename hash_id to api_hash (in the script and in data.json)
# - [x] Automate entering work_delta and feed_delta

# - Make the work/feed message generation better by including
# all possible Жаба инфо messages:
# - [x] Toad is not working/cannot be fed right now, and is not available
# (there is a timer which states when toad can be sent to work/fed)
# - [ ] Toad can be sent to work/fed right now
# - [ ] Toad can be taken from work/fed right now
# - [ ] Toad is working, but not available to take from work
# (there is a timer that states when toad can be taken from work)
# (currently it is treated as the cooldown before toad can be sent to work)

# - [ ] Delete all residual messages sent by bot to keep the chat clean
# - [ ] Maybe add cooldown between each accounts' execution? (determine if needed)
# - [ ] If possible, get rid of slowed accounts slowdown

# Maybe in future
# - Maybe it is possible to find the latest scheduled message(s)
# and based on those manage start time values
# instead of manually deleting all scheduled messages before running the script
# - Maybe add more functionality, like caring about little toad


from datetime import datetime, timedelta
from pyrogram import Client, errors
import time
import json
import argparse

WORK_MESSAGE = "Поход в столовую"
DELAY = 2  # seconds, main delay between messages
SLOWED_ACCOUNTS = [
    "rostikalt",
    "rostikalt2",
    "danikalt2",
    "asmanalt2",
    "asmanalt3",
]
SLOWED_ACCOUNTS_SLEEP_PER_MESSAGE_SCHEDULED = 0.1  # seconds
SCHEDULED_MESSAGES_LIMIT = 100
with open("data.json", "r") as f:
    data = json.load(f)
ACCOUNTS = data["accounts"]
CHAT_ID = data["chat_id"]


def extract_numeric_values(line):
    num_vals = []
    i = 0
    while i < len(line):
        if line[i].isdigit():
            num_val = ""
            while line[i].isdigit() and i < len(line):
                num_val += line[i]
                i += 1
            num_vals.append(num_val)
        i += 1
    return [int(x) for x in num_vals]


def parse_toad_info(raw_toad_info):
    work_line, feed_line = raw_toad_info.split("\n")[:2]
    work_delta_vals = extract_numeric_values(work_line)
    feed_delta_vals = extract_numeric_values(feed_line)
    if not work_delta_vals:
        work_delta_vals = [0, 0]
    if not feed_delta_vals:
        feed_delta_vals = [0, 0]
    work_delta = timedelta(hours=work_delta_vals[0], minutes=work_delta_vals[1])
    feed_delta = timedelta(hours=feed_delta_vals[0], minutes=feed_delta_vals[1])
    return work_delta, feed_delta


def calc_gen_days(work_message, is_premium, fotd):
    messages_per_day = 8
    if is_premium:
        messages_per_day += 2
    elif work_message == "Работа грабитель":
        messages_per_day += 3
    if fotd:
        messages_per_day += 1
    return SCHEDULED_MESSAGES_LIMIT // messages_per_day


def genwork(start_time, is_premium, work_message, gendays):
    messages = []
    current_time = start_time  # datetime object
    for _ in range(gendays * 3):
        messages.append([work_message, current_time])
        current_time += timedelta(hours=2, minutes=DELAY)
        messages.append(["Завершить работу", current_time])
        current_time += timedelta(hours=6)
        if not is_premium and work_message == "Работа грабитель":
            current_time -= timedelta(minutes=DELAY)
            messages.append(["Реанимировать жабу", current_time])
            current_time += timedelta(minutes=DELAY)
    return messages


def genfeed(start_time, is_premium, gendays):
    messages = []
    k_prem = 2 if is_premium else 1
    current_time = start_time  # datetime object
    for _ in range(gendays * 2 * k_prem):
        messages.append(["Покормить жабу", current_time])
        current_time += timedelta(hours=12 // k_prem, minutes=DELAY)
    return messages


def genfotd(start_time, gendays):
    messages = []
    current_time = start_time
    for _ in range(gendays):
        messages.append(["Жаба дня", current_time])
        current_time += timedelta(days=1)
    return messages


def main(account_names, fotd):
    for account_name in account_names:
        bot = Bot(account_name)
        # get is_premium from accounts.json
        is_premium = ACCOUNTS[account_name]["is_premium"]
        data = bot.get_data()
        now = datetime.now()
        work_start_time = now + data["work_delta"] + timedelta(minutes=2)
        feed_start_time = now + data["feed_delta"] + timedelta(minutes=2)
        gen_days = calc_gen_days(
            WORK_MESSAGE,
            is_premium,
            fotd,
        )
        # start generating messages
        messages = []
        messages += genwork(
            work_start_time,
            is_premium,
            WORK_MESSAGE,
            gen_days,
        )
        messages += genfeed(
            feed_start_time,
            is_premium,
            gen_days,
        )
        if fotd:
            fotd_start_time = now + timedelta(days=1)
            fotd_start_time = fotd_start_time.replace(hour=0, minute=0, second=0)
            messages += genfotd(
                fotd_start_time,
                gen_days,
            )
        messages.sort(key=lambda x: x[1])
        bot.execute(messages)


class Bot:
    def __init__(self, account_name):
        self.account_name = account_name
        self.api_id = ACCOUNTS[account_name]["api_id"]
        self.api_hash = ACCOUNTS[account_name]["api_hash"]
        self.session_name = "frogbot_" + account_name
        self.chat_id = CHAT_ID

    def execute(self, messages):
        with Client(self.session_name, self.api_id, self.api_hash) as app:
            for message in messages:
                message_text, schedule_time = message
                try:
                    app.send_message(
                        self.chat_id, message_text, schedule_date=schedule_time
                    )
                    if self.account_name in SLOWED_ACCOUNTS:
                        time.sleep(SLOWED_ACCOUNTS_SLEEP_PER_MESSAGE_SCHEDULED)
                except errors.FloodWait as e:
                    if e.value > 10:
                        return
                    print(f"Flood wait for {e.value} seconds")
                    time.sleep(e.value)
                except errors.ScheduleTooMuch as e:
                    print(f"{e}\nAccount: {self.account_name}")
                    return

    def get_data(self):
        data = {}
        with Client(self.session_name, self.api_id, self.api_hash) as app:
            app.send_message(self.chat_id, "Завершить работу")
            time.sleep(0.1)
            app.send_message(self.chat_id, "Жаба инфо")
            for _ in range(10):
                time.sleep(0.1)
                toad_info_message = next(app.get_chat_history(self.chat_id, limit=1))
                if "🏃‍♂️" in toad_info_message.text:
                    break
            else:
                print("Runtime error. Couldn't receive the toad info")
                raise RuntimeError
            toad_info = toad_info_message.text
            work_delta, feed_delta = parse_toad_info(toad_info)
            data["work_delta"] = work_delta
            data["feed_delta"] = feed_delta
        return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process the input for frog bot.")
    parser.add_argument(
        "account_names",
        type=str,
        nargs="+",
        help="The name(s) of the account(s), separated by commas",
    )
    parser.add_argument(
        "--fotd",
        action="store_true",
        default=False,
        help="Whether to generate fotd messages (add --fotd to the end of the command for True, else just don't add anything)",
    )
    args = parser.parse_args()
    main(args.account_names, args.fotd)


"""
General prompt structure:
python frog_v2.1.py account1 account2... --fotd
Some common prompts
python frog_v2.1.py 
python frog_v2.1.py asmanmain
python frog_v2.1.py asmanalt --fotd
python frog_v2.1.py danikalt
python frog_v2.1.py rostikalt
python frog_v2.1.py rostikalt2
python frog_v2.1.py asmanalt2
python frog_v2.1.py asmanalt3
"""
