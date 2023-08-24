import asyncio
import logging
import os


import aiocron
import openai
import pymongo
from aiogram import Bot, Dispatcher, types
from aiogram.types import InputMediaPhoto, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils import executor
from dotenv import load_dotenv

load_dotenv()


MONGO_URI = os.getenv("MONGO_URI")
# Configure logging
logging.basicConfig(level=logging.INFO)
openai.api_key = os.getenv("OPENAI_API_KEY")

client = pymongo.MongoClient(MONGO_URI)
db = client["Feedbacks"]  # замените на название вашей базы данных
feedback_collection = db["feedback"]

db1 = client["telegram_bot_db"]  # Выберите базу данных
users_collection = db1["users"]

API_TOKEN = os.getenv("API_TOKEN")
# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Define the keyboard layout
main_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
main_keyboard.row("Карта🗺️", "РУП ШИТиИ📚")
main_keyboard.row("Где Я?🫣", "Найти🔍", "ChatGPT🤖")
main_keyboard.add("Жалобы/Предложения📥")
# Global dictionary to store user states
USER_STATES = {}


def add_user(user_id):
    user = {"_id": user_id}
    try:
        users_collection.insert_one(user)
    except:
        # Если пользователь уже существует, игнорируем ошибку
        pass


# Функция для получения всех пользователей
def get_all_users():
    return [user["_id"] for user in users_collection.find({}, {"_id": 1})]


def send_main_keyboard(user_id, message="Выберите опцию:"):
    return bot.send_message(user_id, message, reply_markup=main_keyboard)


def save_feedback(user_id, text):
    feedback_document = {
        "user_id": user_id,
        "text": text,
    }
    feedback_collection.insert_one(feedback_document)


async def ask_openai(question):
    # Using the gpt-3-turbo model for chat-based interaction
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question},
        ],
        max_tokens=800,
    )

    return response.choices[0].message["content"].strip()


@aiocron.crontab("0 9 * * *")  # Это означает каждый день в 23:02
async def send_daily_quote():
    # Вам нужно получить список всех пользователей из вашей базы данных
    users = get_all_users()

    # Генерируем мотивационную цитату с помощью OpenAI
    prompt = "Сначала пожелай доброго утро от лица бота GUIDeon. Потом напиши мотивационную цитат на 100 символов"
    response = await ask_openai(prompt)

    for user_id in users:
        await bot.send_message(user_id, response)


@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    add_user(message.from_user.id)
    first_name = message.from_user.first_name
    welcome_msg = (
        f"Привет, {first_name}! \n\n"
        f"🤖 Это бот для быстрой адаптации Перваша в стенах КБТУ. "
        f"Разработанный организацией OSIT.\n\n"
        f"🔍 Здесь вы можете:\n"
        f"- Узнать где вы или же найти нужный кабинет\n"
        f"- Рабочий учебный план ШИТиИ\n"
        f"- Юзать ChatGPT в телеграме!\n"
        f"- Оставить жалобу/предложения Деканату или OSIT\n"
    )

    await bot.send_message(
        message.from_user.id, welcome_msg, reply_markup=main_keyboard
    )


@dp.message_handler(lambda message: message.text == "Карта🗺️")
async def handle_button1(message: types.Message):
    maps_paths = [
        "./map/1-floor_kbtu.jpg",
        "./map/2-floor_kbtu.jpg",
        "./map/3-floor_kbtu.jpg",
        "./map/4-floor_kbtu.jpg",
        "./map/5-floor_kbtu.jpg",
    ]
    media = [InputMediaPhoto(open(map_path, "rb")) for map_path in maps_paths]

    await bot.send_media_group(message.from_user.id, media)

    # Close the files after sending
    for item in media:
        item.media.close()


@dp.message_handler(lambda message: message.text == "Жалобы/Предложения📥")
async def handle_feedback(message: types.Message):
    await bot.send_message(
        message.from_user.id,
        "Здесь вы можете анонимно написать жалобу, предложение или же сказать спасибо не только OSIT а так же Деканату ШИТиИ. Все письма будут проверяться и читаться. Удачи!",
    )
    USER_STATES[message.from_user.id] = "feedback"


@dp.message_handler(lambda message: USER_STATES.get(message.from_user.id) == "feedback")
async def feedback(message: types.Message):
    save_feedback(message.from_user.id, message.text)
    await bot.send_message(message.from_user.id, "Спасибо за ваше сообщение!")
    USER_STATES[message.from_user.id] = None


@dp.message_handler(lambda message: message.text == "РУП ШИТиИ📚")
async def handle_button1(message: types.Message):
    # Define a new keyboard layout for the RUP options
    rup_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    rup_keyboard.row("ВТИПО", "ИС")
    rup_keyboard.row("АИУ", "РИМ", "IT management")
    rup_keyboard.add("Назад")

    # Send a message to the user with the new keyboard layout
    await bot.send_message(
        message.from_user.id, "Выберите нужный вам РУП:", reply_markup=rup_keyboard
    )


# Handlers for RUP options
@dp.message_handler(
    lambda message: message.text in ["ВТИПО", "ИС", "АИУ", "РИМ", "IT management"]
)
async def handle_rup_options(message: types.Message):
    # Handle the specific RUP option
    # For example:
    if message.text == "ВТИПО":
        path = "./rup_fit/VTIPO.pdf"
    elif message.text == "ИС":
        path = "./rup_fit/IS.pdf"
    elif message.text == "РИМ":
        path = "./rup_fit/RIM.pdf"
    elif message.text == "АИУ":
        path = "./rup_fit/AU.pdf"
    elif message.text == "IT management":
        path = "./rup_fit/it_man.pdf"
    with open(path, "rb") as file:
        await bot.send_document(message.from_user.id, file)

    # Return to the main keyboard after handling the RUP option
    await send_main_keyboard(message.from_user.id)


@dp.message_handler(lambda message: message.text == "Назад")
async def handle_back_button(message: types.Message):
    # Return to the main keyboard
    await send_main_keyboard(message.from_user.id)



chatgpt_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
chatgpt_keyboard.row("Назад")


@dp.message_handler(lambda message: message.text == "ChatGPT🤖")
async def handle_chatgpt(message: types.Message):
    await bot.send_message(
        message.from_user.id, "Задайте свой вопрос:", reply_markup=chatgpt_keyboard
    )
    USER_STATES[message.from_user.id] = "waiting_for_openai_question"


@dp.message_handler(
    lambda message: USER_STATES.get(message.from_user.id)
    == "waiting_for_openai_question"
)
async def handle_openai_question(message: types.Message):
    await bot.send_message(
        message.from_user.id,
        "Ваш запрос принят. Прошу ожидайте это займет какое-то время",
    )
    response = await ask_openai(message.text)
    await bot.send_message(message.from_user.id, response)


@dp.message_handler(
    lambda message: message.text == "Назад"
    and USER_STATES.get(message.from_user.id) == "waiting_for_openai_question"
)
async def handle_back_from_chatgpt(message: types.Message):
    await bot.send_message(
        message.from_user.id,
        "Вы вернулись назад.",
        reply_markup=main_keyboard,  # 'keyboard' это ваша основная клавиатура
    )
    USER_STATES[message.from_user.id] = None


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
