import asyncio
import logging
import os

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


@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    first_name = message.from_user.first_name
    welcome_msg = (
        f"Привет, {first_name}! \n\n"
        f"🤖 Это бот для быстрой адаптации Перваша в стенах КБТУ. "
        f"Разработанный организацией OSIT.\n\n"
        f"🔍 Здесь вы можете:\n"
        f"- Узнать где вы или же найти нужный кабинет\n"
        f"- Получить ответы на частые вопросы\n"
    )

    await asyncio.sleep(1)
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


@dp.message_handler(lambda message: message.text == "Где Я?🫣")
async def ask_for_room_number(message: types.Message):
    await bot.send_message(message.from_user.id, "Введите номер кабинета рядом с вами.")
    USER_STATES[message.from_user.id] = "waiting_for_room_number"


@dp.message_handler(
    lambda message: USER_STATES.get(message.from_user.id) == "waiting_for_room_number"
)
async def handle_room_number(message: types.Message):
    found = False
    if message.text.isdigit():
        room_number = int(message.text)
        if 100 <= room_number <= 143:
            await bot.send_message(message.from_user.id, "Вы на Панфилова, 1 этаж.")
            map_path = "./map/floor1/PF.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True

        elif 144 <= room_number <= 152:
            await bot.send_message(message.from_user.id, "Вы на Толе Би, 1 этаж.")
            map_path = "./map/floor1/TB.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True

        elif 156 <= room_number <= 183:
            await bot.send_message(message.from_user.id, "Вы на Абылайхана, 1 этаж.")
            map_path = "./map/floor1/Abl.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True
        elif 252 <= room_number <= 284:
            await bot.send_message(message.from_user.id, "Вы на Абылайхана, 2 этаж.")
            map_path = "./map/floor2/ABL.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True
        elif 202 <= room_number <= 245:
            await bot.send_message(message.from_user.id, "Вы на Панфилова, 2 этаж.")
            map_path = "./map/floor2/PF.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True
        elif 246 <= room_number <= 251:
            await bot.send_message(message.from_user.id, "Вы на Толе Би, 2 этаж.")
            map_path = "./map/floor2/TB.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True
        elif 300 <= room_number <= 343:
            await bot.send_message(message.from_user.id, "Вы на Панфилова, 3 этаж.")
            map_path = "./map/floor3/PF.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True
        elif 344 <= room_number <= 360:
            await bot.send_message(message.from_user.id, "Вы на Толе Би, 3 этаж.")
            map_path = "./map/floor3/TB.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True
        elif 361 <= room_number <= 388:
            await bot.send_message(message.from_user.id, "Вы на Абылайхана, 3 этаж.")
            map_path = "./map/floor3/ABL.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True
        elif 501 <= room_number <= 522:
            await bot.send_message(message.from_user.id, "Вы на Толе Би, 5 этаж.")
            map_path = "./map/5floor.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True
        elif 400 <= room_number <= 416:
            await bot.send_message(message.from_user.id, "Вы на Панфилова, 4 этаж.")
            map_path = "./map/floor4/PF.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True
        elif 419 <= room_number <= 438:
            await bot.send_message(message.from_user.id, "Вы на Казыбек Би, 4 этаж.")
            map_path = "./map/floor4/KB.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True
        elif 444 <= room_number <= 461:
            await bot.send_message(message.from_user.id, "Вы на Абылайхана, 4 этаж.")
            map_path = "./map/floor4/ABL.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True
        elif 462 <= room_number <= 476 or 417 <= room_number <= 418:
            await bot.send_message(message.from_user.id, "Вы на Толе Би, 4 этаж.")
            map_path = "./map/floor4/TB.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True

    if message.text.lower() in [
        "халык",
        "халык коворкинг",
        "зеленый коворкинг",
        "halyk co-working",
    ]:
        await bot.send_message(message.from_user.id, "Вы на Казыбек би, 1 этаж.")
        map_path = "./map/floor1/KB.png"
        with open(map_path, "rb") as photo:
            await bot.send_photo(message.from_user.id, photo)
        found = True
    elif message.text.lower() in [
        "геймдев",
        "коворкинг на 2 этаже",
        "game dev",
        "gamedev",
        "726",
    ]:
        await bot.send_message(message.from_user.id, "Вы на Казыбек би, 2 этаже.")
        map_path = "./map/floor2/KB.png"
        with open(map_path, "rb") as photo:
            await bot.send_photo(message.from_user.id, photo)
        found = True
    elif message.text.lower() in [
        "ор",
        "офис регистратора",
        "office registration",
        "or",
    ]:
        await bot.send_message(message.from_user.id, "Вы на Панфилова, 2 этаже.")
        map_path = "./map/floor2/OR.png"
        with open(map_path, "rb") as photo:
            await bot.send_photo(message.from_user.id, photo)
        found = True
    elif message.text.lower() == "столовка":
        await bot.send_message(message.from_user.id, "Столовка находится на 1 этаже.")
        map_path = "./map/floor1/Canteen.png"
        with open(map_path, "rb") as photo:
            await bot.send_photo(message.from_user.id, photo)
        found = True
    elif message.text.lower() in [
        "деканат фит",
        "деканат шитии",
        "dean site",
        "site",
        "шитии",
        "фит",
    ]:
        await bot.send_message(message.from_user.id, "Вы на Абылайхана, 2 этаже.")
        map_path = "./map/floor2/DCSITE.png"
        with open(map_path, "rb") as photo:
            await bot.send_photo(message.from_user.id, photo)
        found = True

    if not found:
        await bot.send_message(
            message.from_user.id,
            "Номер комнаты или название не распознано. Пожалуйста, введите корректный номер или название.",
        )

    # Reset the user state
    USER_STATES[message.from_user.id] = None


@dp.message_handler(lambda message: message.text == "Найти🔍")
async def handle_find_room(message: types.Message):
    await bot.send_message(
        message.from_user.id,
        "Введите номер или название кабинета, который вы хотите найти.\n\nТак же можете написать 'покушать' или 'учиться' и узнать где можно покушать/поучиться",
    )
    USER_STATES[message.from_user.id] = "for_room_number"


@dp.message_handler(
    lambda message: USER_STATES.get(message.from_user.id) == "for_room_number"
)
async def handle_room_number(message: types.Message):
    found = False
    if message.text.isdigit():
        room_number = int(message.text)
        if 100 <= room_number <= 143:
            await bot.send_message(
                message.from_user.id, "Это находиться на Панфилова, 1 этаж."
            )
            map_path = "./map/floor1/PF.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True

        elif 144 <= room_number <= 152:
            await bot.send_message(
                message.from_user.id, "Это находиться на Толе би, 1 этаж."
            )
            map_path = "./map/floor1/TB.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True

        elif 156 <= room_number <= 183:
            await bot.send_message(
                message.from_user.id, "Это находиться на Абылайхана, 1 этаж."
            )
            map_path = "./map/floor1/Abl.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True
        elif 252 <= room_number <= 284:
            await bot.send_message(
                message.from_user.id, "Это находиться на Абылайхана, 2 этаж."
            )
            map_path = "./map/floor2/ABL.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True
        elif 202 <= room_number <= 245:
            await bot.send_message(
                message.from_user.id, "Это находиться на Панфилова, 2 этаж."
            )
            map_path = "./map/floor2/PF.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True
        elif 246 <= room_number <= 251:
            await bot.send_message(
                message.from_user.id, "Это находиться на Толе Би, 2 этаж."
            )
            map_path = "./map/floor2/TB.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True
        elif 501 <= room_number <= 522:
            await bot.send_message(
                message.from_user.id, "Это находиться на Толе Би, 5 этаж."
            )
            map_path = "./map/5floor.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True
        elif 300 <= room_number <= 343:
            await bot.send_message(
                message.from_user.id, "Это находиться на Панфилова, 3 этаж."
            )
            map_path = "./map/floor3/PF.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True
        elif 344 <= room_number <= 360:
            await bot.send_message(
                message.from_user.id, "Это находиться на Толе Би, 3 этаж."
            )
            map_path = "./map/floor3/TB.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True
        elif 361 <= room_number <= 388:
            await bot.send_message(
                message.from_user.id, "Это находиться на Абылайхана, 3 этаж."
            )
            map_path = "./map/floor3/ABL.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True
        elif 400 <= room_number <= 416:
            await bot.send_message(
                message.from_user.id, "Это находиться на Панфилова, 4 этаж."
            )
            map_path = "./map/floor4/PF.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True
        elif 419 <= room_number <= 438:
            await bot.send_message(
                message.from_user.id, "Это находиться на Казыбек Би, 4 этаж."
            )
            map_path = "./map/floor4/KB.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True
        elif 444 <= room_number <= 461:
            await bot.send_message(
                message.from_user.id, "Это находиться на Абылайхана, 4 этаж."
            )
            map_path = "./map/floor4/ABL.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True
        elif 462 <= room_number <= 476 or 417 <= room_number <= 418:
            await bot.send_message(
                message.from_user.id, "Это находиться на Толе Би, 4 этаж."
            )
            map_path = "./map/floor4/TB.png"
            with open(map_path, "rb") as photo:
                await bot.send_photo(message.from_user.id, photo)
            found = True

    if message.text.lower() in [
        "халык",
        "халык коворкинг",
        "зеленый коворкинг",
        "halyk co-working",
    ]:
        await bot.send_message(
            message.from_user.id, "Это находиться на Казыбек би, 1 этаж."
        )
        map_path = "./map/floor1/KB.png"
        with open(map_path, "rb") as photo:
            await bot.send_photo(message.from_user.id, photo)
        found = True
    elif message.text.lower() in [
        "геймдев",
        "коворкинг на 2 этаже",
        "game dev",
        "gamedev",
        "726",
    ]:
        await bot.send_message(
            message.from_user.id, "Это находиться на Казыбек би, 2 этаже."
        )
        map_path = "./map/floor2/KB.png"
        with open(map_path, "rb") as photo:
            await bot.send_photo(message.from_user.id, photo)
        found = True
    elif message.text.lower() == "столовка":
        await bot.send_message(
            message.from_user.id, "Столовка находится на 0 этаже Толе Би ."
        )
        map_path = "./map/floor1/Canteen.png"
        with open(map_path, "rb") as photo:
            await bot.send_photo(message.from_user.id, photo)
        found = True
    elif message.text.lower() == "покушать":
        await bot.send_message(
            message.from_user.id,
            "Столовка находится на 0 этаже Толе Би. Купить перекус на 0, 1, 3 этаже Толе би так же на 1 этаже Абылайхана. Еще рядом с универом есть много заведении где можно покушать.",
        )
        found = True

    elif message.text.lower() == "учиться":
        await bot.send_message(
            message.from_user.id,
            "",
        )
        found = True
    elif message.text.lower() in [
        "ор",
        "офис регистратора",
        "office registration",
        "or",
    ]:
        await bot.send_message(
            message.from_user.id, "Это находиться на Панфилова, 2 этаже."
        )
        map_path = "./map/floor2/OR.png"
        with open(map_path, "rb") as photo:
            await bot.send_photo(message.from_user.id, photo)
        found = True
    elif message.text.lower() in [
        "деканат фит",
        "деканат шитии",
        "dean site",
        "site",
        "шитии",
        "фит",
    ]:
        await bot.send_message(
            message.from_user.id, "Это находиться на Абылайхана, 2 этаже."
        )
        map_path = "./map/floor2/DCSITE.png"
        with open(map_path, "rb") as photo:
            await bot.send_photo(message.from_user.id, photo)
        found = True

    if not found:
        await bot.send_message(
            message.from_user.id,
            "Номер кабинета или название не распознано. Пожалуйста, введите корректный номер или название.",
        )

    # Reset the user state
    USER_STATES[message.from_user.id] = None


@dp.message_handler(lambda message: message.text == "ChatGPT🤖")
async def handle_chatgpt(message: types.Message):
    await bot.send_message(message.from_user.id, "Задайте свой вопрос:")
    USER_STATES[message.from_user.id] = "waiting_for_openai_question"


@dp.message_handler(
    lambda message: USER_STATES.get(message.from_user.id)
    == "waiting_for_openai_question"
)
async def handle_openai_question(message: types.Message):
    response = await ask_openai(message.text)
    await bot.send_message(message.from_user.id, response)
    USER_STATES[message.from_user.id] = None


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
