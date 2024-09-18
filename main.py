import logging
from dotenv import main
import asyncio
import os
import time
import sqlite3
import json
import re
from aiogram import F, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from donkey.check_valid_url import check_valid_url
from donkey.validate_json import validate_json
from google.publish import google_publish
from yandex.recrawl import yandex_recrawl
from indexnow.publish_single import indexnow_publish

# TODO: Настроить запись логов в файл
logging.basicConfig(level=logging.INFO, format='%(asctime)s / %(levelname)s / %(message)s', datefmt='%d.%m.%y %H:%M:%S') # Запись логов в файл
__version__ = "0.0.3"
main.load_dotenv()
storage = MemoryStorage()
router = Router()
bot = Bot(token=os.getenv("API_TOKEN"))
dp = Dispatcher(storage=storage)
DB = os.getenv("DB")
admin_id = os.getenv("ADMIN_ID")

class CreateProject(StatesGroup):
    url = State()
    indexnow = State()
    indexnow_key = State()
    indexnow_key_path = State()
    indexnow_service = State()
    indexing_api = State()
    indexing_api_key = State()
    webmaster = State()
    yandex_user_token = State()
    add_to_db = State()

class SettingsForm(StatesGroup):
    main = State()
    set_default_yandex_user_token = State()

class AdminState(StatesGroup):
    broadcast = State()

def init_db():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        url TEXT,
        indexnow BOOLEAN,
        indexnow_key TEXT,
        indexnow_key_path TEXT,
        indexnow_service INT,
        indexing_api BOOLEAN,
        indexing_api_key TEXT,
        webmaster BOOLEAN,
        yandex_user_token TEXT
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        user_id INTEGER PRIMARY KEY,
        default_yandex_user_token TEXT
    )
    ''')
    conn.commit()
    conn.close()

# TODO: Реализовать работу бота на одном сообщении
# TODO: Добавить команду /report
# Хэндлер на команду /start
@dp.message(Command("start"))
async def cmd_start(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.username: # Определяем логин пользователя (Для логгирования)
        username = "@" + callback_query.from_user.username + " (" + str(callback_query.from_user.id) + ")"
    else:
        username = callback_query.from_user.id

    try: await callback_query.message.edit_reply_markup(reply_markup=None) # Попытка скрытия клавиатуры
    except: pass

    logging.info(f"{username} / Введена команда start")
    await state.clear()

    logging.info(f"{username} / Команда start / Соединение с базой данных для определения наличия добавленных проектов")
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute('SELECT id, url FROM projects WHERE user_id = ?', (callback_query.from_user.id,))
    projects = cursor.fetchall()
    logging.info(f"{username} / Команда start / Закрытие соединения с базой данных")
    conn.close()

    builder = InlineKeyboardBuilder()
    if projects:
        builder.row(types.InlineKeyboardButton(text="Список проектов", callback_data="show-projects"))
    else:
        builder.row(types.InlineKeyboardButton(text="➕ Добавить проект", callback_data="create-project"))
    builder.row(types.InlineKeyboardButton(text="Настройки", callback_data="settings"))
    builder.row(types.InlineKeyboardButton(text="Помощь", url="https://imeyk.gitbook.io/recrawler-faq"))

    await bot.send_message(callback_query.from_user.id, f"👋 Привет {callback_query.from_user.first_name}, для просмотра списка проектов используйте команду /projects или /settings для конфигурации работы сценария бота", reply_markup=builder.as_markup())

# Реферальная система
@dp.message(CommandStart(
    deep_link=True,
    magic=F.args.regexp(re.compile(r'ref_(\d+)')) # /?start=ref_255
))
async def cmd_start_book(
        message: Message,
        command: CommandObject
):
    ref_code = command.args.split("_")[1]
    if ref_code:
        # TODO: Добавить запись реферального кода в базу данных
        logging.info(f"{'@' + message.from_user.username + ' (' + str(message.from_user.id) + ')' if message.from_user.username else message.from_user.id} / Приглашен по реферальному коду #{ref_code}")
        await message.answer(f"Вы приглашены по реферальному коду #{ref_code}") # Пока только оповещение

# Команда "Отмена"
@dp.message(StateFilter(None), Command("cancel"))
@dp.callback_query(F.data == "cancel")
@router.message(StateFilter(None), F.text.lower() == "отмена")
async def cmd_cancel_no_state(callback_query: types.CallbackQuery, state: FSMContext):
    try: await callback_query.message.edit_reply_markup(reply_markup=None) # Попытка скрытия клавиатуры
    except: pass

    await state.set_data({}) # Стейт сбрасывать не нужно, удалим только данные
    await bot.send_message(callback_query.from_user.id, "Нечего отменять", reply_markup=None)

@dp.message(Command("cancel"))
@dp.callback_query(F.data == "cancel")
@router.message(F.text.lower() == "отмена")
async def cmd_cancel(callback_query: types.CallbackQuery, state: FSMContext):
    try: await callback_query.message.edit_reply_markup(reply_markup=None) # Попытка скрытия клавиатуры
    except: pass

    await state.clear()
    await bot.send_message(callback_query.from_user.id, "Действие отменено", reply_markup=None)

# Вывод списка проектов
@dp.message(Command("projects"))
@dp.callback_query(F.data == "show-projects")
async def handle_projects(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.username: # Определяем логин пользователя (Для логгирования)
        username = "@" + callback_query.from_user.username + " (" + str(callback_query.from_user.id) + ")"
    else:
        username = callback_query.from_user.id

    await state.set_state(SettingsForm.main) # Устанавливаем текущее состояние
    logging.info(f"{username} / Список проектов / Вызвов функции")

    logging.info(f"{username} / Список проектов / Соединение с базой данных") # Подключение к базе данных для получения списка проектов
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute('SELECT id, url FROM projects WHERE user_id = ?', (callback_query.from_user.id,))
    projects = cursor.fetchall()
    conn.close()
    logging.info(f"{username} / Список проектов / Закытие соединения с базой данных") # Закрытие соединения с базой данных

    builder = InlineKeyboardBuilder()
    if projects:
        logging.info(f"{username} / Список проектов / Вывод списка проектов пользователя")
        for project in projects:
            project_name = re.sub(r'^(https?://)?(www\.)?', '', project[1]).rstrip('/')
            builder.row(types.InlineKeyboardButton(text=project_name, callback_data=f"project_{project[0]}"))        
        builder.row(types.InlineKeyboardButton(text="➕ Добавить проект", callback_data="create-project"))

        await bot.send_message(callback_query.from_user.id, "Список сохраненных проектов", reply_markup=builder.as_markup())
    else:
        logging.info(f"{username} / Список проектов / Список проектов пуст")
        builder.add(types.InlineKeyboardButton(text="➕ Добавить проект", callback_data="create-project"))
        await bot.send_message(callback_query.from_user.id, "Отсутствуют сохраненные проекты", reply_markup=builder.as_markup())

# Вывод информации о проекте
@dp.callback_query(F.data.startswith('project_'))
async def process_project_selection(callback_query: types.CallbackQuery):
    logging.info(f"[{callback_query.from_user.id}] Получаем информацию о проекте")
    await callback_query.message.edit_reply_markup(reply_markup=None)
    project_id = callback_query.data.replace('project_', '')
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute('SELECT id, url, indexing_api, webmaster, indexnow FROM projects WHERE user_id = ? AND id = ?', (callback_query.from_user.id, project_id))
    project = cursor.fetchone()
    project_id = int(project[0])
    if project:
        logging.info(f"[{callback_query.from_user.id}] Вывод информации о проекте {project[1]}.")
        # TODO: Реализовать выбор параметра в проекте
        # TODO: Реализовать изменение проекта
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(text="Удалить", callback_data=f"delete_project_{project_id}"))
        
        message_text = (re.sub(r'^(https?://)?(www\.)?', '', project[1]).rstrip('/') +
            f"\nID: {project[0]}\n" +
            ("\nGoogle Indexing API: 🟢 Включен" if project[2] else '\nGoogle Indexing API: 🔴 Отключен') +
            ("\nYandex Webmaster: 🟢 Включен" if project[3] else '\nYandex Webmaster: 🔴 Отключен') +
            ("\nIndexNow: 🟢 Включен" if project[4] else '\nIndexNow: 🔴 Отключен')
        )
        await bot.send_message(callback_query.from_user.id, message_text, reply_markup=builder.as_markup(), disable_web_page_preview=True)
    conn.close()

# Подтверждение удаления проекта
@dp.callback_query(F.data.startswith('delete_project_'))
async def callback_delete_project_button(callback_query: types.CallbackQuery):
    await callback_query.message.edit_reply_markup(reply_markup=None)
    project_id = callback_query.data.split('_', 2)[-1]
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute('SELECT url FROM projects WHERE id = ? AND user_id = ?', (project_id, callback_query.from_user.id))
    project = cursor.fetchone()
    conn.close()
    logging.info(f"[{callback_query.from_user.id}] Иницирование удаления проекта {project[0]}.")
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Да", callback_data=f"process_delete_project_{project_id}"))
    builder.add(types.InlineKeyboardButton(text="Нет", callback_data=f"cancel"))
    await bot.send_message(callback_query.from_user.id, f"Вы действительно хотите удалить проект {project[0]}?", reply_markup=builder.as_markup(), disable_web_page_preview=True)

# Процесс удаления проекта
@dp.callback_query(F.data.startswith('process_delete_project_'))
async def process_callback_delete_project_button(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_reply_markup(reply_markup=None)
    project_id = callback_query.data.split('_', 3)[-1]
    logging.info(f"[{callback_query.from_user.id}] Удаление проекта – ID: {project_id}.")
    print(project_id)
    print(type(project_id))
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM projects WHERE id = ? AND user_id = ?", (project_id, callback_query.from_user.id))
    conn.commit()
    try:
        logging.info(f"[{callback_query.from_user.id}] Сообщение успешно обновлено")
        await bot.edit_message_text(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id, text=f"Проект ID: {project_id} – Успешно удален")
    except Exception as e:
        logging.error(f"[{callback_query.from_user.id}] Произошла ошибка при редактировании сообщения: {e})")
        await bot.send_message(callback_query.from_user.id, f"Проект ID: {project_id} – Успешно удален")
    # TODO: Добавить возврат в список проектов
    conn.close()
    await state.clear()

# Создание проекта
# TODO: Проработать и добавить необходимые для работы скрипта переменные
@dp.callback_query(F.data == "create-project")
async def process_callback_create_project_button(message: types.Message, state: FSMContext):
    logging.info(f"[{message.from_user.id}] Ввод URL проекта")
    await bot.send_message(message.from_user.id, "Введите URL проекта", reply_markup=None)
    await state.set_state(CreateProject.url) # Устанавливаем состояние ожидания

@dp.message(CreateProject.url)
async def process_project_name(message: types.Message, state: FSMContext):
    cleaned_url = check_valid_url(message.from_user.id, message.text, check_domain=True)
    logging.info(f"[{message.from_user.id}] Проверка валидности URL {cleaned_url}")
    
    if not cleaned_url:
        logging.error(f"[{message.from_user.id}] Введенный домен недоступен или несуществует")
        await message.reply("Введенный домен недоступен или не существует. Пожалуйста, введите корректный URL.")
        return
    else:
        logging.info(f"[{message.from_user.id}] Проверка наличия введенного домена БД")
        conn = sqlite3.connect(DB)
        cursor = conn.cursor()
        cursor.execute('SELECT id, url FROM projects WHERE user_id = ? AND url = ?', (message.from_user.id, cleaned_url))
        project = cursor.fetchone()
        # logging.error(f"[{message.from_user.id}] {project}")
        conn.close()

        if project is None:
            # Если проект не был ранее добавлен в базу данных
            logging.info(f"[{message.from_user.id}] Проект {cleaned_url} ранее не был добавлен в БД. Инициализируем добавление")
            message_text = ('Добавляем проект – ' + re.sub(r'^(https?://)?(www\.)?', '', cleaned_url).rstrip('/'))
            await bot.send_message(message.from_user.id, message_text, disable_web_page_preview=True)
            # await message.answer(message, disable_web_page_preview=True)

            logging.info(f"[{message.from_user.id}] Добавляем проект – {cleaned_url}.")
            await state.update_data(url=cleaned_url) # data = await state.get_data()

            await state.set_state(CreateProject.indexing_api) # Устанавливаем состояние ожидания
            builder = InlineKeyboardBuilder()
            builder.add(types.InlineKeyboardButton(text="Да", callback_data="useIndexingAPI"))
            builder.add(types.InlineKeyboardButton(text="Нет", callback_data="notUseIndexingAPI"))
            await message.answer(
                "Использовать сервис Google Indexing API для переобхода?",
                reply_markup=builder.as_markup()
            )
        else:
            # Если проект ранее был добавлен в базу данных
            # TODO: Настроить вывод информации о проекте
            await message.reply(f"Проект {cleaned_url} - уже существует", disable_web_page_preview=True)
            await state.clear()


# Google Indexing API Обработчик для кнопки "Да"
@dp.callback_query(F.data == "useIndexingAPI")
async def process_use_googleindexing_api(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_reply_markup(reply_markup=None)
    logging.info(f"[{callback_query.from_user.id}] На проекте будет использоваться Google Indexing API")
    await state.update_data(indexing_api=True)
    await bot.answer_callback_query(callback_query.id)
    logging.info(f"[{callback_query.from_user.id}] Добавление json ключа для проекта")
    await bot.send_message(callback_query.from_user.id, "Отправьте JSON ключ")
    await state.set_state(CreateProject.indexing_api_key) # Устанавливаем состояние ожидания

# Обработка JSON ключа для Google Indexing API
# TODO: Добавить проверку на валидность JSON ключа по содержанию строк
@dp.message(CreateProject.indexing_api_key)
async def process_add_google_indexing_api_key(message: types.Message, state: FSMContext):
    json_key = ''

    if message.content_type == 'document':
        if message.document.mime_type == 'application/json' or message.document.file_name.endswith('.json') or message.document.file_name.endswith('.txt'):
            file = await bot.get_file(message.document.file_id)
            file_path = file.file_path
            contents = await bot.download_file(file_path)
            json_key = contents.decode('utf-8')
        else:
            logging.error(f"[{message.from_user.id}] Отправлен неверный JSON ключ.")
            builder = InlineKeyboardBuilder()
            builder.add(types.InlineKeyboardButton(text="Пропустить", callback_data="skipUseIndexingAPI"))
            await message.answer("Неверный формат JSON ключа. Пожалуйста попробуйте снова", reply_markup=builder.as_markup())
            # TODO: Добавить пропуск шага
            return
    elif message.content_type == 'text':
        json_key = message.text
    else:
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(text="Пропустить", callback_data="skipUseIndexingAPI"))
        await message.answer("Неверный формат JSON ключа. Пожалуйста попробуйте снова", reply_markup=builder.as_markup())
        return

    # TODO: Добавить проверку валидности JSON ключа (validate_json.py)
    if validate_json(json_key):
        await state.update_data(indexing_api_key=json_key)
        logging.info(f"[{message.from_user.id}] Введен JSON ключ: {json_key}")
        await message.answer("JSON ключ для Google Indexing API принят.")

        await state.set_state(CreateProject.webmaster)
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(text="Да", callback_data="useWebmaster"))
        builder.add(types.InlineKeyboardButton(text="Нет", callback_data="notUseWebmaster"))
        await bot.send_message(message.from_user.id, "Использовать сервис Яндекс Вебмастер для переобхода?", reply_markup=builder.as_markup())
        #??? await process_use_webmaster()
        # await commit_to_db(message.from_user.id, data)
    else:
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(text="Пропустить", callback_data="skipUseIndexingAPI"))
        await message.answer("Неверный формат JSON ключа. Пожалуйста попробуйте снова", reply_markup=builder.as_markup())
        # TODO: Добавить пропуск шага
        return

    await state.set_state(CreateProject.webmaster)

# Пропуск ввода JSON ключа для Google Indexing API
@dp.callback_query(F.data == "skipUseIndexingAPI")
async def process_not_skip_googleindexing_api_key(callback_query: types.CallbackQuery, state: FSMContext):
    logging.info(f"[{callback_query.from_user.id}] Пропуск ввода ключа Google Indexing API")
    # await callback_query.message.edit_reply_markup(reply_markup=None)
    await state.update_data(indexing_api=False) # await state.get_data()
    
    await state.set_state(CreateProject.webmaster)
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Да", callback_data="useWebmaster"))
    builder.add(types.InlineKeyboardButton(text="Нет", callback_data="notUseWebmaster"))
    await bot.send_message(callback_query.from_user.id, "Использовать сервис Яндекс Вебмастер для переобхода?", reply_markup=builder.as_markup())

# Google Indexing API Обработчик для кнопки "Нет"
@dp.callback_query(F.data == "notUseIndexingAPI")
async def process_not_use_googleindexing_api(callback_query: types.CallbackQuery, state: FSMContext):
    logging.info(f"[{callback_query.from_user.id}] Отказ от использования Google Indexing API")
    await callback_query.message.edit_reply_markup(reply_markup=None)
    await state.update_data(indexing_api=False) # await state.get_data()
    
    await state.set_state(CreateProject.webmaster)
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Да", callback_data="useWebmaster"))
    builder.add(types.InlineKeyboardButton(text="Нет", callback_data="notUseWebmaster"))
    await bot.send_message(callback_query.from_user.id, "Использовать сервис Яндекс Вебмастер для переобхода?", reply_markup=builder.as_markup())


# TODO: Добавить работу с сервисом Яндекс.Вебмастер
@dp.message(CreateProject.webmaster)
async def process_use_webmaster(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_reply_markup(reply_markup=None)
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Да", callback_data="useWebmaster"))
    builder.add(types.InlineKeyboardButton(text="Нет", callback_data="notUseWebmaster"))
    await bot.send_message(callback_query.from_user.id, "Использовать сервис Яндекс Вебмастер для переобхода?", reply_markup=builder.as_markup())

# Яндекс.Вебмастер Обработчик для кнопки "Да"
# TODO: Добавить проверку валидности токена при добавлении
@dp.callback_query(F.data == "useWebmaster")
async def process_use_webmaster(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.username: # Определяем логин пользователя (Для логгирования)
        username = "@" + callback_query.from_user.username + " (" + str(callback_query.from_user.id) + ")"
    else:
        username = callback_query.from_user.id
    
    logging.info(f"{username} / Добавление проекта / Yandex Webmaster / Иницилизация обработчика кнопки 'Да'")
    await callback_query.message.edit_reply_markup(reply_markup=None) # Скрытие inline клавиатуры
    await state.set_state(CreateProject.yandex_user_token) # Установка состояния
    await state.update_data(webmaster=True) # await state.get_data()
    await bot.answer_callback_query(callback_query.id) # ???
    logging.info(f"{username} / Добавление проекта / Yandex Webmaster / Ождиание токена от пользователя")
    
    # TODO: Добавить проверку токена пользователя Яндекс Вебмастер
    logging.info(f"{username} / Добавление проекта / Yandex Webmaster /Соединение с базой данных") # Запрос к базе данных
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    logging.info(f"{username} / Добавление проекта / Yandex Webmaster / Получение настроек пользователя")
    cursor.execute('SELECT default_yandex_user_token FROM settings WHERE user_id = ?', (callback_query.from_user.id,))
    default_user_token = cursor.fetchall()
    logging.info(f"{username} / Добавление проекта / Yandex Webmaster / Закрыто соединение с базой данных")
    conn.close() # Закрытие соединения с базой данных

    if default_user_token:
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(text="Использовать токен по умолчанию", callback_data="useWebmasterWithDefaultToken"))
        await bot.send_message(callback_query.from_user.id, "Отправьте Yandex user token ключ", reply_markup=builder.as_markup())
    else:
        await bot.send_message(callback_query.from_user.id, "Отправьте Yandex user token ключ")

# TODO: Добавить работу с сервисом Яндекс.Вебмастер
@dp.message(CreateProject.yandex_user_token)
async def process_use_webmaster(message: types.Message, state: FSMContext):
    logging.info(f"[{message.from_user.id}] Yandex user token получен - обработка")
    await state.update_data(yandex_user_token = message.text) # await state.get_data()
    
    await state.set_state(CreateProject.indexnow)
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Да", callback_data="useIndexNow"))
    # TODO: Если до этого Яндекс Вебмастер и Google Indexing API = False, то заменяем кнопку нет
    builder.add(types.InlineKeyboardButton(text="Нет", callback_data="notUseIndexNow"))
    await message.answer(
        "Использовать для переобхода технологию IndexNow (Yandex, Bing)?",
        reply_markup=builder.as_markup()
    )

# Яндекс.Вебмастер Обработчик для кнопки "Использовать токен по умолчанию"
@dp.callback_query(F.data == "useWebmasterWithDefaultToken")
async def process_not_use_webmaster(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_reply_markup(reply_markup=None)
    await bot.answer_callback_query(callback_query.id)
    await state.update_data(webmaster=True, yandex_user_token="default") # await state.get_data()
    
    await state.set_state(CreateProject.indexnow_key)
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Да", callback_data="useIndexNow"))
    builder.add(types.InlineKeyboardButton(text="Нет", callback_data="notUseIndexNow"))
    await bot.send_message(callback_query.from_user.id, "Использовать для переобхода технологию IndexNow (Yandex, Bing)?", reply_markup=builder.as_markup())

# Яндекс.Вебмастер Обработчик для кнопки "Нет"
@dp.callback_query(F.data == "notUseWebmaster")
async def process_not_use_webmaster(callback_query: types.CallbackQuery, state: FSMContext):
    logging.info(f"[{callback_query.from_user.id}] Отказ от использования сервиса Яндекс Вебмастер")
    await callback_query.message.edit_reply_markup(reply_markup=None)
    await bot.answer_callback_query(callback_query.id)
    await state.update_data(webmaster=False) # await state.get_data()
    
    await state.set_state(CreateProject.indexnow_key)
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Да", callback_data="useIndexNow"))
    builder.add(types.InlineKeyboardButton(text="Нет", callback_data="notUseIndexNow"))
    await bot.send_message(callback_query.from_user.id, "Использовать для переобхода технологию IndexNow (Yandex, Bing)?", reply_markup=builder.as_markup())

# Добавление проекта - IndexNow
# TODO: Добавить работу с сервисом IndexNow
@dp.message(CreateProject.indexnow)
async def process_use_webmaster(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_reply_markup(reply_markup=None)

    await state.set_state(CreateProject.indexnow_key)
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Да", callback_data="useIndexNow"))
    builder.add(types.InlineKeyboardButton(text="Нет", callback_data="notUseIndexNow"))
    await bot.send_message(callback_query.from_user.id, "Использовать для переобхода технологию IndexNow (Yandex, Bing)", reply_markup=builder.as_markup())

# Добавление проекта - IndexNow - Обработчик для кнопки "Да"
# TODO: Добавить проверку ключа IndexNow
# TODO: Добавить возможность указания пользовательского пути к файлу ключа IndexNow (Столбец в БД: indexnow_key_path)
# TODO: Добавить уточнение у пользователя в какие поисковые системы будем отправлять запрос Yandex, Bing по отдельности или вместе (Столбец в БД: indexnow_service)
@dp.callback_query(F.data == "useIndexNow")
async def process_use_indexnow(callback_query: types.CallbackQuery, state: FSMContext):
    logging.info(f"[{callback_query.from_user.id}] На проекте будет использоваться переобход при помощи технологии IndexNow")
    await callback_query.message.edit_reply_markup(reply_markup=None)
    await state.update_data(indexnow = True) # await state.get_data()

    await state.set_state(CreateProject.indexnow_key)
    await bot.answer_callback_query(callback_query.id)
    logging.info(f"[{callback_query.from_user.id}] Ожидание от пользователя IndexNow ключа")
    await bot.send_message(callback_query.from_user.id, "Отправьте IndexNow ключ")

# Добавление проекта - IndexNow - Добавление значения переменной indexnow_key
@dp.message(CreateProject.indexnow_key)
async def process_use_indexnow(message: types.Message, state: FSMContext):
    logging.info(f"[{message.from_user.id}] Ключ IndexNow получен - обработка")
    await state.update_data(indexnow_key = message.text) # await state.get_data()

    await state.set_state(CreateProject.indexnow_key_path) # Установка состояния
    builder = InlineKeyboardBuilder()
    # builder.add(types.InlineKeyboardButton(text="В корне сайта", callback_data="*"))
    builder.add(types.InlineKeyboardButton(text="Пропустить", callback_data="skipSetIndexNowKeyPatch"))
    await bot.send_message(message.from_user.id, "Ключ IndexNow получен, укажите URL его расположения", reply_markup=builder.as_markup())
    
# Добавление проекта - IndexNow - Обработчик для кнопки "Нет"
@dp.callback_query(F.data == "notUseIndexNow")
async def process_not_use_indexnow(callback_query: types.CallbackQuery, state: FSMContext):
    try: await callback_query.message.edit_reply_markup(reply_markup=None) # Попытка скрытия клавиатуры
    except: pass

    logging.info(f"[{callback_query.from_user.id}] Отказ от использования IndexNow")
    await bot.answer_callback_query(callback_query.id)

    await state.set_state(CreateProject.add_to_db)
    await state.update_data(indexnow = False) # await state.get_data()
    logging.info(f"[{callback_query.from_user.id}] Проект создан.")
    # await bot.send_message(callback_query.from_user.id, f"Проект {url} успешно обработан.\n\n{data}")
    # await asyncio.sleep(2)
    data = await state.get_data()
    await commit_to_db(callback_query.from_user.id, data)
    await state.clear()
    # await bot.edit_message_text(text="Проект сохранен", chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)

# Пропуск указания пути IndexNow key patch
@dp.callback_query(F.data == "skipSetIndexNowKeyPatch")
async def process_not_use_indexnow(callback_query: types.CallbackQuery, state: FSMContext):
    try: await callback_query.message.edit_reply_markup(reply_markup=None) # Попытка скрытия клавиатуры
    except: pass

    logging.info(f"[{callback_query.from_user.id}] Пропуск указания пути к ключу IndexNow")
    # await state.update_data(indexnow_key_path = message.text) # await state.get_data()
    data = await state.get_data()

    await state.set_state(CreateProject.add_to_db)
    await commit_to_db(callback_query.from_user.id, data)
    await state.clear()

# Добавление проекта - IndexNow - Добавление значения переменной indexnow_key_path
# TODO: Можно оптимизировав указав только путь до файла и заполнять indexnow_key при помощи парсинга
@dp.message(CreateProject.indexnow_key_path)
async def set_indexnow_key_patch(message: types.Message, state: FSMContext):
    # try: await callback_query.message.edit_reply_markup(reply_markup=None) # Попытка скрытия клавиатуры
    # except: pass

    logging.info(f"[{message.from_user.id}] Ключ IndexNow получен - обработка")
    await state.update_data(indexnow_key_path = message.text) # await state.get_data()
    data = await state.get_data()

    await state.set_state(CreateProject.add_to_db)
    await commit_to_db(message.from_user.id, data)
    await state.clear()

# Отправка изменения в БД, сохранение проекта
async def commit_to_db(user_id, data):
    # TODO: Добавить обработку если ни добавлен для работы ни один из сервисов
    logging.info(f"[{user_id}] Попытка соединения и добавления параметров проекта в БД.\nData = {data}")

    if data['indexing_api'] or data['webmaster'] or data['indexnow']:
        conn = sqlite3.connect(DB)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO projects (user_id, url, indexing_api, indexing_api_key, webmaster, yandex_user_token, indexnow, indexnow_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (user_id, data['url'], data['indexing_api'], data.get('indexing_api_key', None), data['webmaster'], data.get('yandex_user_token', None), data['indexnow'], data.get('indexnow_key', None)))
        conn.commit()
        logging.info(f"[{user_id}] Параметры проекта успешно добавлены. Закрываем соединение с БД.")
        conn.close()

        # TODO: Добавить сообщение о подтверждении сохранении проекта?
        message_text = (
            "Проект " + re.sub(r'^(https?://)?(www\.)?', '', str(data['url'])).rstrip('/') + 
            " сохранен\n" +
            ('\nGoogle Indexing API: Включен' if data['indexing_api'] else '') +
            ('\nYandex.Webmaster: Включен' if data['webmaster'] else '') +
            ('\nIndexNow: Включен' if data['indexnow'] else '')
        )
        await bot.send_message(user_id, message_text, disable_web_page_preview=True)

        logging.info(f"[{user_id}] Обработка проекта завершена\n\n{data}")
    else:
        await bot.send_message(user_id, "Для добавления проекта необходимо настроить минимум один сервис для работы (Google Indexing API, Yandex.Webmaster, IndexNow)", disable_web_page_preview=True)
        return
    
# Настройки аккаунта
# TODO: Доработка настроек аккаунта
# TODO: Проработать и добавить необходимые для работы скрипта переменные
@dp.message(Command("settings"))
@dp.callback_query(F.data == "settings")
async def settings(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.username: # Определяем логин пользователя (Для логгирования)
        username = "@" + callback_query.from_user.username + " (" + str(callback_query.from_user.id) + ")"
    else:
        username = callback_query.from_user.id
    logging.info(f"{username} / Введена команда settings")
    await state.set_state(SettingsForm.main) # Устанавливаем текущее состояние

    try: await callback_query.message.edit_reply_markup(reply_markup=None) # Попытка скрытия клавиатуры
    except: pass

    logging.info(f"{username} / Команда settings / Соединение с базой данных") # Запрос к базе данных
    await callback_query.answer("Получение переменных настроек аккаунта")
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    logging.info(f"{username} / Команда settings / Получение настроек пользователя")
    cursor.execute('SELECT default_yandex_user_token FROM settings WHERE user_id = ?', (callback_query.from_user.id,))
    settings = cursor.fetchall()
    logging.info(f"{username} / Команда settings / Закрыто соединение с базой данных")
    conn.close() # Закрытие соединения с базой данных

    builder = InlineKeyboardBuilder()
    if settings:
        builder.row(types.InlineKeyboardButton(text=f"Изменить Yandex User token", callback_data="set_default_yandex_user_token"))
    else:
        builder.row(types.InlineKeyboardButton(text=f"Yandex User token: Не задан", callback_data="set_default_yandex_user_token"))

    await bot.send_message(callback_query.from_user.id, "Настройки аккаунта", reply_markup=builder.as_markup())

# Обработчик callback-запроса для установки токена по умолчанию для сервиса Яндекс Вебмастер 
@dp.callback_query(F.data == "set_default_yandex_user_token")
async def handle_button1(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(SettingsForm.set_default_yandex_user_token) # Устанавливаем текущее состояние
    await callback_query.message.edit_reply_markup(reply_markup=None) # Скрываем inline клавиатуру
    # await callback_query.answer("Вы нажали кнопку 1!")
    # TODO: Добавить диалог подтверждения замены токена
    await callback_query.message.answer("Отправьте Yandex User token для использования по умолчанию")

@dp.message(SettingsForm.set_default_yandex_user_token)
async def process_use_webmaster(message: Message, state: FSMContext):
    # await callback_query.message.edit_reply_markup(reply_markup=None) # Скрываем inline клавиатуру
    if message.text == "default":
        await message.answer("Введено неверное значение токена. Пожалуйста, попробуйте снова")
        return
    else:
        await state.update_data(default_yandex_user_token = message.text) # await state.get_data()
        data = await state.get_data()
        logging.info(f"DATA == {data}")

        conn = sqlite3.connect(DB) # Соединение с базой данных
        cursor = conn.cursor()
        attempts = 0
        max_attempts = 5
        while attempts < max_attempts:
            try:
                cursor.execute('INSERT INTO settings (user_id, default_yandex_user_token) VALUES (?, ?)', (message.from_user.id, data['default_yandex_user_token']))
                break
            except sqlite3.OperationalError:
                attempts += 1
                logging.warning(f"Обновление токена по умолчанию для Яндекс Вебмастер / OperationalError: Ошибка добавления записи в базу данных. Попытка {attempts} из {max_attempts}")
                if attempts == max_attempts:
                    logging.warning(f"Обновление токена по умолчанию для Яндекс Вебмастер / Ошибка добавления записи в базу данных. Достигнуто максимально возможное количество попыток")
            except sqlite3.IntegrityError:
                try:
                    cursor.execute('UPDATE settings SET default_yandex_user_token = ? WHERE user_id = ?', (data['default_yandex_user_token'], message.from_user.id))
                    break
                except sqlite3.OperationalError:
                    attempts += 1
                    logging.warning(f"Обновление токена по умолчанию для Яндекс Вебмастер / IntegrityError: Ошибка добавления записи в базу данных. Попытка {attempts} из {max_attempts}")
                    if attempts == max_attempts:
                        logging.warning(f"Обновление токена по умолчанию для Яндекс Вебмастер / Ошибка добавления записи в базу данных. Достигнуто максимально возможное количество попыток")
        conn.commit()
        conn.close() # Закрытие соединения с базой данных
        
        await message.answer(f"Переменная Yandex User token (По умолчанию) = {data['default_yandex_user_token']}")

'''
# Настройка аккаунта param1
@dp.callback_query(F.data == "param1")
async def process_param1(callback_query: types.CallbackQuery, message: types.Message, state: FSMContext):
    logging.info(f"[{message.from_user.id}] Ввод параметра settings-param2")
    async with state.proxy() as data:
        data['param1'] = callback_query.data
    await bot.answer_callback_query(callback_query.id)
    await SettingsForm.next()
    await bot.send_message(callback_query.from_user.id, "Введите значение для параметра 'settings-param2''")

@dp.callback_query(F.data == "param2")
async def process_param2(message: types.Message, state: FSMContext):
    logging.info(f"[{message.from_user.id}] Изменены настройки")
    async with state.proxy() as data:
        data['param2'] = message.text
        logging.info(f"[{message.from_user.id}] Попытка соединения и обновления настроек сценария работы.")
        conn = sqlite3.connect(DB)
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO settings (user_id, param1, param2) VALUES (?, ?, ?)', (message.from_user.id, data['param1'], data['param2']))
        conn.commit()
        logging.info(f"[{message.from_user.id}] Настройки сценария работы успешно обновлены. Закрываем соединение с БД.")
        conn.close()
        await message.answer("Настройки обновлены.")
    await state.finish()

@dp.message_handler(commands=['mysettings'])
async def mysettings(message: types.Message):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute('SELECT param1, param2 FROM settings WHERE user_id = ?', (message.from_user.id,))
    row = cursor.fetchone()
    if row:
        logging.info(f"[{message.from_user.id}] Показаны параметры работы сценария.")
        await message.answer(f"param1: {row[0]}\nparam2: {row[1]}")
    else:
        logging.error(f"[{message.from_user.id}] Отсутствуют сохраненные настройки.")
        await message.answer("У вас нет сохраненных настроек.")
    conn.close()
'''

# Функции администрирования
## Принудительная остановка бота, командой /stop
@dp.message(StateFilter(None), Command("stop"))
async def broadcast_command(message: types.Message, state: FSMContext):
    if message.from_user.id == admin_id:
        await message.answer(text=f"У вас нет прав для использования этой команды")
        return

    logging.critical("Запущена принудительная остановка бота администратором")
    await message.answer(text="🤖 Принудительная остановка бота")
    await bot.delete_webhook(drop_pending_updates=True) # Удаляем вебхук и, при необходимости, очищаем ожидающие обновления
    await bot.session.close() # Закрываем сессию бота, освобождая ресурсы
    os._exit(1)

## Массовая рассылка пользователям 
# TODO: Доработать функцию рассылки для пользователей (На данный момент не работает отправка пользователям)
@dp.message(StateFilter(None), Command("broadcast"))
async def broadcast_command(message: types.Message, state: FSMContext):
    if message.from_user.id == admin_id:
        await message.answer(text=f"У вас нет прав для использования этой команды")
        return

    await message.answer(text="Введите сообщение для рассылки")
    await state.set_state(AdminState.broadcast) # Переходим в состояние ожидания сообщения для рассылки

### Обработчик сообщения для рассылки
@router.message(StateFilter("AdminState:broadcast"))
async def handle_broadcast_message(message: types.Message, state: FSMContext):
    text = message.text # Получаем текст сообщения
    try:
        await bot.send_message(admin_id, text)
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения пользователю {admin_id}: {e}")

    await message.answer("Рассылка завершена.")
    await state.finish() # Сбрасываем состояние

# TODO: Основной обработчик
# TODO: Добавить проверку уже существующего проекта
# TODO: Добавить отправку файлом TXT, CSV
# TODO: Добавить вывод о выполненной задаче в конце выполнения функции
@dp.message(F.text)
async def get_project_info(message: Message):
    logging.info(f"[{message.from_user.id}] Проверка валидности отправленного списка URL")
    # await hide_markup(message.bot, message.chat.id, message.message_id)

    # Выполняем очистку дублей строк и пропускаем пустые
    urls = []
    seen = set()

    for url in message.text.split('\n'):
        if url not in seen:
            if url:
                urls.append(url)
                seen.add(url)

    for line in urls[:]:
        project_url = check_valid_url(message.from_user.id, line, True)
        # TODO: Если проект не добавлен у пользователя, выдаем ошибку
        if not project_url:
            logging.error(f"[{message.from_user.id}] Введенный домен {project_url} недоступен или несуществует. Удаляем строку {line} из списка URL")
            # await message.reply(f"Введенный домен {project_url} недоступен или не существует. Пожалуйста, введите корректный URL.")
            try:
                urls.remove(line)
            except ValueError:
                logging.error(f"[{message.from_user.id}] Невозможно удалить элемент {line}, так как он не найден в списке")
        else:
            logging.info(f"[{message.from_user.id}] Обработка line = {line}")
            conn = sqlite3.connect(DB)
            cursor = conn.cursor()
            cursor.execute('SELECT id, url, indexing_api, indexing_api_key, webmaster, yandex_user_token, indexnow, indexnow_key, indexnow_key_path, indexnow_service FROM projects WHERE user_id = ? AND url = ?', (message.from_user.id, project_url))
            project = cursor.fetchone()
            project_id, project_url, indexing_api, indexing_api_key, webmaster, yandex_user_token, indexnow, indexnow_key, indexnow_key_path, indexnow_service = project

            if project:
                indexing_api_result = None
                webmaster_result = None
                indexnow_result = None

                # Переобход страниц сайта при помощи сервиса Google Indexing API
                # TODO: Вывести работу каждого из сервисов отдельным циклом for ???
                if indexing_api:
                    indexing_api_result = google_publish(message.from_user.id, indexing_api_key, line)

                # Переобход страниц сайта при помощи сервиса Яндекс Вебмастер
                if webmaster:
                    if yandex_user_token == "default":
                        cursor.execute('SELECT default_yandex_user_token FROM settings WHERE user_id = ?', (message.from_user.id,))
                        yandex_user_token = cursor.fetchone()
                        yandex_user_token = yandex_user_token[0]

                    webmaster_result = yandex_recrawl(message.from_user.id, yandex_user_token, line)

                    # TODO: Доделать дилоговое окно при возникновении ошибки при переобходе
                    if "🔴" in webmaster_result:
                        builder = InlineKeyboardBuilder()
                        builder.row(
                            types.InlineKeyboardButton(text="Да", callback_data="non-action"),
                            types.InlineKeyboardButton(text="Нет", callback_data="non-action")
                        )

                        await bot.send_message(message.from_user.id, text=f"{line}\n\n{webmaster_result}\n\nПродолжить отправку на переобход?", disable_web_page_preview=True, disable_notification=True, reply_markup=builder.as_markup())
                        break

                # Отправка на переобход при помощи технологии IndexNow
                if indexnow:
                    indexnow_service = ["yandex"] # TODO: Убрать после добавления возможности изменения переменной
                    # indexnow_service = ["yandex", "bing"] # TODO: Убрать после добавления возможности изменения переменной
                    indexnow_result = indexnow_publish(message.from_user.id, project_url, indexnow_key, indexnow_key_path, indexnow_service, line)
                
                await bot.send_message(message.from_user.id, text=f"{line}\n{indexing_api_result if indexing_api_result else ''}{webmaster_result if webmaster_result else ''}{indexnow_result if indexnow_result else ''}", disable_web_page_preview=True, disable_notification=True)
                # await message.answer(f"ID: {project[0]}\nURL: {project[1]}\nIndexing API: {project[2]}\nIndexing API JSON: {project[3]}\nYandex Webmaster: {project[4]}\nYandex user token: {project[5]}")
            else:
                # TODO: Если преокт не найден - выводим inline кнопки где спрашиваем пользователя о продолжении цикла, выходе или выходе из него (hard-mode: добавить проект)
                logging.error(f"[{message.from_user.id}] Проект {project_url} не найден в БД. Удаляем строку {line} из списка URL")
                try:
                    urls.remove(line)
                except ValueError:
                    logging.error(f"[{message.from_user.id}] Невозможно удалить элемент {line}, так как он не найден в списке")
                # logging.error(f"[{message.from_user.id}] Проект {project_url} не найден в БД")
                # markup = types.InlineKeyboardMarkup()
                # markup.add(types.InlineKeyboardButton("➕ Добавить проект", callback_data="create-project"))
                # await message.answer(f"Проект {project_url} не найден в базе данных", reply_markup=markup)
            conn.close()
    await bot.send_message(message.from_user.id, text="Задача завершена", disable_web_page_preview=True, disable_notification=True)
    # Можно также отправить пользователю подтверждение о добавлении всех строк

# TODO: Странно отрабатывает, возможно удалить
# Список быстрых команд
async def set_commands():
    ## Команды для пользователей
    user_commands = [
        BotCommand(command='start', description='Старт'),
        BotCommand(command='projects', description='Список проектов'),
        BotCommand(command='settings', description='Настройки')
    ]

    await bot.set_my_commands(user_commands, BotCommandScopeDefault()) # Устанавливаем команды для пользователей

# Функция выполняемая при запуске бота
async def on_startup():
    await set_commands() # Установка командного меню
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.send_message(admin_id, f"🤖 Бот запущен – {__version__}", disable_notification=True)

async def on_shutdown():
    await bot.send_message(admin_id, "🤖 Бот остановлен")
    await bot.delete_webhook(drop_pending_updates=True) # Удаляем вебхук и, при необходимости, очищаем ожидающие обновления
    await bot.session.close() # Закрываем сессию бота, освобождая ресурсы
    os._exit(1)

# Запуск процесса поллинга новых апдейтов
async def main():
    dp.startup.register(on_startup) # Выполняемая функция при запуске бота
    dp.shutdown.register(on_shutdown) # Выполняемая функция при остановке бота
    await bot.delete_webhook()
    await dp.start_polling(bot)

if __name__ == "__main__":
    i = 0
    loop = asyncio.get_event_loop() # Получаем текущий event loop
    
    while True:
        try:
            if os.getenv("API_TOKEN") is None:
                logging.critical("Не удалось загрузить переменную API_TOKEN для aiogram. Убедитесь, что он есть в файле .env")
            else:
                init_db()
                loop.run_until_complete(main())  # Запускаем main() в текущем event loop
        except Exception as e:
            i += 1
            logging.critical(f"Произошла критическая ошибка: {e}. Перезапуск бота. Попытка {i}")
            if i >= 5:
                logging.critical(f"Достигнуто максимальное количество ошибок - {i}. Завершение программы")
                os._exit(0)
            time.sleep(5)  # Задержка перед перезапуском