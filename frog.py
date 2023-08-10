# Added in 2.3 update:
# - Now there is an option to synchronize times when accounts are
# sent to work (technically it works for the feed times as well,
# but there feed times will not be synced properly if some of the accounts are premium,
# and some are not).

# - Moved work message from constants to argparser,
# (the default is "Работа грабитель", and you can optionally add this argument
# to change the work message if you would like)

# - Now there is an option to manually enter absolute start work time and
# absolute feed start time, if needed. (though, mostly you won't need it)

# - Finally removed the slowed accounts restriction, and ran the script
# on 5 accounts at the same time (sync on), everything seems to work fine

# - Added "Покормить жабу" with the "Завершить работу" to the get_data
# functionality, so feed delta parsing is now 100% correct

# !(did not test this yet) - Fixed the healing functionality,
# by moving the healing block in genwork for loop to the top of the loop,
# so now it will heal before the first instance of going to work as well

# - Redid the notes system (Update info + NOTES + to-do list + in the future),
# renamed the frog script to just frog.py.
# Now the commit message should just include the version number of the update


# NOTES:
# x) About the parse_data (specifically, work_delta)
# For now, decided that the work delta value parsing is more or less fine
# how it is, even if the toad was on work during the script running,
# it would just mistakenly try to send the toad to work and get it from work
# one time, and in other messages, it would work properly
# Trying to rewrite the genwork function to fix such minor issue would
# be an overkill, and would take too much time
# x) Overall code quality could be always improved, and probably
# there are many places where code is redundant (though, it works as it is)


# To-do list
# - [ ] Add a method to a bot to delete all planned messages
# - [ ] Remove all notes from the script, and add them in a separate .md file


# Features that could be implemented in the future:
# - Maybe it would be a good measure to add a functionality to
# delete all resisual messages created by the script
# (right now it is not that difficult to delete them manually)
# - Is it possible to delete all planned messages before any execution?
# - Maybe add more functionality, like caring about little toad
# - Maybe add going to party functionality (though, it is not really needed)


from datetime import datetime, timedelta
from pyrogram import Client, errors
import time
import json
import argparse


DELAY = 2  # seconds, main delay between messages
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
        if not is_premium and work_message == "Работа грабитель":
            current_time -= timedelta(minutes=DELAY)
            messages.append(["Реанимировать жабу", current_time])
            current_time += timedelta(minutes=DELAY)
        messages.append([work_message, current_time])
        current_time += timedelta(hours=2, minutes=DELAY)
        messages.append(["Завершить работу", current_time])
        current_time += timedelta(hours=6)
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
                except errors.FloodWait as e:
                    if e.value > 30:
                        return
                    print(f"Flood wait for {e.value} seconds")
                    time.sleep(e.value)
                except errors.ScheduleTooMuch as e:
                    print(
                        f"{self.account_name}: Too many scheduled messages, going for the next account."
                    )
                    return

    def get_data(self):
        data = {}
        with Client(self.session_name, self.api_id, self.api_hash) as app:
            app.send_message(self.chat_id, "Завершить работу")
            time.sleep(0.1)
            app.send_message(self.chat_id, "Покормить жабу")
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


def main(
    account_names,
    fotd,
    work_message,
    sync_accounts,
    absolute_work_time,
    absolute_feed_time,
):
    sync_delay = 0
    if sync_accounts:
        all_data = []
        for account_name in account_names:
            bot = Bot(account_name)
            all_data.append(bot.get_data())
        work_delta = max([data["work_delta"] for data in all_data])
        feed_delta = max([data["feed_delta"] for data in all_data])
    now = datetime.now()
    if absolute_work_time is not None:
        work_start_time = datetime.strptime(absolute_work_time, "%Y-%m-%d_%H:%M")
    if absolute_feed_time is not None:
        feed_start_time = datetime.strptime(absolute_feed_time, "%Y-%m-%d_%H:%M")
    for account_name in account_names:
        bot = Bot(account_name)
        # get is_premium from accounts.json
        is_premium = ACCOUNTS[account_name]["is_premium"]
        if not sync_accounts:
            data = bot.get_data()
            work_delta = data["work_delta"]
            feed_delta = data["feed_delta"]
        if absolute_work_time is None:
            work_start_time = now + work_delta + timedelta(minutes=2 + sync_delay)
        if absolute_feed_time is None:
            feed_start_time = now + feed_delta + timedelta(minutes=2 + sync_delay)
        gen_days = calc_gen_days(
            work_message,
            is_premium,
            fotd,
        )
        # start generating messages
        messages = []
        messages += genwork(
            work_start_time,
            is_premium,
            work_message,
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
        if sync_accounts:
            sync_delay += 2


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
    parser.add_argument(
        "--work_message",
        default="Работа грабитель",
        help="If you want a different work message than Работа грабитель",
    )
    parser.add_argument(
        "--sync_accounts",
        action="store_true",
        default=False,
        help="Whether to synchronize all accounts' work and feed times with a const delay (for parties as an example)",
    )
    parser.add_argument(
        "--absolute_work_time",
        default=None,
        type=str,
        help="If you want to set an absolute work time for an account, use this argument. Format: YYYY-MM-DD_HH:MM (don't use with multiple accounts)",
    )
    parser.add_argument(
        "--absolute_feed_time",
        default=None,
        type=str,
        help="If you want to set an absolute feed time for an account, use this argument. Format: YYYY-MM-DD_HH:MM (don't use with multiple accounts)",
    )
    args = parser.parse_args()
    main(
        args.account_names,
        args.fotd,
        args.work_message,
        args.sync_accounts,
        args.absolute_work_time,
        args.absolute_feed_time,
    )


"""
General prompt structure:
python frog.py account1 account2... --fotd
Some common prompts
python frog.py 
python frog.py asmanmain
python frog.py asmanalt --fotd
python frog.py asmanalt2 asmanalt3 rostikalt rostikalt2 danikalt --sync_accounts
python frog.py asmanmain --absolute_work_time 2023-08-10_22:50
python frog.py asmanalt --fotd --absolute_work_time 2023-08-10_22:52
"""
