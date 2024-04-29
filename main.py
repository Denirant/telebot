import telebot
import traceback
import speech_recognition as sr
import subprocess
import os
import logging
from telebot import types
from pymongo import MongoClient
import requests
import g4f
from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch
import json
from datetime import datetime
import random




genres_array = [
    {"id": 1, "genre": "триллер"},
    {"id": 2, "genre": "драма"},
    {"id": 3, "genre": "криминал"},
    {"id": 4, "genre": "мелодрама"},
    {"id": 5, "genre": "детектив"},
    {"id": 6, "genre": "фантастика"},
    {"id": 7, "genre": "приключения"},
    {"id": 8, "genre": "биография"},
    {"id": 9, "genre": "фильм-нуар"},
    {"id": 10, "genre": "вестерн"},
    {"id": 11, "genre": "боевик"},
    {"id": 12, "genre": "фэнтези"},
    {"id": 13, "genre": "комедия"},
    {"id": 14, "genre": "военный"},
    {"id": 15, "genre": "история"},
    {"id": 16, "genre": "музыка"},
    {"id": 17, "genre": "ужасы"},
    {"id": 18, "genre": "мультфильм"},
    {"id": 19, "genre": "семейный"},
    {"id": 20, "genre": "мюзикл"},
    {"id": 21, "genre": "спорт"},
    {"id": 22, "genre": "документальный"},
    {"id": 23, "genre": "короткометражка"},
    {"id": 24, "genre": "аниме"},
    {"id": 26, "genre": "новости"},
    {"id": 27, "genre": "концерт"},
    {"id": 28, "genre": "для взрослых"},
    {"id": 29, "genre": "церемония"},
    {"id": 30, "genre": "реальное ТВ"},
    {"id": 31, "genre": "игра"},
    {"id": 32, "genre": "ток-шоу"},
    {"id": 33, "genre": "детский"},
]

def is_valid_json(my_json):
    try:
        json.loads(my_json)
        return True
    except ValueError:
        return False


FIND, ANSWER = range(2)


def format_duration(minutes):
    hours, remainder = divmod(minutes, 60)
    return f"{hours} часа {remainder} минуты"

BOT_TOKEN = None

def read_bot_token():
    try:
        from config import BOT_TOKEN
    except ImportError:
        pass

    if not BOT_TOKEN:
        BOT_TOKEN = os.environ.get('YOUR_BOT_TOKEN')

    if BOT_TOKEN is None:
        raise ValueError('Token for the bot must be provided (BOT_TOKEN variable)')
    return BOT_TOKEN

BOT_TOKEN = read_bot_token()

r = sr.Recognizer()
bot = telebot.TeleBot(BOT_TOKEN)

mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['telegramDB']
users_collection = db['users']

LOG_FOLDER = '.logs'
if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=f'{LOG_FOLDER}/app.log'
)

logger = logging.getLogger('telegram-bot')
logging.getLogger('urllib3.connectionpool').setLevel('INFO')

def find_conent(message):
    chat_id = message.chat.id
    content = message.text
    msg = None

    if(message.content_type == 'voice'):
        msg = bot.send_message(chat_id, '🔍Ой! Голосовой поиск может быть произведен только на главной странице.🤔')
        bot.register_next_step_handler(msg, find_conent)
        return

    if content.lower() != 'стоп' and content.lower() != 'stop' and content.lower() != '/stop':
        movies = search_movies(content)

        if len(movies) == 0:
            msg = bot.send_message(chat_id, '🔍Ой! Похоже, ничего не найдено по вашему запросу. Пожалуйста, проверьте правильность введенного названия фильма.🤔')
            bot.register_next_step_handler(msg, find_conent)
        else:
            send_movies_results(bot, chat_id, movies, 'найди', content, True)
    else:

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        row2_buttons = [types.KeyboardButton("🔍 Найти"), types.KeyboardButton("✔️ Просмотрено"), types.KeyboardButton("⏰ На потом")]
        markup.row(*row2_buttons)

        row3_buttons = [types.KeyboardButton("📰 Статистика"), types.KeyboardButton("🕰️ Отслеживать"), types.KeyboardButton("ℹ Помощь")]
        markup.row(*row3_buttons)

        row4_buttons = [types.KeyboardButton("🗳️ Подборки"), types.KeyboardButton("💥 Премьеры"), types.KeyboardButton("🥇 Топ 10")]
        markup.row(*row4_buttons)

        bot.send_message(chat_id, 'Вы вышли из режима поиска, теперь вам доступно меню управления ботом', reply_markup=markup)


def findingHandler(message):
    chat_id = message.chat.id
    content = message.text
    msg = None

    print('finding')

    if content == '🏠 Главная страница' or content == '/home':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        row2_buttons = [types.KeyboardButton("🔍 Найти"), types.KeyboardButton("✔️ Просмотрено"), types.KeyboardButton("⏰ На потом")]
        markup.row(*row2_buttons)

        row3_buttons = [types.KeyboardButton("📰 Статистика"), types.KeyboardButton("🕰️ Отслеживать"), types.KeyboardButton("ℹ Помощь")]
        markup.row(*row3_buttons)

        row4_buttons = [types.KeyboardButton("🗳️ Подборки"), types.KeyboardButton("💥 Премьеры"), types.KeyboardButton("🥇 Топ 10")]
        markup.row(*row4_buttons)

        bot.send_message(chat_id, '''
Привет! 🌟 Готов к кино приключениям? 🍿
Напиши мне, что хочешь посмотреть сегодня, и мы найдем для тебя идеальный вариант! 😊

Если хочешь найти фильм, используй команду <b>Найти</b> и вписывай названия. Писать можно сколько угодно, список постоянно будет обновляться. Если нашел, напиши стоп или stop, поиск закончится. Во время поиска, нижнее меню будет недоступно.
Так же можешь написать предложение, и наша нейросеть определит, что ты нужно сделать. Общаться с ней можно в свободной форме, как с человеком, но на всякий случай она будет уточнять результата обработки. Пример запроса:

<i>Например, <b>"Привет! Вчера друзья мне рассказали про классный фильм Шерлок Холм. Найдешь где его можно посмотреть?"</b></i>

Так же возможно у нее попросить что-либо отследить, в таком случае напиши «отследи» и название желаемого контента, в результате будут выведены все совпадения. А в дальнейшем бот будет присылать сообщения, если ему удалось что-либо обнаружить подходящее по названию.

Общайся с ней текстовыми сообщениями или голосовыми, она разберется и обязательно тебе поможет.

Остальное описание функциональности бота можно найти во вкладке <b>Помощь</b>. Счастливого просмотра! 🎬
''', reply_markup=markup, parse_mode='HTML')
    else:
        user_id = message.from_user.id
        user = users_collection.find_one({'user_id': user_id})

        # row3_buttons = [types.KeyboardButton("🔬 Добавить"), types.KeyboardButton("🗑️ Удалить"), types.KeyboardButton("🖌️ Изменить")]
        # markup.row(*row3_buttons)

        # row4_buttons = [types.KeyboardButton("📁 Посмотреть")]

        if(message.text == '📁 Посмотреть'):
            finding = user.get('finding', [])
            if len(finding) > 0:
                buttons = []
                for text in finding:
                    button_text = text
                    callback_data = f"find:{text}"
                    buttons.append([types.InlineKeyboardButton(button_text, callback_data=callback_data)])

                keyboard = types.InlineKeyboardMarkup(buttons)
                msg = bot.send_message(chat_id, 'Cписок отслеживаемых вами картин, выберите один из элементов, чтобы посмотреть все совпадения по запросу:', reply_markup=keyboard)
                bot.register_next_step_handler(msg, findingHandler)
            else:
                msg = bot.send_message(chat_id, 'Вы сейчас ничего не отслеживаете.')
                bot.register_next_step_handler(msg, findingHandler)
        elif message.text == '🔬 Добавить':

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

            row2_buttons = [types.KeyboardButton("Отмена")]
            markup.row(*row2_buttons)

            msg = bot.send_message(chat_id, 'Введите название контента для отслеживания. Если передумали что-либо добавлять, просто нажмите или напишите <b>Отмена</b>', parse_mode='HTML', reply_markup=markup)
            bot.register_next_step_handler(msg, enterFinding)
        elif(message.text == '🗑️ Удалить'):
            findstr = ''

            finding = user.get('finding', [])
            if len(finding) > 0:

                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

                row2_buttons = [types.KeyboardButton("Отмена")]
                markup.row(*row2_buttons)

                for index, text in enumerate(finding, start=1):
                    findstr += f'\n🔘 {index} - {text}'
                msg = bot.send_message(chat_id, 'Введите номер(число) элемента, который больше не хотите отслеживать. Если передумали что-либо удалять, просто нажмите или напишите <b>Отмена</b> \n' + findstr, reply_markup=markup, parse_mode='HTML')

                bot.register_next_step_handler(msg, deleteFinding)
            else:
                msg = bot.send_message(chat_id, 'У вас нет активных отслеживаний')
                bot.register_next_step_handler(msg, findingHandler)
        elif(message.text == '🖌️ Изменить'):
            findstr = ''

            finding = user.get('finding', [])
            if len(finding) > 0:

                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

                row2_buttons = [types.KeyboardButton("Отмена")]
                markup.row(*row2_buttons)

                for index, text in enumerate(finding, start=1):
                    findstr += f'\n🔘 {index} - {text}'
                msg = bot.send_message(chat_id, 'Введите номер(число) элемента, который хотите изменить. Если передумали что-либо менять, просто нажмите или напишите <b>Отмена</b>\n' + findstr, reply_markup=markup, parse_mode='HTML')

                bot.register_next_step_handler(msg, editFinding)
            else:
                msg = bot.send_message(chat_id, 'У вас нет активных отслеживаний')
                bot.register_next_step_handler(msg, findingHandler)

        else:
            if message.content_type == 'voice' or content.startswith('/start') or content.startswith('/find') or content.startswith('/stop') or content.startswith('/info') or content.startswith('/watched') or content.startswith('/later') or content.startswith('/match') or content.startswith('/premiers') or content.startswith('/top10') or content.startswith('/random'):
                msg = bot.reply_to(message, f"Данная команда не является допустимой во вкладке <b>🕰️ Отслеживать</b>\n\nДля выполнения данной команды вернитесь на главную страницу через команду <b>/home</b> или нажав кнопку <b>🏠 Главная страница</b>", parse_mode='HTML')
                bot.register_next_step_handler(msg, findingHandler)
                return

            if 'finding' not in user:
                user['finding'] = []

            if content not in user['finding']:
                user['finding'].append(content)
                users_collection.update_one({'user_id': user_id}, {'$set': user})
                msg = bot.reply_to(message, f"Отслеживание по запросу '{content}' началось. Как только мы получим обновленную информацию по интересующему вас контенту - мы сразу жевас оповестим.\n\nОповещение может происходить при:\n🔘Появление нового фильма\n🔘Выход новой серии сериала\n🔘Появлении нового сезона и т.д.\n\nНо вы всегда можетенайти то, что вас интересовало по запросу, достаточно зайти во вкладку <b>🕰️ Отслеживать</b> и выбрать интересующий вас запрос", parse_mode='HTML')
            else:
                msg = bot.reply_to(message, f"Отслеживание по запросу '{content}' не может быть начато, так как запрос с подобным содержанием уже имеется.\nПроверьте списокактуальных отслеживаний во вкладке <b>📁 Посмотреть</b>", parse_mode='HTML')
            bot.register_next_step_handler(msg, findingHandler)

def enterFinding(message):

    chat_id = message.chat.id
    content = message.text
    msg = None

    user_id = message.from_user.id
    user = users_collection.find_one({'user_id': user_id})

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    row2_buttons = [types.KeyboardButton("🏠 Главная страница")]
    markup.row(*row2_buttons)

    row3_buttons = [types.KeyboardButton("🔬 Добавить"), types.KeyboardButton("🗑️ Удалить"), types.KeyboardButton("🖌️ Изменить")]
    markup.row(*row3_buttons)

    row4_buttons = [types.KeyboardButton("📁 Посмотреть")]
    markup.row(*row4_buttons)

    if(message.content_type == 'voice'):
        msg = bot.send_message(chat_id, '🔍Ой! Голосовой поиск может быть произведен только на главной странице.🤔')
        bot.register_next_step_handler(msg, find_conent)
        return

    if content.lower() == 'отмена' or content.lower() == 'cancel':
        msg = bot.reply_to(message, f"Отмена запроса на добавление в <b>🕰️ Отслеживать</b>", parse_mode='HTML', reply_markup=markup)
        bot.register_next_step_handler(msg, findingHandler)
        return

    if 'finding' not in user:
        user['finding'] = []

    if content not in user['finding']:
        user['finding'].append(content)
        users_collection.update_one({'user_id': user_id}, {'$set': user})
        msg = bot.reply_to(message, f"Отслеживание по запросу '{content}' началось. Как только мы получим обновленную информацию по интересующему вас контенту - мы сразу же вас оповестим.\n\nОповещение может происходить при:\n🔘Появление нового фильма\n🔘Выход новой серии сериала\n🔘Появлении нового сезона и т.д.\n\nНо вы всегда можете найти то, что вас интересовало по запросу, достаточно зайти во вкладку <b>🕰️ Отслеживать</b> и выбрать интересующий вас запрос", parse_mode='HTML', reply_markup=markup)
    else:
        msg = bot.reply_to(message, f"Отслеживание по запросу '{content}' не может быть начато, так как запрос с подобным содержанием уже имеется.\nПроверьте список актуальных отслеживаний во вкладке <b>📁 Посмотреть</b>", parse_mode='HTML', reply_markup=markup)

    bot.register_next_step_handler(msg, findingHandler)

def deleteFinding(message):
    chat_id = message.chat.id
    content = message.text
    msg = None

    user_id = message.from_user.id
    user = users_collection.find_one({'user_id': user_id})
    finding = user.get('finding', [])

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    row2_buttons = [types.KeyboardButton("🏠 Главная страница")]
    markup.row(*row2_buttons)

    row3_buttons = [types.KeyboardButton("🔬 Добавить"), types.KeyboardButton("🗑️ Удалить"), types.KeyboardButton("🖌️ Изменить")]
    markup.row(*row3_buttons)

    row4_buttons = [types.KeyboardButton("📁 Посмотреть")]
    markup.row(*row4_buttons)

    if(message.content_type == 'voice'):
        msg = bot.send_message(chat_id, '🔍Ой! Голосовой поиск может быть произведен только на главной странице.🤔')
        bot.register_next_step_handler(msg, find_conent)
        return

    if content.lower() == 'отмена' or content.lower() == 'cancel':
        msg = bot.reply_to(message, f"Отмена запроса на удаление", parse_mode='HTML', reply_markup=markup)
        bot.register_next_step_handler(msg, findingHandler)
        return

    if int(content) - 1 >= 0 and int(content) - 1 < len(finding):
        item = user['finding'].pop(int(content) - 1)
        users_collection.update_one({'user_id': user_id}, {'$set': user})
        findstr = ''

        for index, text in enumerate(user['finding'], start=1):
            findstr += f'\n🔘 {index} - {text}'

        msg = bot.send_message(chat_id, f'Отслеживание по запросу <b>{item}</b> было отменено.\n\nАктивные запросы:\n' + (findstr if len(user['finding']) > 0 else 'нет'), parse_mode='HTML', reply_markup=markup)
        bot.register_next_step_handler(msg, findingHandler)
    else:
        msg = bot.send_message(chat_id, 'Введенное вами значение не может быть найдено, проверьте и запросите удаление еще раз', reply_markup=markup)
        bot.register_next_step_handler(msg, findingHandler)

def editFinding(message):
    chat_id = message.chat.id
    content = message.text
    msg = None

    user_id = message.from_user.id
    user = users_collection.find_one({'user_id': user_id})
    finding = user.get('finding', [])

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    row2_buttons = [types.KeyboardButton("🏠 Главная страница")]
    markup.row(*row2_buttons)

    row3_buttons = [types.KeyboardButton("🔬 Добавить"), types.KeyboardButton("🗑️ Удалить"), types.KeyboardButton("🖌️ Изменить")]
    markup.row(*row3_buttons)

    row4_buttons = [types.KeyboardButton("📁 Посмотреть")]
    markup.row(*row4_buttons)

    if(message.content_type == 'voice'):
        msg = bot.send_message(chat_id, '🔍Ой! Голосовой поиск может быть произведен только на главной странице.🤔')
        bot.register_next_step_handler(msg, find_conent)
        return

    if content.lower() == 'отмена' or content.lower() == 'cancel':
        msg = bot.reply_to(message, f"Отмена запроса на редактирование", parse_mode='HTML', reply_markup=markup)
        bot.register_next_step_handler(msg, findingHandler)
        return


    if int(content) - 1 >= 0 and int(content) - 1 < len(finding):
        item = user['finding'][int(content) - 1]
        user['finding'][int(content) - 1] = 'replace_element_event#'+user['finding'][int(content) - 1]

        users_collection.update_one({'user_id': user_id}, {'$set': user})

        msg = bot.reply_to(message, f'Введите изменный запрос отслеживания для элемента <b>{item}</b>:', parse_mode='HTML')
        bot.register_next_step_handler(msg, editFindingEnter)
    else:
        msg = bot.send_message(chat_id, 'Введенное вами значение не может быть найдено, проверьте и запросите изменение еще раз', reply_markup=markup)
        bot.register_next_step_handler(msg, findingHandler)

def editFindingEnter(message):
    chat_id = message.chat.id
    content = message.text
    msg = None

    user_id = message.from_user.id
    user = users_collection.find_one({'user_id': user_id})

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    row2_buttons = [types.KeyboardButton("🏠 Главная страница")]
    markup.row(*row2_buttons)

    row3_buttons = [types.KeyboardButton("🔬 Добавить"), types.KeyboardButton("🗑️ Удалить"), types.KeyboardButton("🖌️ Изменить")]
    markup.row(*row3_buttons)

    row4_buttons = [types.KeyboardButton("📁 Посмотреть")]
    markup.row(*row4_buttons)

    index = next(index for index, item in enumerate(user['finding']) if item.startswith('replace_element_event'))

    if(message.content_type == 'voice'):
        msg = bot.send_message(chat_id, '🔍Ой! Голосовой поиск может быть произведен только на главной странице.🤔')
        bot.register_next_step_handler(msg, find_conent)
        return

    if content.lower() == 'отмена' or content.lower() == 'cancel':
        msg = bot.reply_to(message, f"Отмена запроса на редактирование", parse_mode='HTML', reply_markup=markup)
        bot.register_next_step_handler(msg, findingHandler)
        user['finding'][index] = user['finding'][index].split('#')[1]
        users_collection.update_one({'user_id': user_id}, {'$set': user})
        return
    try:

        if content in user['finding']:
            msg = bot.reply_to(message, f'Данное изменение не может быть применино, такой запрос уже существует. Попробуйте еще раз:', parse_mode='HTML')
            bot.register_next_step_handler(msg, editFindingEnter)
            return

        user['finding'][index] = content
        users_collection.update_one({'user_id': user_id}, {'$set': user})
        findstr = ''

        for index, text in enumerate(user['finding'], start=1):
            findstr += f'\n🔘 {index} - {text}'

        msg = bot.send_message(chat_id, f'Запрос на отслеживание был успешно изменен\n\nАктивные запросы:\n' + (findstr if len(user['finding']) > 0 else 'нет'), parse_mode='HTML', reply_markup=markup)
        bot.register_next_step_handler(msg, findingHandler)
    except ValueError:
        msg = bot.send_message(chat_id, 'Вы не указали номер элемента для изменения.', reply_markup=markup)
        bot.register_next_step_handler(msg, findingHandler) 

@bot.message_handler(commands=['start'])
def start_message(message):

    option_menu_1 = types.BotCommand(command='start', description='Запустить бота')
    option_menu_2 = types.BotCommand(command='home', description='Главный экран')
    option_menu_3 = types.BotCommand(command='find', description='Найти')
    option_menu_4 = types.BotCommand(command='stop', description='Остановить поиск')
    option_menu_5 = types.BotCommand(command='info', description='Помощь')
    option_menu_6 = types.BotCommand(command='watched', description='Просмотренные')
    option_menu_7 = types.BotCommand(command='later', description='На потом')
    option_menu_8 = types.BotCommand(command='match', description='Подборки')
    option_menu_9 = types.BotCommand(command='premiers', description='Премьеры')
    option_menu_10 = types.BotCommand(command='top10', description='Топ 10')
    option_menu_11 = types.BotCommand(command='random', description='Случайный фильм')
    bot.set_my_commands([
        option_menu_1,
        option_menu_2,
        option_menu_3,
        option_menu_4,
        option_menu_5,
        option_menu_6,
        option_menu_7,
        option_menu_8,
        option_menu_9,
        option_menu_10,
        option_menu_11,
    ])
    bot.set_chat_menu_button(message.chat.id, types.MenuButtonCommands('commands'))

    user_id = message.from_user.id

    existing_user = users_collection.find_one({'user_id': user_id})

    # Add two buttons below the input field
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    # row1_buttons = [types.KeyboardButton("Home")]
    # markup.row(*row1_buttons)

    row2_buttons = [types.KeyboardButton("🔍 Найти"), types.KeyboardButton("✔️ Просмотрено"), types.KeyboardButton("⏰ На потом")]
    markup.row(*row2_buttons)
    row3_buttons = [types.KeyboardButton("📰 Статистика"), types.KeyboardButton("🕰️ Отслеживать"), types.KeyboardButton("ℹ Помощь")]
    markup.row(*row3_buttons)
    row4_buttons = [types.KeyboardButton("🗳️ Подборки"), types.KeyboardButton("💥 Премьеры"), types.KeyboardButton("🥇 Топ 10")]
    markup.row(*row4_buttons)

    if not existing_user:
        # bot.reply_to(message, 'Вы номенький? Давайте я немного расскажу о себе!', reply_markup=markup)
        bot.reply_to(message, '''
Привет! 🌟 Готов к кино приключениям? 🍿
Напиши мне, что хочешь посмотреть сегодня, и мы найдем для тебя идеальный вариант! 😊

Если хочешь найти фильм, используй команду <b>Найти</b> и вписывай названия. Писать можно сколько угодно, список постоянно будет обновляться. Если нашел, напиши стоп или stop, поиск закончится. Во время поиска, нижнее меню будет недоступно.
Так же можешь написать предложение, и наша нейросеть определит, что ты нужно сделать. Общаться с ней можно в свободной форме, как с человеком, но на всякий случай она будет уточнять результата обработки. Пример запроса:

<i>Например, <b>"Привет! Вчера друзья мне рассказали про классный фильм Шерлок Холм. Найдешь где его можно посмотреть?"</b></i>

Так же возможно у нее попросить что-либо отследить, в таком случае напиши «отследи» и название желаемого контента, в результате будут выведены все совпадения. А в дальнейшем бот будет присылать сообщения, если ему удалось что-либо обнаружить подходящее по названию.

Общайся с ней текстовыми сообщениями или голосовыми, она разберется и обязательно тебе поможет.

Остальное описание функциональности бота можно найти во вкладке <b>Помощь</b>. Счастливого просмотра! 🎬
''', parse_mode='HTML', reply_markup=markup)
        new_user = {'user_id': user_id, 'language': 'ru_RU'}
        users_collection.insert_one(new_user)
    else:
        bot.reply_to(message, 'Привет! 🌟 Какие фильмы или сериалы ты хочешь посмотреть сегодня? 🍿✨', reply_markup=markup)


# Handle the button clicks - in ["Clear", "Watched", "Favorites genres", "View collections"]
@bot.message_handler(func=lambda message: message.text)
def handle_buttons(message):
    user_id = message.from_user.id
    user = users_collection.find_one({'user_id': user_id})
    

    if message.text == "✔️ Просмотрено" or message.text.startswith("/watched"):
        # Retrieve and display the list of watched movies
        user = users_collection.find_one({'user_id': user_id})
        watched_movies = None
        if 'watched' in user:
            watched_movies = user.get('watched', [])
        else: 
            bot.send_message(user_id, "Ваш список просмотренных фильмов пока пуст, но вы всегда можете что-то сюда добавить")
            return
        
        rating_list = user.get('rating', [])
        if watched_movies:
            
            inline_keyboard = []

            for movie in watched_movies:
                # Ищем оценку по id фильма в rating_list
                rating_object = next((item for item in rating_list if item['id'] == movie['id']), {'value': 0})
                rating = rating_object['value']

                # Создаем эмодзи для рейтинга (звезда)
                button_text = f"{movie['name']}{f' - {rating}/5' if rating > 0 else ''}"
                callback_data = f"movie:{movie['id']}"
                inline_keyboard.append([types.InlineKeyboardButton(button_text, callback_data=callback_data)])


            markup = types.InlineKeyboardMarkup(inline_keyboard)
            new_last_message_id = True
            users_collection.update_one({'user_id': user_id}, {'$set': {'isWatched': new_last_message_id}})


            bot.send_message(user_id, f"Привет! 🌟 Вот список фильмов, которые вы уже посмотрели.\n\nВы можете кликнуть по каждому фильму🤩, чтобы посмотреть его карточку и, при необходимости, изменить информацию. 🎬✨\n\n\n", reply_markup=markup)
        else:
            bot.send_message(user_id, "🎬 Кажется, список фильмов пуст. Давайте найдем фильм и отметим его как просмотренный!")
    elif message.text == '🏠 Главная страница' or message.text == '/home':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        # row1_buttons = [types.KeyboardButton("Home")]
        # markup.row(*row1_buttons)

        row2_buttons = [types.KeyboardButton("🔍 Найти"), types.KeyboardButton("✔️ Просмотрено"), types.KeyboardButton("⏰ На потом")]
        markup.row(*row2_buttons)

        row3_buttons = [types.KeyboardButton("📰 Статистика"), types.KeyboardButton("🕰️ Отслеживать"), types.KeyboardButton("ℹ Помощь")]
        markup.row(*row3_buttons)

        row4_buttons = [types.KeyboardButton("🗳️ Подборки"), types.KeyboardButton("💥 Премьеры"), types.KeyboardButton("🥇 Топ 10")]
        markup.row(*row4_buttons)

        bot.send_message(user_id, '''
Привет! 🌟 Готов к кино приключениям? 🍿
Напиши мне, что хочешь посмотреть сегодня, и мы найдем для тебя идеальный вариант! 😊

Если хочешь найти фильм, используй команду <b>Найти</b> и вписывай названия. Писать можно сколько угодно, список постоянно будет обновляться. Если нашел, напиши стоп или stop, поиск закончится. Во время поиска, нижнее меню будет недоступно.
Так же можешь написать предложение, и наша нейросеть определит, что ты нужно сделать. Общаться с ней можно в свободной форме, как с человеком, но на всякий случай она будет уточнять результата обработки. Пример запроса:

<i>Например, <b>"Привет! Вчера друзья мне рассказали про классный фильм Шерлок Холм. Найдешь где его можно посмотреть?"</b></i>

Так же возможно у нее попросить что-либо отследить, в таком случае напиши «отследи» и название желаемого контента, в результате будут выведены все совпадения. А в дальнейшем бот будет присылать сообщения, если ему удалось что-либо обнаружить подходящее по названию.

Общайся с ней текстовыми сообщениями или голосовыми, она разберется и обязательно тебе поможет.

Остальное описание функциональности бота можно найти во вкладке <b>Помощь</b>. Счастливого просмотра! 🎬
''', reply_markup=markup, parse_mode='HTML')
    elif message.text == '🔍 Найти':

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        row2_buttons = [types.KeyboardButton("Стоп")]
        markup.row(*row2_buttons)

        msg = bot.send_message(message.chat.id, 'Вводите название интересующего вас фильма, а мы будет выдавать рузельтаты списком. Если хотите остановиться, напишите стоп или stop.\n\nВнимание: пока вы не остановитесь меню будет недоступно!', reply_markup=markup)

        bot.register_next_step_handler(msg, find_conent)

    elif message.text == '⏰ На потом' or message.text.startswith("/later"):
        user = users_collection.find_one({'user_id': user_id})
        watched_movies = None
        if 'later' in user:
            watched_movies = user.get('later', [])
        else: 
            bot.send_message(user_id, "Ваш список запланированных к просмотру фильмов пока пуст, но вы всегда можете это исправить")
            return
        
        if watched_movies:
            
            inline_keyboard = []

            for movie in watched_movies:

                # Создаем эмодзи для рейтинга (звезда)
                button_text = f"{movie['name']}"
                callback_data = f"movie:{movie['id']}"
                inline_keyboard.append([types.InlineKeyboardButton(button_text, callback_data=callback_data)])

            markup = types.InlineKeyboardMarkup(inline_keyboard)
            new_last_message_id = True
            users_collection.update_one({'user_id': user_id}, {'$set': {'isWatched': new_last_message_id}})


            bot.send_message(user_id, f"Привет! 🌟 Вот список фильмов, которые вы оставили на потом.\n\nВы можете кликнуть по каждому фильму🤩, чтобы посмотреть его карточку и, при необходимости, изменить информацию. 🎬✨\n\n\n", reply_markup=markup)
        else:
            bot.send_message(user_id, "🎬 Список фильмов пуст. Найдите фильм и запишите, чтобы не забыть посмотреть позже.")
    elif message.text == '🗳️ Подборки' or message.text.startswith("/match"):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        row2_buttons = [types.KeyboardButton("🏠 Главная страница")]
        markup.row(*row2_buttons)

        row3_buttons = [types.KeyboardButton("😍 Любимый жанр"), types.KeyboardButton("🎉 По темам")]
        markup.row(*row3_buttons)

        row4_buttons = [types.KeyboardButton("🎲 Случайный фильм")]
        markup.row(*row4_buttons)

        bot.send_message(user_id, "📋 Добро пожаловать в раздел подборок! \n\n🔍Здесь вы найдете тематические подборки, подборки по жанру и случайные фильмы. 💡 Если вы хотите предложить новые виды подборок, то можете написать сообщение на аккаунт _________", reply_markup=markup)
    elif message.text == '🎲 Случайный фильм' or message.text.startswith("/random"):
        deep_info_url = f'https://api.kinopoisk.dev/v1.4/movie/random?lists=top250'
        kino_dev = '8W83T87-DV244BK-PEE7PXK-6PS64WX'

        headers_deep = {
            'accept': 'application/json',
            'X-API-KEY': kino_dev
        }

        response_random = requests.get(deep_info_url, headers=headers_deep)
        random_item = response_random.json()

        movie_details, photo_url, movie_name, genres, firmUrl = get_movie_details(random_item["id"])

        # Создание кнопок
        markup = types.InlineKeyboardMarkup()
        # Проверяем, добавлен ли фильм в просмотренные
        is_watched = any(movie.get('id') == random_item["id"] for movie in user.get('watched', []))
        is_later = any(movie.get('id') == random_item["id"] for movie in user.get('later', []))

        if is_watched:
            markup.add(types.InlineKeyboardButton("Удалить из просмотренных", callback_data=f"unwatched:{random_item['id']}:without"))
        else:
            markup.add(types.InlineKeyboardButton("Добавить в просмотренное", callback_data=f"watched:{random_item['id']}:without"))

        if not is_later:
            markup.add(types.InlineKeyboardButton("Посмотреть позже", callback_data=f"watch_later:{random_item['id']}:without"))
        else:
            markup.add(types.InlineKeyboardButton("Убрать из посмотреть позже", callback_data=f"unwatch_later:{random_item['id']}:without"))

        random_last = bot.send_photo(user_id, photo_url, caption=movie_details, parse_mode='HTML', reply_markup=markup)
        # user['last_message_id'] = 
        users_collection.update_one({'user_id': user_id}, {'$set': {'last_message_id': random_last.message_id}})

    elif message.text == '🥇 Топ 10' or message.text.startswith("/top10"):
        category = 'top10-hd'

        base_url = f'https://api.kinopoisk.dev/v1.4/movie?page=1&limit=10&lists={category}'
        api_key = '8W83T87-DV244BK-PEE7PXK-6PS64WX'

        headers = {
            'accept': 'application/json',
            'X-API-KEY': api_key
        }

        response = requests.get(base_url, headers=headers)
        movies = []

        print(response.json())

        if response.status_code == 200:
            movies_data = response.json()
            items = movies_data.get('docs', [])

            # Извлечение nameRu для каждого фильма
            filtered_movies = [{'name': movie.get('name'), 'id': movie.get('id')} for movie in items if (movie.get('type') == 'movie' or movie.get('type') == 'tv-series')]

            movies = filtered_movies
        else:
            print(f"Error: {response.status_code}")
            movies = []

        send_movies_results(bot, user_id, movies, 'найди', '')
    elif message.text == '💥 Премьеры' or message.text.startswith("/premiers"):
        category = 'the_closest_releases'

        base_url = f'https://api.kinopoisk.dev/v1.4/movie?page=1&limit=10&lists={category}'
        api_key = '8W83T87-DV244BK-PEE7PXK-6PS64WX'

        headers = {
            'accept': 'application/json',
            'X-API-KEY': api_key
        }

        response = requests.get(base_url, headers=headers)
        movies = []

        print(response.json())

        if response.status_code == 200:
            movies_data = response.json()
            items = movies_data.get('docs', [])

            # Извлечение nameRu для каждого фильма
            filtered_movies = [{'name': movie.get('name'), 'id': movie.get('id')} for movie in items if (movie.get('type') == 'movie' or movie.get('type') == 'tv-series')]

            movies = filtered_movies
        else:
            print(f"Error: {response.status_code}")
            movies = []

        send_movies_results(bot, user_id, movies, 'найди', '')
    elif message.text == '/stop':
        bot.send_message(user_id, "Данная команда доступна только для остановки поиска через элемент меню '🔍 Найти'.")
    elif message.text == '🕰️ Отслеживать':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        row2_buttons = [types.KeyboardButton("🏠 Главная страница")]
        markup.row(*row2_buttons)

        row3_buttons = [types.KeyboardButton("🔬 Добавить"), types.KeyboardButton("🗑️ Удалить"), types.KeyboardButton("🖌️ Изменить")]
        markup.row(*row3_buttons)

        row4_buttons = [types.KeyboardButton("📁 Посмотреть")]
        markup.row(*row4_buttons)

        msg = bot.send_message(user_id, "🕰️ В этом окне вы можете управлять отслеживаемым контентом.\n\nВы можете добавлять, удалять, иизменять запрос или просмотреть все совпадения по контенту.\n\nЕсли, в данном разделе, вы просто напиши желаемое название, то это будет расцениваться как добавление запроса.", reply_markup=markup)
        bot.register_next_step_handler(msg, findingHandler)

    elif message.text == '🎉 По темам':
        
        navigation_buttons = []
        navigation_buttons.append(
            [
                types.InlineKeyboardButton("💥 Премьеры", callback_data="collection&the_closest_releases"),
                types.InlineKeyboardButton("🔥 Популярные", callback_data="collection&bestofamediateka")
            ],
        )

        navigation_buttons.append(
            [
                types.InlineKeyboardButton("🥇 Топ 10", callback_data="collection&top10-hd"),
                types.InlineKeyboardButton("🤣 Комедии", callback_data="collection&family_comedies")
            ],

        )
        
        navigation_buttons.append(
            [
                types.InlineKeyboardButton("👑 Лучшее 2023", callback_data="collection&top20of2023"),
                types.InlineKeyboardButton("🎄 Новый год", callback_data="collection&ny_family")
            ]
        )

        navigation_buttons.append(
            [
                types.InlineKeyboardButton("🛋️ Семейное", callback_data="collection&hd-family")
            ]
        )

        inline_keyboard = navigation_buttons
        keyboard = types.InlineKeyboardMarkup(inline_keyboard)

        bot.send_message(user_id, "🎁 Наши тематические подборки фильмов ждут вас!", reply_markup=keyboard)
    elif message.text == "😍 Любимый жанр":
        watched_movies = []
        if 'watched' in user:
            watched_movies = user.get('watched', [])

        all_genres = [genre for movie in watched_movies for genre in movie.get('genres', [])]

        if len(all_genres) > 0:
            genre_counts = {}
            for genre in all_genres:
                genre_counts[genre] = genre_counts.get(genre, 0) + 1

            unique_genres = sorted(set(all_genres), key=lambda x: genre_counts[x], reverse=True)
            favorite_genres = unique_genres[:3]

            navigation_buttons = []

            for item in favorite_genres:
                navigation_buttons.append(
                [
                    types.InlineKeyboardButton(item.capitalize(), callback_data=f"genre_list&{item}"),
                ]
            )
            inline_keyboard = navigation_buttons
            keyboard = types.InlineKeyboardMarkup(inline_keyboard)
            
            bot.send_message(user_id, "❣️ Выберите ваш любимый жанр и мы соберем с ним подборку!", reply_markup=keyboard)

        else:
            bot.send_message(user_id, "😿 Мы не можем предоставить вам подборку по любимому жанру, для начала добавьте фильмы в просмотренные и поставьте им оценку, а после этого вернитесь в <b>🗳️ Подборки</b> ")
                  

    elif message.text == "📰 Статистика" or message.text.startswith("/stats"):
        # Retrieve user's watched movies and genres
        user = users_collection.find_one({'user_id': user_id})
        watched_movies = []
        if 'watched' in user:
            watched_movies = user.get('watched', [])

        
        # Extract genres from watched movies
        all_genres = [genre for movie in watched_movies for genre in movie.get('genres', [])]
        if len(all_genres) == 0:
            all_genres = ['Помечайте фильмы как просмотренные и ставьте оценки. Мы покажем ваши любимые жанры']

        # Create a dictionary to count the occurrences of each genre
        genre_counts = {}
        for genre in all_genres:
            genre_counts[genre] = genre_counts.get(genre, 0) + 1

        # Create a list of unique genres in descending order of occurrence
        unique_genres = sorted(set(all_genres), key=lambda x: genre_counts[x], reverse=True)

        ratings = user.get('rating', [])
        total_ratings = len(ratings)
        average_rating = 0

        if total_ratings > 0:
            total_sum = sum(rating['value'] for rating in ratings)  # Суммируем все значения рейтингов
            average_rating = round(total_sum / total_ratings, 1)  # Вычисляем средний балл
        else:
            total_ratings = 'Оценивайте фильмы, чтобы мы понимали ваши предпочтения.'

        later_list = user.get('later', [])
        later_list_len = len(later_list)
        print(later_list)

        if later_list_len <= 0:
            later_list_len = 'Находи фильмы и сохраняйте в лист ожидания "На потом"'

        finding = user.get('finding', [])
        finding_len = len(finding)
        print(finding_len)

        if finding_len <= 0:
            finding_len = 'Чего-то очень сильно ждете? Расскажите нам об этом, а мы вам сообщим, когда будет возможность посмотреть.'

        # Display the list of favorite genres with counts
        # genres_with_counts = [f"{genre}: {genre_counts[genre]}" for genre in unique_genres]
        bot.send_message(user_id, f"<b>🌟📖 Вот некоторая информация о вас:</b>\n\n<b>Ваши самые любимые жанры:</b> 😍 {', '.join(unique_genres[:3])}\n\n<b>Скольки фильмов/сериалов вы посмотрели:</b> 🧮 {len(watched_movies) if len(watched_movies) > 0 else 'Если вы посмотрели фильм, то находите его и добавляйте в Просмотрено, это поможет подбирать контент именно под вас!'}\n\n<b>Сколько фильмов вы отложили на потом:</b> ⏰ {later_list_len}\n\n<b>Сколько фильмов вы оценили:</b> 👍 {total_ratings}\n\n<b>Сколько фильмов вы ожидаете:</b> ⌛ {finding_len}\n\n\n<b>🚀 Чем больше вы пользуетесь данным ботом, тем более точную информацию мы сможем вам предоставить!🤓</b>", parse_mode='HTML')
    elif message.text == "Match film by genre":
        # Retrieve user's watched movies and genres
        user = users_collection.find_one({'user_id': user_id})
        watched_movies = None
        if 'watched' in user:
            watched_movies = user.get('watched', [])
        else: 
            bot.send_message(user_id, "Вы не можете попасть сюда, так как о вас нет информации")
            return

        # Extract genres from watched movies
        all_genres = None
        if 'genres' in user:
            all_genres = [genre for movie in watched_movies for genre in movie.get('genres', [])]
        else: 
            bot.send_message(user_id, "Вы не можете попасть сюда, так как о вас нет информации")
            return

        # Create a dictionary to count the occurrences of each genre
        genre_counts = {}
        for genre in all_genres:
            genre_counts[genre] = genre_counts.get(genre, 0) + 1

        # Create a list of unique genres in descending order of occurrence
        unique_genres = sorted(set(all_genres), key=lambda x: genre_counts[x], reverse=True)

        # Display the list of favorite genres with counts
        genres_with_counts = [f"{genre}: {genre_counts[genre]}" for genre in unique_genres]

        # Number of genres to display
        genres_to_display = 4

        # Create a ReplyKeyboardMarkup
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        row1_buttons = []
        # Iterate over the first 'genres_to_display' genres
        for i in range(min(genres_to_display, len(unique_genres))):
            genre = unique_genres[i]
            # Add a button to the markup
            row1_buttons.append(types.KeyboardButton(genre))

        markup.row(*row1_buttons)

        # Add the "Home" button in a new row
        markup.row(types.InlineKeyboardButton("🏠 Главная страница"))

        bot.send_message(user_id, "В меню перечислены ваши любимые жанры, выберете жанр и мы соберем подборку для ВАС:", reply_markup=markup)
    elif message.text == "ℹ Помощь" or message.text.startswith("/info"):
        bot.send_message(user_id, '''
Инструкция по работе с ботом:

<b>Поиск контента</b>: 
- если не помните название фильма или сериала, но помните его сюжет, то попросите нейросеть помочь. Для этого напиши текстовое или голосовое сообщение, в котором будет команда «помоги» или «подскажи» и ваше описание. После этого нейросеть попробует определить название фильма. 
Помните, чем точнее вы ей опишите сюжет фильма, тем выше шанс получить верный ответ. 
- поиск по команде «/find название»
- написать сообщение на главной странице с уточнением команды «найти», можно использовать похожие по смыслу слова, главное, чтобы нейросеть понимала.
- нажать по кнопке «Найти», после чего откроется бесконечное поле ввода, можно искать что угодно, когда надоест нажать «Стоп»
- можно написать название фильма, сериала, мультика и тд. Нейросеть автоматически подставит команду найти.
- можно добавить в отслеживаемое и самостоятельно проверять актуальный контент по запросу. Для этого надо зайти во вкладку «Отслеживать», нажать «Показать» и выбрать элемент. В результате будет показан список совпадения по запросу.

<b>Просмотр</b>:
Возможно сохранение всего просмотренного, надо найти контент и отметить, как просмотренный. Если ранее контент был добавлен в окно «На потом», то можно отметить, как просмотренный, там.
Просмотренные фильмы и оценки для просмотренного кино влияют на любимый жанры и личные рекомендации.

<b>На потом</b>
Возможно сохранение контента на просмотр позднее, надо найти контент и отметить, как «посмотреть позже». 

<b>Статистика</b>
Информация по вашему аккаунту, можно узнать любимые жанры, количество просмотренных фильмов, количество оцененных фильмов и т.д.

<b>Отслеживать</b>
Добавляйте отслеживание контента через вкладку «Отслеживать». Вам достаточно указать название картины для отслеживания, а всю остальную работы, мы сделаем за вас. (отследим выход новых фильмов серии, выход новых сезонов, окончание сезона сериала и т.д.)

<b>Подборки</b>
Вкладка с подборками по вашим любимым жанрам и тематические подборки. В каждой подборке хранится список с фильмами, который вы можете добавить «на потом» или отметить, как уже просмотренный, и выставить оценку.
А если не знаете, что посмотреть и не хотите ковыряться в подборках, то можете довериться судьбе и выбрать контент из вкладки «Случайный». 

''', parse_mode='HTML')
    elif message.text.startswith("/find"):

        parts = message.text.split(' ')

        if len(parts) >= 2 and parts[0] == "/find":
            name = ' '.join(parts[1:])

            if name and any(c.isalnum() for c in name):
                print("Найденное имя:", name)
            else:
                name = None
                print("После /find не найдено буквенных символов, записываем null")
        else:
            name = None
            print("Сообщение не начинается с /find или не содержит никакого текста после /find")

        if(name):
            # bot.send_message(user_id, f"Вот ваше название фильма: {name}", parse_mode='HTML')
            movies = search_movies(name)
            send_movies_results(bot, user_id, movies, 'найди', name)
            return

        bot.send_message(user_id, "Я вас не понял. Уточните название фильма или сериала, что вы хотите найти. Вам нужно добавить название кинокартины сразу после команды. 🎥🔍", parse_mode='HTML')
    else:
        # Display the selected genre
        
        genre_to_id = {genre["genre"]: genre["id"] for genre in genres_array}

        selected_genre = message.text.lower()  # Convert to lowercase for case-insensitivity

        if selected_genre in genre_to_id:

            bot.send_message(user_id, f"Вы выбрали жанр: {message.text}")
            
            # Display the selected id
            selected_id = genre_to_id[selected_genre]
            bot.send_message(user_id, f"Вы выбрали жанр с id: {selected_id}")

            # The API endpoint
            url = 'https://kinopoiskapiunofficial.tech/api/v2.2/films'

            # Parameters for the request
            params = {
                'genres': selected_id,
                'order': 'RATING',
                'type': 'ALL',
                'ratingFrom': 0,
                'ratingTo': 10,
                'yearFrom': 1000,
                'yearTo': 3000,
                'page': random.randint(1, 5)
            }

            # The API key header
            headers = {
                'accept': 'application/json',
                'X-API-KEY': '6ea49ced-083a-4c2a-b622-9137ca531bd6'
            }

            # Sending the GET request
            response = requests.get(url, params=params, headers=headers)

            # Checking the response
            if response.status_code == 200:
                # Do something with the response.json() data
                data = response.json()
                
                # Extracting film details
                films = data.get('items', [])

                # Creating a formatted string for each film
                film_strings = []
                for index, film in enumerate(films, start=1):
                    film_id = film.get('kinopoiskId', '')
                    film_name = film.get('nameRu', '')
                    film_url = f"https://www.kinopoisk.ru/film/{film_id}/"

                    # Creating the formatted string
                    film_string = f"{index}) {film_name}, <a href='{film_url}'>Ссылка</a>"
    
                    # Appending to the list
                    film_strings.append(film_string)

                # Joining the strings with newline characters
                result_string = '\n'.join(film_strings)

                # Sending the message
                bot.send_message(user_id, f"Контент подобранный по жанру <b>{selected_genre}</b>: \n{result_string}", disable_web_page_preview=True, parse_mode='HTML')
            else:
                # Handle the error
                print(f"Error: {response.status_code}")
                print(response.text)
        else:
            bot.send_message(user_id, f"🎥 Пожалуйста, подождите всего несколько мгновений, пока наш нейропомошник проанализирует ваш запрос и онлайн кинотеатры, чтобы подобрать для вас наилучший результат... 🍿✨")
            text = message.text
            # command, content = extract_command_and_content(text)

            response_gpt = g4f.ChatCompletion.create(
                model=g4f.models.gpt_35_turbo,
                messages=[{
                    "role": "user",
                    "content": '''
Имеются следующие команды: найди, отслеживать, подскажи и не_найдено. 

Далее будет предоставлен текст, в котором тебе надо выделить команду из приведенных выше с максимальным совпадением по логике и название фильма, если в названии фильма имеются ошибки в написании, то необходимо их исправлять. 

Если в запросе пользователя нет команды, но возможно примерно определить название кинокартины, тогда подставляй команду найти.

Если в запросе пользователя невозможно определить название кинокартины, то необходимо подставить команду "не найдено", а поле film оставить пустой строкой.

Если в запросе пользователя имеется указание на помощь в поиске, например помоги или напомни, тогда надо вернуть команду «подскажи», а поле film будет храниться подсказку от тебя, что это за картина.

Правильный ответ предоставь строго в формате json с полями: command и film. Данные без визуального выделения формата json, только сырой ответ. 

Текст для расшифровки: ''' + text
                }]
            )

            # response_gpt = response_gpt.replace('json', '')

            print(response_gpt)

            if is_valid_json(response_gpt):
                data = json.loads(response_gpt)

                command, content = data['command'], data['film']

                if command and content:
                    user['last_command'] = command
                    user['last_content'] = content
                    users_collection.update_one({'user_id': user_id}, {'$set': user})

                    if command == 'подскажи':
                        bot.send_message(user_id, f"Вот что думаешь наш ассистент:\n\n<b>{content}</b>", parse_mode='HTML')
                        return

                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("Верно", callback_data="correct"),
                            types.InlineKeyboardButton("Неверно", callback_data="incorrect"))

                    response_message = f"🌟 Наша система учится всё время, и ваша помощь просто неоценима! Пожалуйста, проверьте, что всё работает как надо: \n\n<b>Вы попросили:</b> {command}\n<b>Название кинокартины:</b> {content}\n\nВсе верно?"
                    bot.send_message(user_id, response_message, parse_mode='HTML', reply_markup=markup)
                else:
                    bot.send_message(user_id, f"Мы не смогли определить название картины.\n\nИзвините, наш бот только учится распознавать названия и команды, проверьте корректность введенного названия, поставьте знаки припенания, при необходимости, и убедитесь в наличии команды и попробуйте еще раз.", parse_mode='HTML')
                    return
            else:
                bot.send_message(user_id, "😊 Ой, вы забыли указать доступную команду или название фильма, попробуйте еще раз!🔍")


@bot.message_handler(content_types=['voice'])
def voice_handler(message):
    user_id = message.from_user.id
    user = users_collection.find_one({'user_id': user_id})

    file_id = message.voice.file_id
    file = bot.get_file(file_id)

    file_size = file.file_size
    if int(file_size) >= 715000:
        bot.send_message(message.chat.id, 'Upload file size is too large.')
    else:
        download_file = bot.download_file(file.file_path)
        with open('audio.ogg', 'wb') as file:
            file.write(download_file)

        bot.send_message(user_id, f"🎥 Пожалуйста, подождите всего несколько мгновений, пока наш нейропомошник проанализирует ваш запрос и онлайн кинотеатры, чтобы подобрать для вас наилучший результат... 🍿✨")
        text = voice_recognizer(user['language'])

        response_gpt = g4f.ChatCompletion.create(
            model=g4f.models.gpt_35_turbo,
            messages=[{
                "role": "user",
                "content": '''
Имеются следующие команды: найди, отслеживать, подскажи и не_найдено. 

Далее будет предоставлен текст, в котором тебе надо выделить команду из приведенных выше с максимальным совпадением по логике и название фильма, если в названии фильма имеются ошибки в написании, то необходимо их исправлять. 

Если в запросе пользователя нет команды, но возможно примерно определить название кинокартины, тогда подставляй команду найти.

Если в запросе пользователя невозможно определить название кинокартины, то необходимо подставить команду "не найдено", а поле film оставить пустой строкой.

Если в запросе пользователя имеется указание на помощь в поиске, например помоги или напомни, тогда надо вернуть команду «подскажи», а поле film будет храниться подсказку от тебя, что это за картина.

Правильный ответ предоставь строго в формате json с полями: command и film. Данные без визуального выделения формата json, только сырой ответ. 

Текст для расшифровки: ''' + text
            }]
        )

        print(response_gpt)

        if is_valid_json(response_gpt):
            data = json.loads(response_gpt)
            command, content = data['command'], data['film']
            if command and content:
                user['last_command'] = command
                user['last_content'] = content
                users_collection.update_one({'user_id': user_id}, {'$set': user})
                if command == 'подскажи':
                    bot.send_message(user_id, f"Вот что думаешь наш ассистент:\n\n<b>{content}</b>", parse_mode='HTML')
                    return
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("Верно", callback_data="correct"),
                        types.InlineKeyboardButton("Неверно", callback_data="incorrect"))
                response_message = f"🌟 Наша система учится всё время, и ваша помощь просто неоценима! Пожалуйста, проверьте, что всё работает как надо: \n\n<b>Вы попросили:</b>{command}\n<b>Название кинокартины:</b> {content}\n\nВсе верно?"
                bot.send_message(user_id, response_message, parse_mode='HTML', reply_markup=markup)
            else:
                bot.send_message(user_id, f"Мы не смогли определить название картины.\n\nИзвините, наш бот только учится распознавать названия и команды, проверьте корректностьвведенного названия, поставьте знаки припенания, при необходимости, и убедитесь в наличии команды и попробуйте еще раз.", parse_mode='HTML')
                return
        else:
            bot.send_message(user_id, "😊 Ой, вы забыли указать доступную команду или название фильма, попробуйте еще раз!🔍")

@bot.callback_query_handler(func=lambda call: call.data in ["correct", "incorrect"])
def transcription_callback_handler(call):
    user_id = call.from_user.id
    user = users_collection.find_one({'user_id': user_id})

    # Check if the user was waiting for confirmation
    if 'last_command' in user and 'last_content' in user:
        if call.data == "correct":
            command = user['last_command']
            content = user['last_content']

            if command == "найди":
                movies = search_movies(content)
                send_movies_results(bot, user_id, movies, command, content)
            elif command == 'отслеживать':
                if 'finding' not in user:
                    user['finding'] = []

                if content not in user['finding']:
                    user['finding'].append(content)
                    users_collection.update_one({'user_id': user_id}, {'$set': user})

                    bot.send_message(user_id, f"Отслеживание по запросу '{content}' началось. Как только мы получим обновленную информацию по интересующему вас контенту - мы сразу же вас оповестим.\n\nОповещение может происходить при:\n🔘Появление нового фильма\n🔘Выход новой серии сериала\n🔘Появлении нового сезона и т.д.\n\nНо вы всегда можете найти то, что вас интересовало по запросу, достаточно зайти во вкладку <b>🕰️ Отслеживать</b> и выбрать интересующий вас запрос", parse_mode='HTML')
                else:
                    bot.send_message(user_id, f"Отслеживание по запросу '{content}' не может быть начато, так как запрос с подобным содержанием уже имеется.\nПроверьте вкладку <b>🕰️ Отслеживать</b>", parse_mode='HTML')
            else:
                bot.send_message(user_id, f"Данная команда еще не поддерживается, ма изучим возникшую проблему и разберемся с ней", parse_mode='HTML')

        elif call.data == "incorrect":
            bot.send_message(user_id, "Извините, наш бот только учится распознавать названия и команды, проверьте корректность введенного названия, поставьте знаки припенания, при необходимости, и убедитесь в наличии команды и попробуйте еще раз.")
        
        # Clear the last command and content
        users_collection.update_one({'user_id': user_id}, {'$unset': {'last_command': '', 'last_content': ''}})
    else:
        bot.send_message(user_id, "Неверный запрос.")

def add_punctuation_russian(text):
    if not text:
        return ""

    model_name = "arshad-bert-base-uncased-sentence"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForTokenClassification.from_pretrained(model_name)

    inputs = tokenizer(text, return_tensors="pt")
    outputs = model(**inputs)
    predictions = torch.argmax(outputs.logits, dim=2)

    restored_text = ""
    for token, pred_label in zip(tokenizer.convert_ids_to_tokens(inputs["input_ids"][0]), predictions[0]):
        if token.startswith("##"):
            restored_text = restored_text.rstrip() + token[2:]
        else:
            if pred_label == 1:
                restored_text = restored_text.rstrip() + token + " "
            else:
                restored_text += token + " "

    return restored_text.strip()

def voice_recognizer(language):
    subprocess.run(['ffmpeg', '-i', 'audio.ogg', 'audio.wav', '-y'])
    text = 'Words not recognized.'
    file = sr.AudioFile('audio.wav')
    with file as source:
        try:
            audio = r.record(source)
            text = r.recognize_google(audio, language=language)
            text = add_punctuation_russian(text)
        except:
            logger.error(f"Exception:\n {traceback.format_exc()}")

    return text

def search_movies(query):
    base_url = f'https://api.kinopoisk.dev/v1.4/movie/search?page=1&limit=10&query={query}'
    api_key = '8W83T87-DV244BK-PEE7PXK-6PS64WX'
    headers = {
        'accept': 'application/json',
        'X-API-KEY': api_key
    }
    response = requests.get(base_url, headers=headers)
    movies = []
    # print(response.json())
    if response.status_code == 200:
        movies_data = response.json()
        items = movies_data.get('docs', [])
        # Извлечение nameRu для каждого фильма
        filtered_movies = [{'name': movie.get('name'), 'id': movie.get('id')} for movie in items if (movie.get('type') == 'movie' or movie.get('type') == 'animated-series' or movie.get('type') == 'cartoon' or movie.get('type') == 'tv-series')]

        return filtered_movies
    else:
        print(f"Error: {response.status_code}")
        return []
    
    
    

def send_movies_results(bot, user_id, movies, command, content, isInfinite=False):
    if not movies:
        bot.send_message(user_id, "🔍Ой! Похоже, ничего не найдено по вашему запросу. Пожалуйста, проверьте правильность введенного названия фильма.🤔")
        return

    user = users_collection.find_one({'user_id': user_id})
    user['movies'] = movies
    user['total_pages'] = (len(movies) + 4) // 5
    user['current_page'] = 1
    users_collection.update_one({'user_id': user_id}, {'$set': user})

    send_movies_page(bot, user_id, movies, user['current_page'], user['total_pages'], isInfinite)


def send_movies_page(bot, user_id, movies, current_page, total_pages, isInfinite=False):
    print('send_movies_page function')
    user = users_collection.find_one({'user_id': user_id})
    start_index = (current_page - 1) * 5
    end_index = min(current_page * 5, len(movies))
    page_movies = movies[start_index:end_index]

    buttons = []
    for idx, movie in enumerate(page_movies):
        button_text = movie['name']
        callback_data = f"movie:{movie['id']}"
        buttons.append([types.InlineKeyboardButton(button_text, callback_data=callback_data)])

    navigation_buttons = []
    if current_page == total_pages and total_pages > 1:
        navigation_buttons.append([types.InlineKeyboardButton("◀️ Назад", callback_data="prev_page")])
    if current_page == 1 and total_pages > 1:
        navigation_buttons.append([types.InlineKeyboardButton("Вперед ▶️", callback_data="next_page")])
    if current_page > 1 and current_page < total_pages:
        navigation_buttons.append([types.InlineKeyboardButton("◀️ Назад", callback_data="prev_page"), types.InlineKeyboardButton("Вперед ▶️", callback_data="next_page")])

    inline_keyboard = buttons + navigation_buttons
    keyboard = types.InlineKeyboardMarkup(inline_keyboard)

    message_text = u"\n🕵<b>Вот что нам удалось найти по вашему запросу.</b>"
    if(isInfinite):
        message_text = u"Если вашего фильма нет в списке, проверьте корректность ввода, и мы постараемся найти что-то похожее для вас! Чтобы остановиться, напишите <b>стоп</b> или <b>stop</b>"
    message_text += f"\n\n\n📖<b>Страница {current_page} из {total_pages}</b>"
        

    sent_message = bot.send_message(user_id, message_text, parse_mode='HTML', reply_markup=keyboard)

    if(isInfinite):
        bot.register_next_step_handler(sent_message, find_conent)


def get_movie_details(movie_id):
    base_url = f'https://kinopoiskapiunofficial.tech/api/v2.2/films/{movie_id}'
    api_key = '6ea49ced-083a-4c2a-b622-9137ca531bd6'

    deep_info_url = f'https://api.kinopoisk.dev/v1.4/movie/{movie_id}'
    kino_dev = '8W83T87-DV244BK-PEE7PXK-6PS64WX'

    headers = {
        'accept': 'application/json',
        'X-API-KEY': api_key
    }

    headers_deep = {
        'accept': 'application/json',
        'X-API-KEY': kino_dev
    }

    response = requests.get(base_url, headers=headers)
    response_watch = requests.get(deep_info_url, headers=headers_deep)

    if response.status_code == 200 and response_watch.status_code == 200:
        film = response.json()

        print(film)

        genres = [genre["genre"] for genre in film['genres']]
        filmUrl = film['webUrl']

        # Формирование текста для бота
        message = f"<b>{film['nameRu'] if film['nameRu'] else film['nameOriginal']}</b>\n"
        # message += f"\n<b>📅 Год выпуска:</b> {film['year']} - {film['endYear']}"
        if film['ratingImdb'] and film['ratingImdbVoteCount']: message += f"\n<b>⭐ Оценка:</b> {film['ratingImdb']}[оценили {'{:,.0f}'.format(int(film['ratingImdbVoteCount']))}]"
        message += f"\n<b>📅 Год выпуска:</b> {film['year']}"
        if film.get("serial"):
            if film["completed"] and film['endYear'] != film['year']:
                message += f" - {film['endYear']}"
            if not film["completed"]: 
                message += f" - н.в."
                
        message += f"\n<b>🎭 Жанры:</b> {', '.join(genres)}"
        
        message += f"\n<b>👀 Где посмотреть:</b>"
        # message += f"Кинопоиск: <a href='{film['webUrl']}'>смотреть</a>\n"
        watch = response_watch.json()
        items_watch = watch["watchability"]["items"]
        if len(items_watch) != 0:
            for item in items_watch:
                message += f"\n ∙ {item['name']}: <a href='{item['url']}'>смотреть</a>"
        else:
            if(watch['ticketsOnSale']): 
                message += f"\n<b>⚓⚠️ Данный фильм возможно посмотреть только в кино.⚠️⚓</b>\n"
            else: 
                message += f"\n<b>⚓⚠️ Данный фильм возможно посмотреть только на пиратских киноплощадках.⚠️⚓</b>\n"

        
        

        if(film["serial"]):
            message += f"\n<b>⏳ Статус: "
            if(film["completed"]):
                message += f"все сезоны выпущены в полном объеме, однако сериал в будующем может быть продолджен</b>"
            else:
                message += f"не все сезоны выпущены в полном объеме, уточнить график выхода серий можно в онлайн кинотеатре</b>"

            serial_episode = f'https://api.kinopoisk.dev/v1.4/season?page=1&limit=10&selectFields=episodes&notNullFields=episodesCount&movieId={movie_id}'


            response_episodes = requests.get(serial_episode, headers=headers_deep)
            # if response_episodes.status_code == 200:
            #     episodes = response_episodes.json()
            #     print(episodes)
            #     message += f"\n<b>📖 Количество сезонов:</b> {episodes['total']}"

        else:
            if film['filmLength']: message += f"\n<b>⏳ Продолжительность фильма:</b> {format_duration(film['filmLength'])}"
        
        if film['description']: message += f"\n\n<b>📄 Описание:</b> {film['description'][:120]}..."

        movie_name = film['nameRu'] if film['nameRu'] else film['nameOriginal']

        # Получение URL изображения
        # photo_url = film.get('posterUrl') or film.get('posterUrlPreview')
        photo_url = watch['poster']['previewUrl']
        return message, photo_url, movie_name, genres, filmUrl
    else:
        print(f"Error: {response.status_code}")
        return None
    
@bot.callback_query_handler(func=lambda call: call.data in ["by_rating", "favourite_genre"] or call.data.startswith("collection&") or call.data.startswith("genre_list&") )
def collection_handler(call):
    user_id = call.from_user.id
    user = users_collection.find_one({'user_id': user_id})

    if call.data == "favourite_genre":
        watched_movies = None
        if 'watched' in user:
            watched_movies = user.get('watched', [])
        else: 
            bot.send_message(user_id, "Вы не можете попасть сюда, так как о вас нет информации")
            return

        all_genres = None
        if 'genres' in user:
            all_genres = [genre for movie in watched_movies for genre in movie.get('genres', [])]
        else: 
            bot.send_message(user_id, "Вы не можете попасть сюда, так как о вас нет информации")
            return
        

        genre_counts = {}
        for genre in all_genres:
            genre_counts[genre] = genre_counts.get(genre, 0) + 1

        unique_genres = sorted(set(all_genres), key=lambda x: genre_counts[x], reverse=True)
        first_genre = unique_genres[0]

        genre_to_id = {genre["genre"]: genre["id"] for genre in genres_array}

        selected_genre = first_genre.lower()
        navigation_buttons = []
        
        selected_id = genre_to_id[selected_genre]
        url = 'https://kinopoiskapiunofficial.tech/api/v2.2/films'
        params = {
            'genres': selected_id,
            'order': 'RATING',
            'type': 'ALL',
            'ratingFrom': 0,
            'ratingTo': 10,
            'yearFrom': 1000,
            'yearTo': 3000,
            'page': random.randint(1, 5)
        }
        headers = {
            'accept': 'application/json',
            'X-API-KEY': '6ea49ced-083a-4c2a-b622-9137ca531bd6'
        }
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            
            films = data.get('items', [])
            for index, film in enumerate(films, start=1):
                film_id = film.get('kinopoiskId', '')
                film_name = film.get('nameRu', '')
                film_url = f"https://www.kinopoisk.ru/film/{film_id}/"
                navigation_buttons.append(
                    [
                        types.InlineKeyboardButton(film_name, url=film_url),
                    ]
                )
            
        inline_keyboard = navigation_buttons
        keyboard = types.InlineKeyboardMarkup(inline_keyboard)

        bot.send_message(user_id, f"🍿🎬 Подборка фильмов по вашему самому популярному жанру: <b>{first_genre}</b>.\n\nВсе фильмы отсортированы по убыванию рейтинга на кинопоиске.✨", parse_mode='HTML', reply_markup=keyboard)

    elif call.data == "by_rating":
        watched_movies = None
        if 'watched' in user:
            watched_movies = user.get('watched', [])
        else: 
            bot.send_message(user_id, "Вы не можете попасть сюда, так как о вас нет информации")
            return

        all_genres = None
        if 'genres' in user:
            all_genres = [genre for movie in watched_movies for genre in movie.get('genres', [])]
        else: 
            bot.send_message(user_id, "Вы не можете попасть сюда, так как о вас нет информации")
            return

        genre_counts = {}
        for genre in all_genres:
            genre_counts[genre] = genre_counts.get(genre, 0) + 1

        unique_genres = sorted(set(all_genres), key=lambda x: genre_counts[x], reverse=True)
        first_genre = unique_genres[1]

        genre_to_id = {genre["genre"]: genre["id"] for genre in genres_array}

        selected_genre = first_genre.lower()
        navigation_buttons = []
        
        selected_id = genre_to_id[selected_genre]
        url = 'https://kinopoiskapiunofficial.tech/api/v2.2/films'
        params = {
            'genres': selected_id,
            'order': 'RATING',
            'type': 'ALL',
            'ratingFrom': 0,
            'ratingTo': 10,
            'yearFrom': 1000,
            'yearTo': 3000,
            'page': random.randint(1, 5)
        }
        headers = {
            'accept': 'application/json',
            'X-API-KEY': '6ea49ced-083a-4c2a-b622-9137ca531bd6'
        }
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            
            films = data.get('items', [])
            for index, film in enumerate(films, start=1):
                film_id = film.get('kinopoiskId', '')
                film_name = film.get('nameRu', '')
                film_url = f"https://www.kinopoisk.ru/film/{film_id}/"
                navigation_buttons.append(
                    [
                        types.InlineKeyboardButton(film_name, url=film_url),
                    ]
                )
            
        inline_keyboard = navigation_buttons
        keyboard = types.InlineKeyboardMarkup(inline_keyboard)

        bot.send_message(user_id, f"🍿🎬 Подборка фильмов по вашим отзывам.\n\nВсе фильмы отсортированы по убыванию рейтинга на кинопоиске.✨", parse_mode='HTML', reply_markup=keyboard)
    elif call.data.startswith("collection&"):
        category = call.data.split("&")[1] #new_year, love, brutal

        base_url = f'https://api.kinopoisk.dev/v1.4/movie?page=1&limit=10&lists={category}'
        api_key = '8W83T87-DV244BK-PEE7PXK-6PS64WX'

        headers = {
            'accept': 'application/json',
            'X-API-KEY': api_key
        }

        response = requests.get(base_url, headers=headers)
        movies = []

        print(response.json())

        if response.status_code == 200:
            movies_data = response.json()
            items = movies_data.get('docs', [])

            # Извлечение nameRu для каждого фильма
            filtered_movies = [{'name': movie.get('name'), 'id': movie.get('id')} for movie in items if (movie.get('type') == 'movie' or movie.get('type') == 'animated-series' or movie.get('type') == 'cartoon' or movie.get('type') == 'tv-series')]

            movies = filtered_movies
        else:
            print(f"Error: {response.status_code}")
            movies = []

        send_movies_results(bot, user_id, movies, 'найди', '')
    elif call.data.startswith("genre_list&"):
        genre = call.data.split("&")[1]

        base_url = f'https://api.kinopoisk.dev/v1.4/movie?page=1&limit=10&selectFields=id&selectFields=name&selectFields=type&notNullFields=rating.imdb&type=&genres.name={genre}'
        api_key = '8W83T87-DV244BK-PEE7PXK-6PS64WX'

        headers = {
            'accept': 'application/json',
            'X-API-KEY': api_key
        }

        response = requests.get(base_url, headers=headers)
        movies = []

        if response.status_code == 200:
            movies_data = response.json()
            items = movies_data.get('docs', [])

            # Извлечение nameRu для каждого фильма
            filtered_movies = [{'name': movie.get('name'), 'id': movie.get('id')} for movie in items if (movie.get('type') == 'movie' or movie.get('type') == 'animated-series' or movie.get('type') == 'cartoon' or movie.get('type') == 'tv-series')]

            movies = filtered_movies
        else:
            print(f"Error: {response.status_code}")
            movies = []

        send_movies_results(bot, user_id, movies, 'найди', '')



        
        


@bot.callback_query_handler(func=lambda call: call.data.startswith("movie:") or call.data.startswith("watched:") or call.data.startswith("watch_later:") or call.data.startswith("unwatch_later:") or call.data.startswith("unwatched:") or call.data.startswith("setRating:") or call.data.startswith("editRating:") or call.data.startswith("rating:") or call.data.startswith("find:") or call.data in ["prev_page", "next_page", "return_to_list"])
def movies_callback_handler(call):
    user_id = call.from_user.id
    user = users_collection.find_one({'user_id': user_id})

    if call.data == "prev_page":
        user['current_page'] = max(1, user.get('current_page', 1) - 1)
    elif call.data == "next_page":
        user['current_page'] = min(user.get('total_pages', 1), user.get('current_page', 1) + 1)
    elif call.data.startswith("movie:"):
        movie_id = int(call.data.split(":")[1])
        movie_details, photo_url, movie_name, genres, firmUrl = get_movie_details(movie_id)

        # print(movie_details)

        # Создание кнопок
        markup = types.InlineKeyboardMarkup()
        # Проверяем, добавлен ли фильм в просмотренные
        is_watched = any(movie.get('id') == movie_id for movie in user.get('watched', []))

        if is_watched:
            markup.add(types.InlineKeyboardButton("Удалить из просмотренных", callback_data=f"unwatched:{movie_id}"))
        else:
            markup.add(types.InlineKeyboardButton("Добавить в просмотренное", callback_data=f"watched:{movie_id}"))

        rating_object = next((item for item in user.get('rating', []) if item['id'] == movie_id), None)

        if not rating_object:
            markup.add(types.InlineKeyboardButton("Поставить оценку", callback_data=f"setRating:{movie_id}"))
        else:
            markup.add(types.InlineKeyboardButton("Изменить оценку", callback_data=f"editRating:{movie_id}"))

        later_object = next((item for item in user.get('later', []) if item['id'] == movie_id), None)

        if not later_object:
            markup.add(types.InlineKeyboardButton("Посмотреть позже", callback_data=f"watch_later:{movie_id}"))
        else:
            markup.add(types.InlineKeyboardButton("Убрать из посмотреть позже", callback_data=f"unwatch_later:{movie_id}"))
        markup.add(types.InlineKeyboardButton("Вернуться к списку", callback_data="return_to_list"))


        message = bot.send_photo(user_id, photo_url, caption=movie_details, parse_mode='HTML', reply_markup=markup)
        user['last_message_id'] = message.message_id
    elif call.data.startswith("find:"):
        print('find controller')

        text = call.data.split(":")[1]

        movies = search_movies(text)
        send_movies_results(bot, user_id, movies, 'найди', text)

        return

    elif call.data.startswith("watched:"):
        print('watched')

        # Извлекаем id фильма из callback_data
        watched_movie_id = int(call.data.split(":")[1])

        if True:
            # Проверяем, есть ли этот фильм уже в массиве user['watched']
            if 'watched' not in user:
                user['watched'] = []

            movie_details, photo_url, movie_name, genres, firmUrl = get_movie_details(watched_movie_id)

            # Проверяем, что фильм еще не добавлен в массив user['watched']
            if watched_movie_id not in [movie['id'] for movie in user['watched']]:
                

                print(movie_name)
                
                current_date = datetime.now().strftime("%d.%m.%Y")
                watched_movie = {'name': movie_name, 'id': watched_movie_id}
                watched_movie['date_added'] = current_date
                watched_movie['genres'] = genres

                user['watched'].append(watched_movie)
                users_collection.update_one({'user_id': user_id}, {'$set': user})

                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("Удалить из просмотренных", callback_data=f"unwatched:{watched_movie_id}{':without' if len(call.data.split(':')) > 2 else ''}"))

                if(len(call.data.split(":")) == 2): 
                    rating_object = next((item for item in user.get('rating', []) if item['id'] == watched_movie_id), None)
                    if not rating_object:
                        markup.add(types.InlineKeyboardButton("Поставить оценку", callback_data=f"setRating:{watched_movie_id}"))
                    else:
                        markup.add(types.InlineKeyboardButton("Изменить оценку", callback_data=f"editRating:{watched_movie_id}"))
                
                
                later_object = next((item for item in user.get('later', []) if item['id'] == watched_movie_id), None)

                if not later_object:
                    markup.add(types.InlineKeyboardButton("Посмотреть позже", callback_data=f"watch_later:{watched_movie_id}{':without' if len(call.data.split(':')) > 2 else ''}"))
                else:
                    markup.add(types.InlineKeyboardButton("Убрать из посмотреть позже", callback_data=f"unwatch_later:{watched_movie_id}{':without' if len(call.data.split(':')) > 2 else ''}"))
                
                if(len(call.data.split(":")) == 2): markup.add(types.InlineKeyboardButton("Вернуться к списку", callback_data="return_to_list"))

                bot.edit_message_reply_markup(chat_id=user_id, message_id=user['last_message_id'], reply_markup=markup)

                bot.send_message(user_id, f"Фильм '{watched_movie['name']}' добавлен в просмотренное ({current_date}).")
                
            else:
                bot.send_message(user_id, f"Фильм '{movie_name}' уже находится в просмотренных.")
        else:
            bot.send_message(user_id, "Фильм или сериал возможно вернуть в просмотренные только если запрос на поиск не изменился! 🔄🎬")
    elif call.data.startswith('watch_later:'):
        movie_id = int(call.data.split(":")[1])

        # print(call.data)

        # later_movie = {}
        # later_movie = next((movie for movie in user.get('movies', []) if movie.get('id') == movie_id), None)

        # print(later_movie)

        if True:
            if 'later' not in user:
                user['later'] = []

            movie_details, photo_url, movie_name, genres, firmUrl = get_movie_details(movie_id)

            if movie_id not in [movie['id'] for movie in user['later']]:
                current_date = datetime.now().strftime("%d.%m.%Y")
                later_movie = {'name': movie_name, 'id': movie_id}
                later_movie['date_added'] = current_date
                later_movie['genres'] = genres


                user['later'].append(later_movie)
                users_collection.update_one({'user_id': user_id}, {'$set': user})

                markup = types.InlineKeyboardMarkup()
                is_watched = any(movie.get('id') == movie_id for movie in user.get('watched', []))

                if is_watched:
                    markup.add(types.InlineKeyboardButton("Удалить из просмотренных", callback_data=f"unwatched:{movie_id}{':without' if len(call.data.split(':')) > 2 else ''}"))
                else:
                    markup.add(types.InlineKeyboardButton("Добавить в просмотренное", callback_data=f"watched:{movie_id}{':without' if len(call.data.split(':')) > 2 else ''}"))

                if(len(call.data.split(":")) == 2): 
                    rating_object = next((item for item in user.get('rating', []) if item['id'] == movie_id), None)

                    if not rating_object:
                        markup.add(types.InlineKeyboardButton("Поставить оценку", callback_data=f"setRating:{movie_id}"))
                    else:
                        markup.add(types.InlineKeyboardButton("Изменить оценку", callback_data=f"editRating:{movie_id}"))

                markup.add(types.InlineKeyboardButton("Убрать из посмотреть позже", callback_data=f"unwatch_later:{movie_id}{':without' if len(call.data.split(':')) > 2 else ''}"))
                if(len(call.data.split(":")) == 2):  markup.add(types.InlineKeyboardButton("Вернуться к списку", callback_data="return_to_list"))
                

                bot.edit_message_reply_markup(chat_id=user_id, message_id=user['last_message_id'], reply_markup=markup)

                bot.send_message(user_id, f"Фильм '{later_movie['name']}' добавлен в позже.")
                
            else:
                bot.send_message(user_id, f"Фильм '{later_movie['name']}' уже находится в позже.")

    elif call.data.startswith('unwatch_later:'):
        movie_id = int(call.data.split(":")[1])

        watched_movie = {}

        watched_movie = next((movie for movie in user.get('movies', []) if movie.get('id') == movie_id), None)

        if watched_movie is None:
            watched_movie = next((movie for movie in user.get('later', []) if movie.get('id') == movie_id), None)

        user['later'] = [movie for movie in user.get('later', []) if movie.get('id') != movie_id]
        users_collection.update_one({'user_id': user_id}, {'$set': user})

        markup = types.InlineKeyboardMarkup()
        is_watched = any(movie.get('id') == movie_id for movie in user.get('watched', []))

        if is_watched:
            markup.add(types.InlineKeyboardButton("Удалить из просмотренных", callback_data=f"unwatched:{movie_id}{':without' if len(call.data.split(':')) > 2 else ''}"))
        else:
            markup.add(types.InlineKeyboardButton("Добавить в просмотренное", callback_data=f"watched:{movie_id}{':without' if len(call.data.split(':')) > 2 else ''}"))
        
        if(len(call.data.split(":")) == 2):
            rating_object = next((item for item in user.get('rating', []) if item['id'] == movie_id), None)
            if not rating_object:
                markup.add(types.InlineKeyboardButton("Поставить оценку", callback_data=f"setRating:{movie_id}"))
            else:
                markup.add(types.InlineKeyboardButton("Изменить оценку", callback_data=f"editRating:{movie_id}"))
        markup.add(types.InlineKeyboardButton("Посмотреть позже", callback_data=f"watch_later:{movie_id}{':without' if len(call.data.split(':')) > 2 else ''}"))
        
        if(len(call.data.split(":")) == 2): markup.add(types.InlineKeyboardButton("Вернуться к списку", callback_data="return_to_list"))
                
        bot.edit_message_reply_markup(chat_id=user_id, message_id=user['last_message_id'], reply_markup=markup)


        bot.send_message(user_id, f"Фильм '{watched_movie['name']}' удален из просмотренных.")

    elif call.data.startswith("unwatched:"):
        # Извлекаем id фильма из callback_data
        movie_id = int(call.data.split(":")[1])

        watched_movie = {}

        watched_movie = next((movie for movie in user.get('watched', []) if movie.get('id') == movie_id), None)

        if watched_movie is None:
            watched_movie = next((movie for movie in user.get('watched', []) if movie.get('id') == movie_id), None)

        user['watched'] = [movie for movie in user.get('watched', []) if movie.get('id') != movie_id]
        users_collection.update_one({'user_id': user_id}, {'$set': user})

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Добавить в просмотренное", callback_data=f"watched:{movie_id}{':without' if len(call.data.split(':')) > 2 else ''}"))
        if(len(call.data.split(":")) == 2): 
            rating_object = next((item for item in user.get('rating', []) if item['id'] == movie_id), None)
            if not rating_object:
                markup.add(types.InlineKeyboardButton("Поставить оценку", callback_data=f"setRating:{movie_id}"))
            else:
                markup.add(types.InlineKeyboardButton("Изменить оценку", callback_data=f"editRating:{movie_id}"))
        
        later_object = next((item for item in user.get('later', []) if item['id'] == movie_id), None)

        if not later_object:
            markup.add(types.InlineKeyboardButton("Посмотреть позже", callback_data=f"watch_later:{movie_id}{':without' if len(call.data.split(':')) > 2 else ''}"))
        else:
            markup.add(types.InlineKeyboardButton("Убрать из посмотреть позже", callback_data=f"unwatch_later:{movie_id}{':without' if len(call.data.split(':')) > 2 else ''}"))
        
        if(len(call.data.split(":")) == 2): markup.add(types.InlineKeyboardButton("Вернуться к списку", callback_data="return_to_list"))
                
        bot.edit_message_reply_markup(chat_id=user_id, message_id=user['last_message_id'], reply_markup=markup)


        bot.send_message(user_id, f"Фильм '{watched_movie['name']}' удален из просмотренных.")
    elif call.data.startswith("setRating:"):
        movie_id = call.data.split(":")[1]

        print(movie_id)

        inline_keyboard = [
            [
                types.InlineKeyboardButton("1", callback_data=f"rating:{movie_id}&1&set"),
                types.InlineKeyboardButton("2", callback_data=f"rating:{movie_id}&2&set"),
                types.InlineKeyboardButton("3", callback_data=f"rating:{movie_id}&3&set"),
                types.InlineKeyboardButton("4", callback_data=f"rating:{movie_id}&4&set"),
                types.InlineKeyboardButton("5", callback_data=f"rating:{movie_id}&5&set"),
            ],
            [
                types.InlineKeyboardButton("Отмена", callback_data=f"rating:-1&1&set"),
            ]
        ]
        markup = types.InlineKeyboardMarkup(inline_keyboard)
        rating_message = bot.send_message(user_id, f"Выберете подходящую оценку для данного фильма, результат будет сохранен автоматически.", reply_markup=markup)

        user['rating_message_id'] = rating_message.message_id
    elif call.data.startswith("editRating:"):
        movie_id = int(call.data.split(":")[1])

        rating_object = next((item for item in user.get('rating', []) if item['id'] == movie_id), None)
        
        print(rating_object)

        rating_number = rating_object['value']

        inline_keyboard = [
            [
                types.InlineKeyboardButton(f"✅ 1" if rating_number == 1 else "1", callback_data=f"rating:{movie_id}&1&edit"),
                types.InlineKeyboardButton(f"✅ 2" if rating_number == 2 else "2", callback_data=f"rating:{movie_id}&2&edit"),
                types.InlineKeyboardButton(f"✅ 3" if rating_number == 3 else "3", callback_data=f"rating:{movie_id}&3&edit"),
                types.InlineKeyboardButton(f"✅ 4" if rating_number == 4 else "4", callback_data=f"rating:{movie_id}&4&edit"),
                types.InlineKeyboardButton(f"✅ 5" if rating_number == 5 else "5", callback_data=f"rating:{movie_id}&5&edit"),
            ],
            [
                types.InlineKeyboardButton("Отмена", callback_data=f"rating:-1&1&edit"),
            ]
        ]
        markup = types.InlineKeyboardMarkup(inline_keyboard)
        rating_message = bot.send_message(user_id, f"Выберете подходящую оценку для данного фильма, результат будет сохранен автоматически.", reply_markup=markup)

        user['rating_message_id'] = rating_message.message_id
        # user['last_message_id'] = rating_message.message_id

    elif call.data.startswith("rating:"):
        dataPart = call.data.split(":")[1].split("&")
        movie_id = int(dataPart[0])
        rating_value = int(dataPart[1])
        mode_type = dataPart[2]

        if(movie_id == -1):
            bot.delete_message(chat_id=user_id, message_id=user['rating_message_id'])
            user['rating_message_id'] = ''

            return

        if mode_type == 'set':
            if 'rating' not in user:
                user['rating'] = []

            rating_object = next((item for item in user.get('rating', []) if item['id'] == movie_id), None)

            if not rating_object:
                rating_obj = {}

                rating_obj['id'] = movie_id
                rating_obj['value'] = rating_value

                user['rating'].append(rating_obj)

                bot.delete_message(chat_id=user_id, message_id=user['rating_message_id'])
                bot.send_message(user_id, f"Ваша оценка была сохранена, это повлияется на ваши рекомендации.")


                markup = types.InlineKeyboardMarkup()
                is_watched = any(movie.get('id') == movie_id for movie in user.get('watched', []))

                if is_watched:
                    markup.add(types.InlineKeyboardButton("Удалить из просмотренных", callback_data=f"unwatched:{movie_id}"))
                else:
                    markup.add(types.InlineKeyboardButton("Добавить в просмотренное", callback_data=f"watched:{movie_id}"))

                markup.add(types.InlineKeyboardButton("Изменить оценку", callback_data=f"editRating:{movie_id}"))
                later_object = next((item for item in user.get('later', []) if item['id'] == movie_id), None)

                if not later_object:
                    markup.add(types.InlineKeyboardButton("Посмотреть позже", callback_data=f"watch_later:{movie_id}"))
                else:
                    markup.add(types.InlineKeyboardButton("Убрать из посмотреть позже", callback_data=f"unwatch_later:{movie_id}"))
                markup.add(types.InlineKeyboardButton("Вернуться к списку", callback_data="return_to_list"))
                        
                bot.edit_message_reply_markup(chat_id=user_id, message_id=user['last_message_id'], reply_markup=markup)
            else:
                bot.send_message(user_id, f"У вас уже имеется оценка на данный фильм, обновите карточку контента или посмотрите в 'Просмотренные'")
        else:
            rating_object = next((item for item in user.get('rating', []) if item['id'] == movie_id), None)
            rating_object['value'] = rating_value

            bot.delete_message(chat_id=user_id, message_id=user['rating_message_id'])
            bot.send_message(user_id, f"Ваша оценка была сохранена, это повлияется на ваши рекомендации.")
    
        user['rating_message_id'] = ''
    
    if(call.data == 'return_to_list' and 'isWatched' in user and user['isWatched'] == True):
        bot.delete_message(chat_id=user_id, message_id=user['last_message_id'])
        user['last_message_id'] = ''
        user['isWatched'] = ''
        return

    if (not(call.data.startswith("movie:")) and not(call.data.startswith("watched:")) and not(call.data.startswith("watch_later:")) and not(call.data.startswith("unwatch_later:")) and not(call.data.startswith("unwatched:")) and not(call.data.startswith("setRating:")) and not(call.data.startswith("editRating:")) and not(call.data.startswith("rating:")) and not(call.data.startswith("find:"))):
        send_movies_page(bot, user_id, user['movies'], user['current_page'], user['total_pages'])
        # bot.delete_message(chat_id=user_id, message_id=user['last_message_id'])
        user['last_message_id'] = ''

    users_collection.update_one({'user_id': user_id}, {'$set': user})


if __name__ == '__main__':
    logger.info('start bot')
    bot.polling(True)
    logger.info('stop bot')


