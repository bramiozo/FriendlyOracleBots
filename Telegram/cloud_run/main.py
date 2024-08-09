import argparse
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from pydantic.dataclasses import dataclass
from typing import List
from telegram import Bot, Update, Message
from telegram.ext import Application, MessageHandler, filters, CallbackContext, Updater
import httpx
from tenacity import retry, stop_after_attempt, wait_fixed
import threading
import os
import yaml
from collections import defaultdict
from os.path import join, dirname
from sys import argv
from dotenv import load_dotenv, find_dotenv

from time import sleep
from uvicorn import run
from multiprocessing import Process
import pydub
import random

# add logger
import logging
logger = logging.getLogger(__name__)


# get directory from absolute path
# BASEDIR = os.path.dirname(argv[0])
# dotenv_path = join(find_dotenv(), '.env')
# load_dotenv(dotenv_path)


OPENAI_MODEL = os.environ.get('OPENAI_MODEL', default='gpt-4-1106-preview')
OPENAI_KEY = os.environ.get('OPENAI_KEY')
OPENAI_ORG_KEY = os.environ.get('OPENAI_ORG_KEY')
BOT_KEY = os.environ.get('BOT_KEY')
BOT_NAME = os.environ.get('BOT_NAME')
PORT = int(os.environ.get('PORT', 80))

'''
security: anyone can invoke the bot and fire up the cloud run instance.
filtering: takes place in the bot itself.
'''


class TelegramUpdate(BaseModel):
    update_id: int
    message: dict


class Context(BaseModel):
    bot: Bot
    update: Update
    args: list
    job_queue: object
    chat_data: dict
    user_data: dict
    bot_data: dict
    matches: List

    class Config:
        arbitrary_types_allowed = True


with open(join(dirname(__file__), 'assets', 'llm_settings.yml'), 'r') as llm_settings:
    settings = yaml.safe_load(llm_settings)

with open(join(dirname(__file__), 'assets', 'telegram.yml'), 'r') as telegram_settings:
    telegram_settings = yaml.safe_load(telegram_settings)

with open(join(dirname(__file__), 'assets', 'connection.yml'), 'r') as connection_settings:
    connection_settings = yaml.safe_load(connection_settings)


NUM_RETRIES = connection_settings['retry']['number']
RETRY_WAIT = connection_settings['retry']['wait']

TIMEOUT_CONNECT = connection_settings['timeout']['connect']
TIMEOUT_READ = connection_settings['timeout']['read']
TIMEOUT_WRITE = connection_settings['timeout']['write']
TIMEOUT_POOL = connection_settings['timeout']['pool']

CHAT_MEMORY = defaultdict(str)
GLOBAL_INTERACTION_ID = defaultdict(int)

timeout = httpx.Timeout(connect=TIMEOUT_CONNECT,
                        read=TIMEOUT_READ,
                        write=TIMEOUT_WRITE,
                        pool=TIMEOUT_POOL)


allowed_users = telegram_settings['allowed_users']

app = FastAPI()
bot = Bot(token=BOT_KEY)


@app.post("/{token}")
async def process_update(token: str,
                         telegram_update: TelegramUpdate):  # context: Context
    if token != BOT_KEY:
        raise HTTPException(status_code=403, detail="Invalid token")

    update = Update.de_json(telegram_update.dict(), bot)
    if update and update.message:
        if update.message.from_user.username not in allowed_users:
            raise HTTPException(status_code=403, detail="Unauthorized user")

        # BOT_NAME = telegram_settings['allowed_users'][update.message.from_user.username]['allowed_bot']

        if isinstance(update.message.text, str):
            username = update.message.from_user.username
            if GLOBAL_INTERACTION_ID[username] == 0:
                user_input = f"Hi I am {allowed_users[username]['name']}\
                from {allowed_users[username]['country_of_origin']}\n"+update.message.text
            else:
                user_input = update.message.text

            CHAT_MEMORY[username] += "USER: " + update.message.text + "\n"

            username = update.message.from_user.username

            response_text = await fetcher(base_llm, user_input, username)
            GLOBAL_INTERACTION_ID[username] += 1

            await bot.send_message(chat_id=update.message.chat_id, text=response_text)
        elif update.message.voice.file_id is not None:
            audio_file_id = "EMPTY"
            username = "EMPTY"
            user_text = "EMPTY"
            response_text = "EMPTY"
            try:
                audio_file_id = await bot.get_file(update.message.voice.file_id)
                username = update.message.from_user.username

                user_text = await fetcher(base_transcription, audio_file_id, username)

                if type(user_text) == str:
                    CHAT_MEMORY[username] += "USER: " + user_text + "\n"
                else:
                    # logger.error(f"User text is not a string: {user_text}")
                    user_text = f"""<ERROR ID=1>The user tried to upload an audio transcription using Whisper, 
                    but it failed. The user_text is given by: {user_text}</ERROR>"""
                    CHAT_MEMORY[username] += "USER: " + user_text + "\n"

                response_text = await fetcher(base_llm, user_text, username)

                GLOBAL_INTERACTION_ID[username] += 1
                await bot.send_message(chat_id=update.message.chat_id, text=response_text)

            except Exception as e:
                await bot.send_message(chat_id=update.message.chat_id,
                                       text=f"Sorry, I couldn't understand that. \
                                       I am having some issues with the audio file.\r\n \
                                       audio_file_id: {audio_file_id}\r\n \
                                       username: {username}\r\n \
                                       user_text: {user_text}\r\n \
                                       response_text: {response_text}\r\n \
                                       \r\n Exception: {e}")
        else:
            await bot.send_message(chat_id=update.message.chat_id,
                                   text=f"I don't understand that. \
Was that a picture? I don\'t understand pictures yet.\
The type of the message is {type(update.message.text)}")

    return {"ok": "POST request processed"}


# get query to print out the chat memory
@app.get("/debug")
async def chat():
    return {"ok": CHAT_MEMORY}


@app.get("/allowedusers")
async def allowedusers():
    return {"ok": allowed_users}


# Upload PDF/DOCX file to Google Cloud Storage

# Parse PDF/DOCX file to text

# Parse chunks of text to OpenAI-embeddings

# Store embeddings in


async def base_transcription(file_id, username):
    assert BOT_NAME in settings['system_prompts'].keys(
    ), f"BOT_NAME {BOT_NAME} not in settings"

    try:
        audio_file = await bot.get_file(file_id)
        # await bot.download_file(audio_file.file_path)
        file_location = audio_file.file_path

        # output = random.randint(9999, 99999)
        await audio_file.download_to_drive(file_location)
        sound = await pydub.AudioSegment.from_file(file_location)
        sound.export(f"{username}_{file_id}.wav", format="wav")
        # This file needs to be removed after the transcription is done...

    except:
        text = f"<ERROR ID=2>Sorry: failed to get audio file with id {file_id}.\r\n \
            The file location is {file_location}.\r\n \
    The error message is: {e} \
    </ERROR>"

    sleep(1)
    try:
        with open(f"{username}_{file_id}.wav", 'rb') as f:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post('https://api.openai.com/v1/audio/transcriptions',
                                             headers={
                                                 'Content-Type': 'multipart/form-data',
                                                 'Authorization': f'Bearer {OPENAI_KEY}',
                                                 'OpenAI-Organization': OPENAI_ORG_KEY
                                             }, files={
                                                 'file': f
                                             },
                                             data={'model': 'whisper-1'
                                                   }
                                             )
    except Exception as e:
        text = f"<ERROR ID=3>Sorry, I am having some issues. \
                    This is what I got: {e}</ERROR>"

    try:
        text = response.json()['text'].strip()
    except Exception as e:
        text = f"<ERROR ID=4>Sorry, I couldn't understand that. I am having some issues. \
                    This is what I got: {str(response.json())}</ERROR>"

    CHAT_MEMORY[username] += "Dutch: \n" + text + "\n\n"
    return text


async def base_llm(input_text, username):
    assert BOT_NAME in settings['system_prompts'].keys(
    ), f"BOT_NAME {BOT_NAME} not in settings"
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post('https://api.openai.com/v1/chat/completions', headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {OPENAI_KEY}',
            'OpenAI-Organization': OPENAI_ORG_KEY
        }, json={
            # f"'{OPENAI_MODEL}'",  'gpt-3.5-turbo-1106'
            'model': 'gpt-4-1106-preview',
            'messages': [
                {'role': 'system',
                 'content': f'{settings["system_prompts"][BOT_NAME]["who_am_i"]}'
                 },
                {'role': 'user',
                 'content': CHAT_MEMORY[username] + "\n\n" + input_text + "\n"
                 }

            ],
            'max_tokens': 512,
            'temperature': 0.75
        })
    try:
        text = response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        text = f"<ERROR ID=5>Sorry, I couldn't understand that. I am having some issues. \
        This is what I got; \n\
model= {OPENAI_MODEL}, \n\
OPENAI_KEY= {OPENAI_KEY}, \n\
OPENAI_ORG_KEY= {OPENAI_ORG_KEY}, \n\
BOT_KEY= {BOT_KEY}, \n\
chat_memory= {CHAT_MEMORY[username]},\n \
error-> {str(response.json())}</ERROR>"

    CHAT_MEMORY[username] += "Dutch: \n" + str(text) + "\n\n"
    return text


@retry(stop=stop_after_attempt(NUM_RETRIES), wait=wait_fixed(RETRY_WAIT))
async def fetcher(operation, *args, **kwargs):
    try:
        return await operation(*args, **kwargs)
    except httpx.ConnectTimeout as e:
        return f"Aborting: connection timeout exceeded; {e}"
    except httpx.ReadTimeout as e:
        return f"Aborting: read timeout exceeded; {e}"
    except httpx.WriteTimeout as e:
        return f"Aborting: write timeout exceeded; {e}"
    except httpx.HTTPStatusError as e:
        return f"Aborting, HTTP status: {e}"
    except Exception as e:
        return f"An error occurred: {e}"

if __name__ == "__main__":
    run("main:app", host="0.0.0.0", port=PORT, log_level="info", reload=True)
