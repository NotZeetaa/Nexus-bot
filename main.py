from typing import Final
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import os
from datetime import datetime
import re
import logging

logging.basicConfig(level=logging.INFO)

# Use environment variables for sensitive information
TELEGRAM_TOKEN: Final = os.getenv("TELEGRAM_TOKEN")
BOT_USERNAME: Final = os.getenv("BOT_USERNAME")
GT_TOKEN: Final = os.getenv("GT_TOKEN")
REPO_OWNER: Final = "NotZeetaa"
REPO_NAME: Final = "cirrus-ci"
REPO_URL: Final = f"https://{GT_TOKEN}@github.com/{REPO_OWNER}/{REPO_NAME}"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello! Thanks for chatting with me!')

async def clone_repository():
    os.system(f'git clone {REPO_URL}')
    repo_name = REPO_URL.split('/')[-1].split('.')[0]
    os.chdir(repo_name)

async def replace_string_in_setup(device: str):
    pattern = re.compile(r'bash build\.sh null {}\s+lto'.format(re.escape(device)))
    
    with open('setup.sh', 'r') as file:
        content = file.read()
        if pattern.search(content):
            content = pattern.sub(f'bash build.sh null {device} null', content)
            normal = True
        else:
            logging.info('No')
            normal = False

    with open('setup.sh', 'w') as file:
        file.write(content)
    
    return normal   

async def handle_git_operations(device: str, command: str):
    await clone_repository()
    os.system(f'git switch {device}')
    os.system('git fetch origin')
    os.system('git pull')
    normal = await replace_string_in_setup(device)
    if command == 'lto':
        os.system(f'sed -i "s/bash build.sh null {device} null/bash build.sh null {device} lto/g" setup.sh')
        os.system('git add .')
        os.system('git commit -s -m "LTO build"')
    else:
        if normal:
            os.system('git add .')
            os.system('git commit -s -m "Normal build"')
            os.system('git push')
        else:
            os.system('git commit -s -m "Automatic run" --allow-empty') 
    os.system('git push')

async def handle_response(update: Update, command: str, original_text: str, arguments: list):
    device_mapping = {
        'alioth': 'alioth device',
        'apollo': 'apollo device',
        'lmi': 'lmi device',
        'munch': 'munch device',
    }

    now = datetime.now()
    date_time = now.strftime("%H:%M:%S")

    if command in device_mapping:
        device = device_mapping[command]
        await handle_git_operations(command, device)
        await update.message.reply_text(f'[{date_time}] Build Started to {device}!')

    elif command == 'all':
        await handle_git_operations('main')
        await update.message.reply_text(f'[{date_time}] Build Started to all devices!')

    elif command == 'gm':
        await update.message.reply_text(f'[{date_time}] Let me sleep!')

    elif command == 'gn':
        await update.message.reply_text(f'[{date_time}] Good night!')
        
    elif command == 'lto':
        if arguments:
            device = arguments[0]
            if device in device_mapping:
                await handle_git_operations(device, command)
                await update.message.reply_text(f'[{date_time}] LTO build for {device}!')
            else:
                await update.message.reply_text(f'[{date_time}] Invalid device argument for LTO command.')
        else:
            await update.message.reply_text(f'[{date_time}] Missing device argument for LTO command.')

    elif command == 'server':
        # Modify the server response to handle both Windows and Linux
        platform = os.name  # 'posix' for Linux, 'nt' for Windows
        if platform == 'posix':
            await update.message.reply_text(f'[{date_time}] Server is running on my Linux machine!')
        elif platform == 'nt':
            await update.message.reply_text(f'[{date_time}] Server is running on my Windows machine!')
        else:
            await update.message.reply_text(f'[{date_time}] Server information not available.')

    else:
        await update.message.reply_text(f'[{date_time}] No device found!')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type
    text: str = update.message.text

    print(f'User ({update.message.chat.id}) in {message_type}: "{text}"')

    if message_type == 'supergroup' and BOT_USERNAME in text:
        # Extract command and arguments
        parts = text.split()
        command = parts[1].lower() if len(parts) > 1 else None
        arguments = parts[2:] if len(parts) > 2 else []

        if command:
            await handle_response(update, command, text, arguments)


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f'Update {update} caused error {context.error}')

if __name__ == '__main__':
    logging.info('Starting bot...')
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.add_error_handler(error)

    logging.info('Polling...')
    app.run_polling(poll_interval=3)