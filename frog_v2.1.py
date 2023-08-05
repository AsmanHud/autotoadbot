from datetime import datetime, timedelta
from pyrogram import Client, errors
import time
import json
import argparse


class Bot:
    def __init__(self, account_name):
        self.account_name = account_name
        self.api_id = ACCOUNTS[account_name]["api_id"]
        self.hash_id = ACCOUNTS[account_name]["hash_id"]
        self.session_name = "frogbot_" + account_name
        self.chat_id = CHAT_ID

    def execute(self, messages):
        with Client(self.session_name, self.api_id, self.hash_id) as app:
            for message in messages:
                message_text, schedule_time = message
                try:
                    app.send_message(
                        self.chat_id, message_text, schedule_date=schedule_time
                    )
                    if self.account_name in SLOWED_ACCOUNTS:  # DELETE THIS IN FUTURE
                        time.sleep(
                            SLOWED_ACCOUNTS_SLEEP_PER_MESSAGE_SCHEDULED
                        )  # DELETE THIS IN FUTURE
                except errors.FloodWait as e:
                    if e.value > 10:
                        return
                    print(f"Flood wait for {e.value} seconds")
                    time.sleep(e.value)
                except errors.ScheduleTooMuch as e:
                    print(f"{e}\nAccount: {self.account_name}")
                    return


DELAY = 2  # seconds, main delay between messages
SLOWED_ACCOUNTS = [
    "rostikalt",
    "rostikalt2",
    "danikalt2",
    "asmanalt2",
    "asmanalt3",
]  # DELETE THIS IN FUTURE
SLOWED_ACCOUNTS_SLEEP_PER_MESSAGE_SCHEDULED = 0.1  # seconds # DELETE THIS IN FUTURE
SCHEDULED_MESSAGES_LIMIT = 100


with open("data.json", "r") as f:
    data = json.load(f)
ACCOUNTS = data["accounts"]
CHAT_ID = data["chat_id"]


def calc_gen_days(work_message, is_premium, fotd):
    messages_per_day = 8
    if is_premium:
        messages_per_day += 2
    elif work_message == "Работа грабитель":
        messages_per_day += 3
    if fotd:
        messages_per_day += 1
    return SCHEDULED_MESSAGES_LIMIT // messages_per_day


def parse_delta(delta_raw):
    hours, minutes = delta_raw.split(":")
    hours = int(hours)
    minutes = int(minutes)
    return timedelta(hours=hours, minutes=minutes)


def genwork(start_time, is_premium, work_message, gendays):
    messages = [["Завершить работу", datetime.now()]]
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


def main(account_names_raw, work_delta, feed_delta, fotd):
    account_names = account_names_raw.split(",")
    multaccdelay = 0
    for account_name in account_names:
        bot = Bot(account_name)
        # get is_premium from accounts.json
        is_premium = ACCOUNTS[account_name]["is_premium"]
        now = datetime.now()
        work_start_time = (
            now + parse_delta(work_delta) + timedelta(minutes=multaccdelay)
        )
        feed_start_time = (
            now + parse_delta(feed_delta) + timedelta(minutes=multaccdelay)
        )
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
        multaccdelay += 5


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process the input for frog bot.")
    parser.add_argument(
        "account_names_raw",
        type=str,
        help="The name(s) of the account(s), separated by commas",
    )
    parser.add_argument(
        "work_delta",
        type=str,
        help="Go to work delta, in the format HH:MM",
    )
    parser.add_argument(
        "feed_delta",
        type=str,
        help="Feed delta, in the format HH:MM",
    )
    parser.add_argument(
        "--fotd",
        action="store_true",
        default=False,
        help="Whether to generate fotd messages (add --fotd to the end of the command for True, else just don't add anything)",
    )
    args = parser.parse_args()
    WORK_MESSAGE = "Работа грабитель"
    main(args.account_names_raw, args.work_delta, args.feed_delta, args.fotd)


"""
General prompt structure:
python frog_v2.1.py account1,account2... work_delta feed_delta --fotd
Some common prompts
python frog_v2.1.py 
python frog_v2.1.py asmanmain 00:00 00:00
python frog_v2.1.py asmanalt 5:51 3:7 --fotd
python frog_v2.1.py rostikalt,rostikalt2,asmanalt2 5:10 12:00
"""
