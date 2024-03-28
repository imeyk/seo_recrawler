from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import sqlite3
import json
import os

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)
API_TOKEN = os.getenv('API_TOKEN')
if API_TOKEN is None:
    raise ValueError("Не удалось загрузить API_TOKEN для aiogram. Убедитесь, что он есть в файле .env")
else:
    print(API_TOKEN)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class Form(StatesGroup):
    name = State()
    option1 = State()
    jsonKey = State()

class SettingsForm(StatesGroup):
    param1 = State()
    param2 = State()

def validate_json(json_data):
    try:
        json.loads(json_data)
        return True
    except ValueError:
        return False

def init_db():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        name TEXT,
        option1 TEXT,
        jsonKey TEXT
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        user_id INTEGER PRIMARY KEY,
        param1 BOOLEAN,
        param2 TEXT
    )
    ''')
    conn.commit()
    conn.close()

init_db()

@dp.message_handler(commands=['start'], state='*')
async def start_command(message: types.Message, state: FSMContext):
    await state.finish()
    await message.reply("Welcome! Use /create to start a new project or /settings to configure your settings.")

@dp.message_handler(commands=['cancel', 'exit'], state='*')
async def cancel_command(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.finish()
    await message.reply('Процесс был успешно прерван.')

@dp.message_handler(commands=['create'])
async def create_project(message: types.Message):
    await Form.name.set()
    await message.reply("Enter the name of the project:")

@dp.message_handler(state=Form.name)
async def process_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await Form.next()
    await message.reply("Enter option1 for the project:")

@dp.message_handler(state=Form.option1)
async def process_option1(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['option1'] = message.text
    await Form.next()
    await message.reply("Send the JSON key as a file or text:")

@dp.message_handler(content_types=['document', 'text'], state=Form.jsonKey)
async def process_jsonKey(message: types.Message, state: FSMContext):
    json_key = ''
    if message.document:
        if message.document.mime_type == 'application/json' or message.document.file_name.endswith('.json') or message.document.file_name.endswith('.txt'):
            file = await bot.get_file(message.document.file_id)
            file_path = file.file_path
            contents = await bot.download_file(file_path)
            json_key = contents.decode('utf-8')
        else:
            await message.reply("Please send a valid JSON file.")
            return
    else:
        json_key = message.text

    if validate_json(json_key):
        async with state.proxy() as data:
            data['jsonKey'] = json_key
            conn = sqlite3.connect('bot.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO projects (user_id, name, option1, jsonKey) VALUES (?, ?, ?, ?)', (message.from_user.id, data['name'], data['option1'], data['jsonKey']))
            conn.commit()
            conn.close()
            await message.reply("Project created successfully!")
    else:
        await message.reply("Invalid JSON. Please try again.")
        return

    await state.finish()

@dp.message_handler(commands=['settings'])
async def settings(message: types.Message):
    await SettingsForm.param1.set()
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("True", callback_data="true"), types.InlineKeyboardButton("False", callback_data="false"))
    await message.reply("Choose settings-param1:", reply_markup=markup)

@dp.callback_query_handler(state=SettingsForm.param1)
async def process_param1(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['param1'] = callback_query.data
    await bot.answer_callback_query(callback_query.id)
    await SettingsForm.next()
    await bot.send_message(callback_query.from_user.id, "Enter settings-param2:")

@dp.message_handler(state=SettingsForm.param2)
async def process_param2(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['param2'] = message.text
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO settings (user_id, param1, param2) VALUES (?, ?, ?)', (message.from_user.id, data['param1'], data['param2']))
        conn.commit()
        conn.close()
        await message.reply("Settings updated!")
    await state.finish()

@dp.message_handler(commands=['mysettings'])
async def mysettings(message: types.Message):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT param1, param2 FROM settings WHERE user_id = ?', (message.from_user.id,))
    row = cursor.fetchone()
    if row:
        await message.reply(f"Your settings:\nparam1: {row[0]}\nparam2: {row[1]}")
    else:
        await message.reply("You don't have any settings saved.")
    conn.close()

@dp.message_handler(commands=['projects'])
async def list_projects(message: types.Message):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM projects WHERE user_id = ?', (message.from_user.id,))
    projects = cursor.fetchall()
    markup = types.InlineKeyboardMarkup()
    for project in projects:
        markup.add(types.InlineKeyboardButton(project[0], callback_data=f"project_{project[0]}"))
    await message.reply("Your projects:", reply_markup=markup)
    conn.close()

@dp.callback_query_handler(lambda c: c.data.startswith('project_'))
async def process_project_selection(callback_query: types.CallbackQuery):
    project_name = callback_query.data.replace('project_', '')
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, option1, jsonKey FROM projects WHERE user_id = ? AND name = ?', (callback_query.from_user.id, project_name))
    project = cursor.fetchone()
    if project:
        await bot.send_message(callback_query.from_user.id, f"Project: {project[0]}\nOption1: {project[1]}\nJSON Key: {project[2]}")
    else:
        await bot.send_message(callback_query.from_user.id, "Project not found.")
    conn.close()

@dp.message_handler()
async def get_project_info(message: types.Message):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, option1, jsonKey FROM projects WHERE user_id = ? AND name = ?', (message.from_user.id, message.text))
    project = cursor.fetchone()
    if project:
        await message.reply(f"Project: {project[0]}\nOption1: {project[1]}\nJSON Key: {project[2]}")
    else:
        await message.reply("Project not found.")
    conn.close()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)