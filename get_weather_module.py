import requests
from datetime import datetime
from config import *

def _check_response(endpoint: str) -> dict:
    """
    Check the response from the API endpoint and handle errors.

    Parameters:
    - endpoint (str): The API endpoint to check

    Returns:
    - geo_data (dict): The data from the API response
    """
    geo_data = {"err": False, "err_msg": -1}
    try:
        response = requests.get(endpoint)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        geo_data["err"] = True
        geo_data["err_msg"] = "Your internet connection is bad, try again later."
    except requests.exceptions.HTTPError:
        geo_data["err"] = True
        geo_data["err_msg"] = "There is something wrong with the server, please try again later."
    geo_data = response.json()
    return geo_data

def process_information(city: str) -> dict:
    """
    Process location information for a given city.

    Parameters:
    - city (str): The name of the city

    Returns:
    - geo_data (dict): The location information
    """
    geo_endpoint = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=5&appid={API_KEY}"
    geo_data = _check_response(geo_endpoint)
    return geo_data

def weather_by_coord(lat: str, lon: str) -> str:
    """
    Get weather information based on coordinates.

    Parameters:
    - lat (str): The latitude of the location
    - lon (str): The longitude of the location

    Returns:
    - geo_data (str): The weather information
    """
    geo_endpoint = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}"
    geo_data = _check_response(geo_endpoint)
    return geo_data

def parse_weather(geo_data: dict, n_of_day: int) -> str:
    """
    Parse weather information and format it as a message.

    Parameters:
    - geo_data (dict): The weather information
    - n_of_day (int): The day for which to retrieve information (0 for current day)

    Returns:
    - message (str): The formatted weather information
    """
    geo_data = geo_data['list']
    first_day_idx = 0
    while geo_data[first_day_idx]['dt_txt'][11:13] != '21':
        first_day_idx += 1
    first_day_idx += 1
    
    start_idx = first_day_idx + (n_of_day - 1) * 8 if n_of_day != 0 else 0
    end_idx = start_idx + 8 if n_of_day != 0 else first_day_idx
    weather_dict = geo_data[start_idx:end_idx]
    message = f"\n\t\t\t\t🌐 *Weather Information* 🌐\t\t\t\t\n\n"
    for weather_data in weather_dict:
        dt = datetime.utcfromtimestamp(weather_data['dt']).strftime('%Y-%m-%d %H:%M:%S')
        temp = "{:.2f}".format(weather_data['main']['temp'] - 273.15)
        feels_like = "{:.2f}".format(weather_data['main']['feels_like'] - 273.15)
        description = weather_data['weather'][0]['description']
        wind_speed = weather_data['wind']['speed']
        humidity = weather_data['main']['humidity']
        # Format the message using Markdown
        message += (
            f"_\t\t\t\t📅\t\t{dt}\t\t📅\t\t\t\t\n\n_"
            f"*🌡️  Temperature:* {temp}°C\n"
            f"*💓  Feels Like:* {feels_like}°C\n"
            f"*📰  Description:* {description}\n"
            f"*🌬️  Wind Speed:* {wind_speed} m/s\n"
            f"*💦  Humidity:* {humidity}%\n\n"
        )
    return message
