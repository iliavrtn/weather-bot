"""
WeatherBot Telegram Bot

This script implements a Telegram bot to provide weather information to users based on their chosen city.

Author: iliaVrtn
Date: 12.10.2023
"""

import logging
from datetime import time
import pytz
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, Update, Bot
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
import db_module
from get_weather_module import process_information, weather_by_coord, parse_weather
from config import *

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
# Set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Define conversation states
CHOOSING, TYPING_REPLY, UPDATE_TYPING_REPLY, DAILY_WEATHER = range(4)

# List to store daily weather information
daily_weather_info = {}

# Keyboard layout for the main menu
main_menu_keyboard = [
    ["Update my city", "Cancel updates", "My city weather"],
    ["Choose city"],
    ["Done"],
]

main_menu_markup = ReplyKeyboardMarkup(main_menu_keyboard, one_time_keyboard=True, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Start command handler. Displays initial message with options.

    Parameters:
    - update (Update): The incoming Telegram update
    - context (ContextTypes.DEFAULT_TYPE): The context object for the conversation

    Returns:
    int: The next conversation state
    """
    # Greet the user and provide information about their current city if available
    reply_text = "Hi! I'm here to provide you weather information about your city! "
    user_id = update.message.from_user.id
    user_data = (int(user_id),)
    result = db_module.execute_query(f"SELECT city FROM telegram_users.users WHERE user_id= %s", user_data)
    if result:
        reply_text += f"Your current city is {result[0][0]} 😃"
    else:
        reply_text += f"You can choose *Update my city* to get daily weather information at 7:00 ⌚"
    
    # Send the initial message with options
    await update.message.reply_text(reply_text, reply_markup=main_menu_markup, parse_mode=ParseMode.MARKDOWN)
    return CHOOSING


async def update_my_city_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Prompt user to enter the city for daily weather updates.

    Parameters:
    - update (Update): The incoming Telegram update
    - context (ContextTypes.DEFAULT_TYPE): The context object for the conversation

    Returns:
    int: The next conversation state
    """
    reply_text = "Enter the city for which you want to receive daily weather updates 💌"
    await update.message.reply_text(reply_text, reply_markup=ReplyKeyboardRemove())
    return UPDATE_TYPING_REPLY


async def update_city_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handler for updating the user's city based on the provided input.

    Parameters:
    - update (Update): The incoming Telegram update
    - context (ContextTypes.DEFAULT_TYPE): The context object for the conversation

    Returns:
    int: The next conversation state
    """
    await search_city(update, context)
    return UPDATE_TYPING_REPLY


async def other_city_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handler for searching and displaying the available cities based on user input.

    Parameters:
    - update (Update): The incoming Telegram update
    - context (ContextTypes.DEFAULT_TYPE): The context object for the conversation

    Returns:
    int: The next conversation state
    """
    await search_city(update, context)
    return TYPING_REPLY


async def search_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Searches for the entered city and displays available options for selection.

    Parameters:
    - update (Update): The incoming Telegram update
    - context (ContextTypes.DEFAULT_TYPE): The context object for the conversation

    Returns:
    int: The next conversation state
    """
    city = update.message.text.capitalize()
    geo_data = process_information(city)
    if "err" in geo_data:
        await update.message.reply_text(text=geo_data["err_msg"], reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    if len(geo_data) == 0:
        reply_text = f"I didn't find such a city 😔 Check if you typed it correctly and try again."
        await update.message.reply_text(reply_text, reply_markup=ReplyKeyboardRemove())
    else:
        keyboard = list_of_cities(geo_data, city)
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Which city is yours?\n", reply_markup=reply_markup)
    return TYPING_REPLY


async def other_city_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Prompt user to enter the city for weather information.

    Parameters:
    - update (Update): The incoming Telegram update
    - context (ContextTypes.DEFAULT_TYPE): The context object for the conversation

    Returns:
    int: The next conversation state
    """
    reply_text = "Enter city that you want to get weather information about 🌇"
    await update.message.reply_text(reply_text, reply_markup=ReplyKeyboardRemove())
    return TYPING_REPLY


async def my_city_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handler for displaying weather information for the user's saved city.

    Parameters:
    - update (Update): The incoming Telegram update
    - context (ContextTypes.DEFAULT_TYPE): The context object for the conversation

    Returns:
    int: The next conversation state
    """
    user_id = update.message.from_user.id
    user_data = (int(user_id),)
    data = db_module.execute_query(f'SELECT lat,lon,city FROM telegram_users.users WHERE user_id= %s', user_data)
    if data:
        lat, lon = data[0][0], data[0][1]
        city = data[0][2]
        geo_data = weather_by_coord(lat, lon)
        if 'err' in geo_data:
            await update.message.reply_text(text=geo_data['err_msg'], reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        daily_weather_info[user_id] = ["", "", "", "", ""]
        for i in range(5):
            daily_weather_info[user_id][i] = parse_weather(geo_data, city, i)
        inline_keyboard = [
            [InlineKeyboardButton("Today, " + geo_data['list'][0]['dt_txt'][:10], callback_data="0"),
             InlineKeyboardButton("Tomorrow, " + geo_data['list'][1 * 8]['dt_txt'][:10], callback_data="1")
             ],
            [InlineKeyboardButton(geo_data['list'][2 * 8]['dt_txt'][:10], callback_data="2"),
             InlineKeyboardButton(geo_data['list'][3 * 8]['dt_txt'][:10], callback_data="3")
             ],
            [InlineKeyboardButton(geo_data['list'][4 * 8]['dt_txt'][:10], callback_data="4")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard)
        await update.message.reply_text(
            text="Choose a day you want to get weather information 📆",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return DAILY_WEATHER
    await update.message.reply_text(
        text="You have not chosen the city yet, choose *Update my city* to do it 😸",
        reply_markup=main_menu_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    return CHOOSING


def list_of_cities(geo_data: list, city: str) -> list:
    """
    Generates a list of cities for display in inline keyboard.

    Parameters:
    - geo_data (list): List of geographic data for cities
    - city (str): The user's selected city

    Returns:
    list: List of keyboard options
    """
    country_arr = [list([item['state'], item['country']]) if 'state' in item else list(["", item['country']])
                   for item in geo_data]
    keyboard = []
    cities=[]
    for i in range(len(country_arr)):
        city_name = ", ".join([city, country_arr[i][0], country_arr[i][1]])
        if city_name not in cities:
            cities.append(city_name)
            if city_name.find(", , ") > 0:  # some cities does not have states 
                city_name = city_name.replace(", ", "", 1)
            callback_data = city_name + ':' + ','.join([str(geo_data[i]['lon']), str(geo_data[i]['lat'])])
            keyboard.append([InlineKeyboardButton(city_name, callback_data=callback_data)])
    return keyboard


async def choose_city_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for selecting a city from the displayed options.

    Parameters:
    - update (Update): The incoming Telegram update
    - context (ContextTypes.DEFAULT_TYPE): The context object for the conversation
    """
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    index = query.data.find(':')
    city = query.data[:index]
    lon_index = query.data.find(',', index)
    lon = query.data[index + 1:lon_index]
    lat = query.data[lon_index + 1:]
    geo_data = weather_by_coord(lat, lon)
    if 'err' in geo_data:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=geo_data['err_msg'],
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    daily_weather_info[user_id] = ["", "", "", "", ""]
    for i in range(5):
        daily_weather_info[user_id][i] = parse_weather(geo_data, city, i)
    inline_keyboard = [
        [InlineKeyboardButton("Today, " + geo_data['list'][0]['dt_txt'][:10], callback_data="0"),
         InlineKeyboardButton("Tomorrow, " + geo_data['list'][1 * 8]['dt_txt'][:10], callback_data="1")
         ],
        [InlineKeyboardButton(geo_data['list'][2 * 8]['dt_txt'][:10], callback_data="2"),
         InlineKeyboardButton(geo_data['list'][3 * 8]['dt_txt'][:10], callback_data="3")
         ],
        [InlineKeyboardButton(geo_data['list'][4 * 8]['dt_txt'][:10], callback_data="4")]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard)
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Choose a day you want to get weather information 📆",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    return DAILY_WEATHER

async def save_my_city_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Callback handler for saving the user's city button.

    Parameters:
    - update (Update): The incoming Telegram update
    - context (ContextTypes.DEFAULT_TYPE): The context object for the conversation

    Returns:
    None
    """
    query = update.callback_query
    await query.answer()

    # Extracting information from the callback data
    index = query.data.find(':')
    lon_index = query.data.find(',', index)
    user_id = query.from_user.id
    new_lat = query.data[lon_index + 1:]
    new_lon = query.data[index + 1:lon_index]
    my_city = query.data[:index]

    user_data = (int(user_id),)
    result = db_module.execute_query(f"SELECT user_id FROM telegram_users.users WHERE user_id= %s", user_data)

    # Update or insert user's city information in the database
    if result:
        user_data = (new_lat, new_lon, my_city, int(user_id))
        db_module.execute_query(f"UPDATE telegram_users.users SET lat= %s, lon= %s, city= %s WHERE user_id= %s", user_data)
    else:
        user_data = (int(user_id), new_lat, new_lon, my_city)
        db_module.execute_query(f"INSERT INTO telegram_users.users VALUES (%s, %s, %s, %s)", user_data)

    # Confirmation messages
    reply_text = f"Your city has been changed to {my_city}!😃"
    await context.bot.send_message(chat_id=query.message.chat_id, text=reply_text, reply_markup=ReplyKeyboardRemove())
    await context.bot.send_message(chat_id=query.message.chat_id, text="Is there anything else I can help with? 😇", reply_markup=main_menu_markup)
    return CHOOSING


async def daily_weather(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Callback handler for daily weather updates.

    Parameters:
    - update (Update): The incoming Telegram update
    - context (ContextTypes.DEFAULT_TYPE): The context object for the conversation

    Returns:
    None
    """
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    text = ""

    # Matching query data to display corresponding weather information
    match query.data:
        case "0":
            text += daily_weather_info[user_id][0]
        case "1":
            text += daily_weather_info[user_id][1]
        case "2":
            text += daily_weather_info[user_id][2]
        case "3":
            text += daily_weather_info[user_id][3]
        case "4":
            text += daily_weather_info[user_id][4]
    # Sending weather information to the user
    await context.bot.send_message(chat_id=query.message.chat_id, text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=ReplyKeyboardRemove())
    await context.bot.send_message(chat_id=query.message.chat_id, text="Is there anything else I can help with? 😇", reply_markup=main_menu_markup)
    return CHOOSING


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handler for unknown commands.

    Parameters:
    - update (Update): The incoming Telegram update
    - context (ContextTypes.DEFAULT_TYPE): The context object for the conversation

    Returns:
    int: The next conversation state
    """
    await update.message.reply_text("Unknown command. Please choose the options below 👇", reply_markup=main_menu_markup)
    return CHOOSING

async def outside_conv_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for messages outside the conversation.

    Parameters:
    - update (Update): The incoming Telegram update
    - context (ContextTypes.DEFAULT_TYPE): The context object for the conversation

    Returns:
    None
    """
    await update.message.reply_text("Type /start to start the conversation 🏃")


async def start_in_conv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for starting a conversation when already in a conversation.

    Parameters:
    - update (Update): The incoming Telegram update
    - context (ContextTypes.DEFAULT_TYPE): The context object for the conversation

    Returns:
    None
    """
    await update.message.reply_text("You are already in conversation, choose the options below 👇", reply_markup=main_menu_markup)
    return CHOOSING


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for ending the conversation.

    Parameters:
    - update (Update): The incoming Telegram update
    - context (ContextTypes.DEFAULT_TYPE): The context object for the conversation

    Returns:
    None
    """
    await update.message.reply_text("See you next time! 👋", reply_markup=ReplyKeyboardRemove())
    try:
        del daily_weather_info[update.message.from_user.id]
    except:
        print("Key Not Present!")
    return ConversationHandler.END

async def timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for timeout the conversation.

    Parameters:
    - update (Update): The incoming Telegram update
    - context (ContextTypes.DEFAULT_TYPE): The context object for the conversation

    Returns:
    None
    """
    await context.bot.send_message(chat_id=update.message.from_user.id, text="See you next time! 👋", reply_markup=ReplyKeyboardRemove())
    try:
        del daily_weather_info[update.message.from_user.id]
    except:
        print("Key Not Present!")
    


async def send_daily_updates(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Function to send daily weather updates to subscribed users.

    Parameters:
    - context (ContextTypes.DEFAULT_TYPE): The context object for the conversation

    Returns:
    None
    """
    users = db_module.get_users_with_daily_updates()

    if users:
        for user in users:
            geo_data = weather_by_coord(user[1], user[2])
            city = user[3] + '\n\n'
            message = parse_weather(geo_data, city, 0)
            await context.bot.send_message(chat_id=user[0], text=message, parse_mode=ParseMode.MARKDOWN)


async def cancel_daily_updates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handler for canceling daily weather updates subscription.

    Parameters:
    - update (Update): The incoming Telegram update
    - context (ContextTypes.DEFAULT_TYPE): The context object for the conversation

    Returns:
    int: The next conversation state
    """
    user_id = update.message.from_user.id
    user_data = (int(user_id),)
    result = db_module.execute_query(f"SELECT user_id FROM telegram_users.users WHERE user_id= %s", user_data)

    if result:
        db_module.execute_query(f"DELETE FROM telegram_users.users WHERE user_id= %s", user_data)
        await update.message.reply_text(text="You unsubscribed successfully!", reply_markup=main_menu_markup)
    else:
        await update.message.reply_text("You are not subscribed to daily updates yet 😞. Choose *Update my city* to get daily updates.", parse_mode=ParseMode.MARKDOWN)

    return CHOOSING


async def help_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handler for providing help information to the user.

    Parameters:
    - update (Update): The incoming Telegram update
    - context (ContextTypes.DEFAULT_TYPE): The context object for the conversation

    Returns:
    int: The next conversation state
    """
    reply_text = """
    *Update my city*: Set your city to get updates ☀️\n
    *Cancel updates*: Temporarily pause weather notifications 🌤 \n
    *My city weather*: Receive instant weather details for your saved city 🌦 \n
    *Choose city*: Explore and select a new location ⛈ \n
    *Done*: End conversation, or type /start at any time to return to the main menu 🌈 \n
    */help*: Access a quick guide to commands and usage ❄️ \n
    */start*: Begin your weather journey with Weather Bot 💦"""
    await update.message.reply_text(text=reply_text, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_markup)
    return CHOOSING


def main() -> None:

    application = Application.builder().token(BOT_TOKEN).build()

    outside_conversation_message = MessageHandler(filters.TEXT | filters.COMMAND, outside_conv_message)
    unknown_message = MessageHandler(filters.TEXT, unknown)
    unknown_command = MessageHandler(filters.COMMAND, unknown)
    done_message = MessageHandler(filters.Regex("^Done$"), done)
    start_command = MessageHandler(filters.Regex("^/start$"), start_in_conv)
    help_command = CommandHandler("help", help_user)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [
                help_command,
                MessageHandler(filters.Regex("^Update my city$"), update_my_city_choice),
                MessageHandler(filters.Regex("^Cancel updates$"), cancel_daily_updates),
                MessageHandler(filters.Regex("^My city weather$"), my_city_choice),
                MessageHandler(filters.Regex("Choose city$"), other_city_choice),
                start_command,
                done_message,
                unknown_message,
                unknown_command
            ],

            TYPING_REPLY: [
                help_command,
                CallbackQueryHandler(choose_city_button),
                MessageHandler(filters.Regex("^[A-Za-z\s\-\'\.]+$"), other_city_handler),
                start_command,
                done_message,
                unknown_message,
                unknown_command
            ],
            UPDATE_TYPING_REPLY: [
                help_command,
                CallbackQueryHandler(save_my_city_button),
                MessageHandler(filters.Regex("^[A-Za-z\s\-\'\.]+$"), update_city_handler),
                start_command
            ],
            DAILY_WEATHER: [
                help_command,
                CallbackQueryHandler(daily_weather),
                start_command,
                done_message,
                unknown_message,
                unknown_command
            ],
            ConversationHandler.TIMEOUT: [MessageHandler(filters.TEXT | filters.COMMAND, timeout)],
        },
        conversation_timeout=120,
        fallbacks=[done]
    )

    application.add_handler(conv_handler)
    application.add_handler(outside_conversation_message)
    application.add_handler(help_command)
    application.job_queue.run_daily(send_daily_updates, time=time(hour=7, minute=00, tzinfo=pytz.timezone('Asia/Tel_Aviv')))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
