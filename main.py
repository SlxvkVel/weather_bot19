from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import os
from dotenv import load_dotenv
import requests
load_dotenv('tokens.env')
API_TOKEN = os.getenv("token_api")
WEATHER_API_KEY = os.getenv("token_weather")
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
# Создаем базу данных SQLite и таблицу для городов
conn = sqlite3.connect('cities.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS cities (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,city_name TEXT)''')
conn.commit()
# Функция получения погоды
def get_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&lang=ru&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return None
# Функция сохранения города в базу данных
def save_city(user_id, city_name):
    cursor.execute('INSERT INTO cities (user_id, city_name) VALUES (?, ?)', (user_id, city_name))
    conn.commit()
# Функция получения последних введенных городов
def get_last_cities(user_id):
    cursor.execute('SELECT city_name FROM cities WHERE user_id = ? ORDER BY id DESC LIMIT 5', (user_id,))
    return [row[0] for row in cursor.fetchall()]
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.answer("Привет! Введи название города, чтобы получить прогноз погоды.")
@dp.message_handler()
async def get_weather_command(message: types.Message):
    city = message.text
    weather_data = get_weather(city)
    if weather_data is not None:
        main = weather_data['main']
        weather = weather_data['weather'][0]
        response = (
            f"Погода в городе {city}:\n"
            f"Температура: {main['temp']}°C\n"
            f"Состояние: {weather['description']}\n"
        )
        await message.answer(response)
        # Сохраняем город в базу данных
        save_city(message.from_user.id, city)
        # Создаем клавиатуру с кнопками для последних городов и подробного прогноза
        keyboard = InlineKeyboardMarkup()
        button_show_cities = InlineKeyboardButton("Показать последние введенные города",callback_data='show_last_cities')
        button_detailed_forecast = InlineKeyboardButton("Узнать более подробный прогноз",callback_data=f'detailed_forecast_{city}')
        keyboard.add(button_show_cities, button_detailed_forecast)
        await message.answer(
            "Нажмите на кнопку ниже, чтобы увидеть последние введенные города или получить более подробный прогноз:",reply_markup=keyboard)
    else:
        await message.answer("Не удалось получить данные о погоде. Проверьте название города.")
@dp.callback_query_handler(lambda callback_query: callback_query.data == 'show_last_cities')
async def show_last_cities(callback_query: types.CallbackQuery):
    last_cities = get_last_cities(callback_query.from_user.id)
    keyboard = InlineKeyboardMarkup()
    if last_cities:
        for city in set(last_cities):
            keyboard.add(InlineKeyboardButton(city, callback_data=f'weather_{city}'))
        await callback_query.message.answer("Выберите город, прогноз для которого хотите узнать:",reply_markup=keyboard)
    else:
        await callback_query.message.answer("У вас пока нет введенных городов.")
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('weather_'))
async def show_weather(callback_query: types.CallbackQuery):
    city = callback_query.data.split('weather_')[1]
    weather_data = get_weather(city)
    if weather_data is not None:
        main = weather_data['main']
        weather = weather_data['weather'][0]
        response = (
            f"Погода в городе {city}:\n"
            f"Температура: {main['temp']}°C\n"
            f"Состояние: {weather['description']}\n"
            f"Влажность: {main['humidity']}%\n"
        )
        await callback_query.message.answer(response)
    else:
        await callback_query.message.answer("Не удалось получить данные о погоде для этого города.")
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('detailed_forecast_'))
async def show_detailed_forecast(callback_query: types.CallbackQuery):
        city = callback_query.data.split('detailed_forecast_')[1]
        # Получаем более подробные данные о погоде
        detailed_weather_data = get_weather(city)
        if detailed_weather_data is not None:
            main = detailed_weather_data['main']
            weather = detailed_weather_data['weather'][0]
            response = (
                f"Подробный прогноз погоды в городе {city}:\n"
                f"Температура: {main['temp']}°C\n"
                f"Ощущается как: {main['feels_like']}°C\n"
                f"Состояние: {weather['description']}\n"
                f"Влажность: {main['humidity']}%\n"
                f"Давление: {main['pressure']} гПа\n"
                f"Скорость ветра: {detailed_weather_data['wind']['speed']} м/с\n"
                f"Облачность: {detailed_weather_data['clouds']['all']}% \n"
            )
            await callback_query.message.answer(response)
        else:
            await callback_query.message.answer("Не удалось получить данные о погоде для этого города.")
if __name__ == '__main__':
        executor.start_polling(dp)