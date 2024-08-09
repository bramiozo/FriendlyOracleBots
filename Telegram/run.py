from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, MessageHandler, Filters
import requests
import threading
import os
from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

OPENAI_KEY = os.environ.get('OPENAI_KEY')
OPENAI_ORG_KEY = os.environ.get('OPENAI_ORG_KEY')
BOT_KEY = os.environ.get('BOT_KEY')

app = Flask(__name__)
bot = Bot(token=BOT_KEY)

def handle(update, context):
    text = update.message.text
    response = requests.post('https://api.openai.com/v1/engines/davinci-codex/completions', headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OPENAI_KEY}',
        'OpenAI-Organization': OPENAI_ORG_KEY
    }, json={
        'prompt': text,
        'max_tokens': 60,
    }).json()['choices'][0]['text'].strip()

    bot.send_message(chat_id=update.message.chat_id, text=response)

@app.route('/', methods=['POST'])
def webhook_handler():
    update = Update.de_json(request.get_json(force=True), bot)
    Dispatcher(bot, None).process_update(update)
    return 'ok'


if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(port=5000)).start()

    bot.set_webhook(url='https://your-cloud-run-url.run.app')


