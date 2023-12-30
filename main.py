from typing import Final
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import os
from datetime import datetime

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

async def handle_git_operations(device: str):
    await clone_repository()
    os.system(f'git switch {device}')
    os.system('git fetch origin')
    os.system('git pull')
    os.system('git commit -s -m "Automatic run" --allow-empty')
    os.system('git push')

async def handle_response(update: Update, processed: str, original_text: str):
    device_mapping = {
        'alioth': 'alioth device',
        'apollo': 'apollo device',
        'lmi': 'lmi device',
        'munch': 'munch device',
    }

    now = datetime.now()
    date_time = now.strftime("%H:%M:%S")

    if processed in device_mapping:
        device = device_mapping[processed]
        await handle_git_operations(processed)
        await update.message.reply_text(f'[{date_time}] Build Started to {device}!')

    elif processed == 'all':
        await handle_git_operations('main')
        await update.message.reply_text(f'[{date_time}] Build Started to all devices!')

    elif processed == 'gm':
        await update.message.reply_text(f'[{date_time}] Let me sleep!')

    elif processed == 'gn':
        await update.message.reply_text(f'[{date_time}] Good night!')

    elif processed == 'server':
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

    if message_type == 'supergroup':
        if BOT_USERNAME in text:
            new_text: str = text.replace(BOT_USERNAME, '').strip()
            await handle_response(update, new_text, text)

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')

if __name__ == '__main__':
    print('Starting bot...')
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.add_error_handler(error)

    print('Polling...')
    app.run_polling(poll_interval=3)
