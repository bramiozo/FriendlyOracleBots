import os
# from telegram import Bot, Update
import telebot
from os.path import join, dirname
from dotenv import load_dotenv
import asyncio
import requests
import threading
import yaml
from collections import defaultdict
import pprint

dotenv_path = join(dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

# TODO: should handle multiple users/conversations -> CHAT_MEMORY should be a dict
# TODO: should only be accessible to authorized users

OPENAI_KEY = os.environ.get('OPENAI_KEY')
OPENAI_ORG_KEY = os.environ.get('OPENAI_ORG_KEY')
BOT_KEY = os.environ.get('BOT_KEY_DutchieDutch_bot')

with open(join(dirname(__file__), '..', 'assets', 'llm_settings.yml'), 'r') as llm_settings:
    settings = yaml.safe_load(llm_settings)

with open(join(dirname(__file__), '..', 'assets', 'telegram.yml'), 'r') as telegram_settings:
    telegram_settings = yaml.safe_load(telegram_settings)

allowed_users = telegram_settings['allowed_users']
bot = telebot.TeleBot(BOT_KEY)

CHAT_MEMORY = defaultdict(str)
GLOBAL_INTERACTION_ID = defaultdict(int)

########################
### helper functions ##
########################


def check_user(
    message): return True if message.from_user.username in allowed_users.keys() else False

########################
### pre-set responses ##
########################


@bot.message_handler(commands=['Greet'], func=check_user)
def greet(message):
    bot.reply_to(message, "Hey! Hows it going?")


@bot.message_handler(commands=['hello'], func=check_user)
def hello(message):
    bot.send_message(message.chat.id, "Hello!")


@bot.message_handler(commands=['masha'], func=check_user)
def masha(message):
    bot.send_message(message.chat.id, "Mijn liefste!")


@bot.message_handler(commands=['whoami'], func=check_user)
def whoami(message):
    bot.send_message(
        message.chat.id, "I am a bulbabot created by Masha and Bram!")


@bot.message_handler(commands=['reset'], func=check_user)
def reset(message):
    global CHAT_MEMORY
    CHAT_MEMORY[message.from_user.username] = ""
    bot.send_message(
        message.chat.id, "I forgot everything, who are you again?")

########################
### Open responses #####
########################


def get_llm_response(input_text):
    response_json = requests.post('https://api.openai.com/v1/chat/completions', headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OPENAI_KEY}',
        'OpenAI-Organization': OPENAI_ORG_KEY
    }, json={
        'model': 'gpt-4',
        'messages': [
            {"role": "system",
                "content": settings['system_prompts']['dutchie_dutch']['who_am_i']},
            {"role": "user", "content": input_text}],
        'max_tokens': 300,
        'temperature': 0.9,
        'top_p': 1,
        'n': 1,
    }).json()
    try:
        response = response_json['choices'][0]['message']['content'].strip()
    except Exception as e:
        pprint.pprint(response_json)
        raise e

    return response

# TODO: add func that asserts the message is proper


@bot.message_handler(func=check_user)
def llm_response(message):
    text = message.text
    username = message.from_user.username

    global CHAT_MEMORY
    global GLOBAL_INTERACTION_ID

    if GLOBAL_INTERACTION_ID[username] == 0:
        text = f"Hi I am {allowed_users[username]['name']} from {allowed_users[username]['country_of_origin']}"

    CHAT_MEMORY[username] += "USER: " + text + "\n"

    response_text = get_llm_response(CHAT_MEMORY[username])

    CHAT_MEMORY[username] += response_text + "\n\n"
    GLOBAL_INTERACTION_ID[username] += 1

    bot.reply_to(message, response_text)


bot.polling()
