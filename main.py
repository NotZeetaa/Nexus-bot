from typing import Final
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import os
from datetime import datetime
import re
import psutil

import logging

# Configure the logging format and level
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


# Use environment variables for sensitive information
TELEGRAM_TOKEN: Final = os.getenv("TELEGRAM_TOKEN")
BOT_USERNAME: Final = os.getenv("BOT_USERNAME")
GT_TOKEN: Final = os.getenv("GT_TOKEN")
TELEGRAM_USER_ID: Final = os.getenv("TELEGRAM_USER_ID")
REPO_OWNER: Final = "NotZeetaa"
REPO_NAME: Final = "cirrus-ci"
REPO_URL: Final = f"https://{GT_TOKEN}@github.com/{REPO_OWNER}/{REPO_NAME}"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello! Thanks for chatting with me!')

async def clone_repository():
    os.system(f'git clone {REPO_URL}')
    repo_name = REPO_URL.split('/')[-1].split('.')[0]
    os.chdir(repo_name)
    
async def replace_branch(branch: str):
    with open('setup.sh', 'r') as file:
        content = file.read()

    # Use regular expression to find and replace the branch name
    pattern = re.compile(r'(-b\s+)(\S+)')
    updated_content = pattern.sub(r'\1' + branch, content)

    with open('setup.sh', 'w') as file:
        file.write(updated_content)

async def replace_string_in_setup(device: str):
    pattern = re.compile(r'bash build\.sh null {}\s+lto'.format(re.escape(device)))
    
    with open('setup.sh', 'r') as file:
        content = file.read()
        if pattern.search(content):
            content = pattern.sub(f'bash build.sh null {device} null', content)
            normal = True
        else:
            normal = False

    with open('setup.sh', 'w') as file:
        file.write(content)
    
    return normal   

async def handle_git_operations(device: str, command: str, branch: str):
    await clone_repository()
    os.system(f'git switch {device}')
    os.system('git fetch origin')
    os.system('git pull')
    await replace_branch(branch)
    normal = await replace_string_in_setup(device)
    if command == 'lto':
        os.system(f'sed -i "s/bash build.sh null {device} null/bash build.sh null {device} lto/g" setup.sh')
        os.system('git add .')
        os.system('git commit -s -m "LTO build" --allow-empty')
    else:
        if normal:
            os.system('git add .')
            os.system('git commit -s -m "Normal build"')
        else:
            os.system('git add .')
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
        device = command
        branch = arguments[0] if arguments else 'sched-4'
        await handle_git_operations(device, command, branch)
        await update.message.reply_text(f'[{date_time}] ⚒️ Build for {command} on branch {branch}!')

    elif command == 'all':
        await handle_git_operations('main')
        await update.message.reply_text(f'[{date_time}] ⚒️ Build Started to all devices!')

    elif command == 'gm':
        await update.message.reply_text(f'[{date_time}] Let me sleep!')

    elif command == 'gn':
        await update.message.reply_text(f'[{date_time}] Good night!')
        
    elif command == 'lto':
        if len(arguments) >= 1:
            device = arguments[0]
            branch = arguments[1] if len(arguments) >= 2 else 'sched-4'
    
            if device in device_mapping:
                await handle_git_operations(device, command, branch)
                await update.message.reply_text(f'[{date_time}] ⚒️ LTO build for {device} on branch {branch}!')
            else:
                await update.message.reply_text(f'[{date_time}] Invalid device argument for LTO command.')
        else:
            branch = 'sched-4'
            device = arguments[0] if arguments else None
    
            if device in device_mapping:
                await handle_git_operations(device, command, branch)
                await update.message.reply_text(f'[{date_time}] ⚒️ LTO build for {device} on branch {branch}!')
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

# Define a global variable to track the locked state
is_locked = False

async def handle_lock_bot_command(update: Update):
    global is_locked
    logging.info(f'The value of the variable is: {update.effective_user.id}')
    # Check if the user ID matches the one mentioned in the GitHub secret
    if str(update.effective_user.id) == TELEGRAM_USER_ID:
        is_locked = True
        await update.message.reply_text('Commands are now locked.')
    else:
        await update.message.reply_text('You are not authorized to use this command.')

async def handle_unlock_bot_command(update: Update):
    global is_locked
    # Check if the user ID matches the one mentioned in the GitHub secret
    logging.info(f'The value of the variable is: {update.effective_user.id}')
    if str(update.effective_user.id) == TELEGRAM_USER_ID:
        is_locked = False
        await update.message.reply_text('Commands are now unlocked.')
    else:
        await update.message.reply_text('You are not authorized to use this command.')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_locked

    message_type: str = update.message.chat.type
    text: str = update.message.text

    print(f'User ({update.message.chat.id}) in {message_type}: "{text}"')

    if message_type == 'supergroup':
        # Extract command and arguments
        parts = text.split()
        if parts:
            command = parts[0].lower()  # Extract command (e.g., '/build', '/gm', etc.)
            arguments = parts[1:]       # Extract arguments (if any)

            # Check if the command is one of the restricted commands and if it's locked
            if is_locked and command in ['/lock-bot', '/unlock-bot', '/build'] and str(update.effective_user.id) != TELEGRAM_USER_ID:
                await update.message.reply_text('Commands are currently locked.')
                return

            # Process the commands
            if command == '/build':
                if len(arguments) == 3 and arguments[1].lower() == 'lto':
                    await handle_lto_build_command(update, arguments)
                elif len(arguments) == 2:
                    await handle_build_command(update, arguments)
                else:
                    await update.message.reply_text('Invalid command format. Please use /build (device) (lto) (branch) or /build (device) (branch).')
            elif command == '/gm':
                await handle_generic_command(update, 'gm')
            elif command == '/gn':
                await handle_generic_command(update, 'gn')
            elif command == '/server':
                await handle_generic_command(update, 'server')
            elif command == '/all':
                await handle_generic_command(update, 'all')
            elif command == '/lock-bot':
                await handle_lock_bot_command(update)
            elif command == '/unlock-bot':
                await handle_unlock_bot_command(update)

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')

async def handle_build_command(update: Update, arguments: list):
    device = arguments[0]
    branch = arguments[1]
    
    await handle_git_operations(device, 'build', branch)
    now = datetime.now()
    date_time = now.strftime("%H:%M:%S")
    await update.message.reply_text(f'[{date_time}] Build for {device} on branch {branch}!')

async def handle_lto_build_command(update: Update, arguments: list):
    device = arguments[0]
    branch = arguments[2]
    
    await handle_git_operations(device, 'lto', branch)
    now = datetime.now()
    date_time = now.strftime("%H:%M:%S")
    await update.message.reply_text(f'[{date_time}] LTO build for {device} on branch {branch}!')

async def handle_generic_command(update: Update, command: str):
    now = datetime.now()
    date_time = now.strftime("%H:%M:%S")
    
    if command == 'gm':
        await update.message.reply_text(f'[{date_time}] Let me sleep!')
    elif command == 'gn':
        await update.message.reply_text(f'[{date_time}] Good night!')
    elif command == 'server':
        await handle_server_command(update, date_time)
    elif command == 'all':
        await handle_git_operations('main')
        await update.message.reply_text(f'[{date_time}] Build Started to all devices!')

async def handle_server_command(update: Update, date_time: str):
    platform = os.name  # 'posix' for Linux, 'nt' for Windows
    cpu_usage = psutil.cpu_percent(interval=1)
    ram_usage = psutil.virtual_memory().percent
    cpu_cores = psutil.cpu_count()

    await update.message.reply_text(f'[{date_time}] Server is running on my {platform} machine!\n\n'
                                    f'Github actions usage: \n'
                                    f'⚙️ CPU Usage: {cpu_usage}%\n'
                                    f'⚙️ RAM Usage: {ram_usage}%\n'
                                    f'⚙️ CPU Cores: {cpu_cores}')
    
if __name__ == '__main__':
    print('Starting bot...')
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.add_error_handler(error)

    print('Polling...')
    app.run_polling(poll_interval=3)