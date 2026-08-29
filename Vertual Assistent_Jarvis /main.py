"""
Jarvis - A simple voice-controlled desktop assistant.

Listens for the wake word "Jarvis", then executes a spoken command:
opening websites, playing music, telling jokes, and reporting the weather.
"""

import time
import subprocess
import webbrowser

import requests
import speech_recognition as sr

import musicLibrary


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

WAKE_WORD = "jarvis"

DEFAULT_CITY = "Dhaka"

WAKE_WORD_TIMEOUT = 5          # seconds to wait for the wake word
WAKE_WORD_PHRASE_LIMIT = 3     # max seconds for the wake word itself
AMBIENT_NOISE_DURATION = 0.5   # seconds spent calibrating for background noise
POST_SPEECH_PAUSE = 0.6        # seconds to wait after speaking, to avoid
                                # the microphone picking up Jarvis's own voice

GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
JOKE_API_URL = "https://v2.jokeapi.dev/joke/Any"

SITES = {
    "open google": "https://google.com",
    "open youtube": "https://youtube.com",
    "open facebook": "https://facebook.com",
    "open linkedin": "https://linkedin.com",
    "open github": "https://github.com/afifIG",
}

recognizer = sr.Recognizer()


# --------------------------------------------------------------------------
# Speech output
# --------------------------------------------------------------------------

def speak(text: str) -> None:
    """Print and speak a line of text aloud, then briefly pause.

    The pause prevents the microphone from picking up Jarvis's own
    voice as the next spoken command.
    """
    print("Jarvis:", text)
    subprocess.run(["say", text])
    time.sleep(POST_SPEECH_PAUSE)


def notify(text: str) -> None:
    """Print a message without speaking it aloud (for minor/expected errors)."""
    print(f"Jarvis: {text}")


# --------------------------------------------------------------------------
# External services
# --------------------------------------------------------------------------

def get_weather(city: str) -> str:
    """Return a short spoken weather summary for the given city."""
    geo_params = {
        "name": city,
        "count": 1,
        "language": "en",
        "format": "json",
    }

    try:
        geo_response = requests.get(GEOCODING_API_URL, params=geo_params, timeout=10)
        geo_data = geo_response.json()
    except requests.RequestException:
        return "Sorry, I couldn't reach the weather service right now."

    results = geo_data.get("results")
    if not results:
        return f"I could not find {city}."

    latitude = results[0]["latitude"]
    longitude = results[0]["longitude"]

    weather_params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
    }

    try:
        weather_response = requests.get(WEATHER_API_URL, params=weather_params, timeout=10)
        current = weather_response.json()["current"]
    except (requests.RequestException, KeyError):
        return "Sorry, I couldn't fetch the weather right now."

    return (
        f"The temperature in {city} is {current['temperature_2m']} degrees Celsius. "
        f"Humidity is {current['relative_humidity_2m']} percent. "
        f"Wind speed is {current['wind_speed_10m']} kilometers per hour."
    )


def get_joke() -> str:
    """Return a random joke as a single string."""
    try:
        response = requests.get(JOKE_API_URL, timeout=10)
        data = response.json()
    except requests.RequestException:
        return "I couldn't think of a joke right now."

    if data.get("type") == "single":
        return data["joke"]

    return f"{data['setup']} {data['delivery']}"


# --------------------------------------------------------------------------
# Command handlers
# --------------------------------------------------------------------------

def handle_play(command: str) -> None:
    words = command.split(" ")
    song = words[1] if len(words) >= 2 else None

    if song not in musicLibrary.music:
        notify("Sorry, I don't have that song.")
        return

    webbrowser.open(musicLibrary.music[song])


def handle_joke() -> None:
    speak("Oh, I've got a good one for you!")
    speak(get_joke())
    speak("Haha! I hope you liked it.")


def process_command(command: str) -> None:
    """Route a spoken command to the appropriate handler."""
    command = command.lower()

    for phrase, url in SITES.items():
        if phrase in command:
            webbrowser.open(url)
            return

    if command.startswith("play"):
        handle_play(command)
    elif "weather" in command:
        speak(get_weather(DEFAULT_CITY))
    elif "joke" in command:
        handle_joke()
    else:
        notify("Sorry, I don't understand that command.")


# --------------------------------------------------------------------------
# Voice input
# --------------------------------------------------------------------------

def listen(timeout=None, phrase_time_limit=None) -> str:
    """Record audio from the microphone and transcribe it to text.

    Raises the same exceptions as speech_recognition (WaitTimeoutError,
    UnknownValueError) on failure - callers are expected to handle them.
    """
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=AMBIENT_NOISE_DURATION)
        audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)

    return recognizer.recognize_google(audio)


def run() -> None:
    """Main loop: wait for the wake word, then listen for and run a command."""
    speak("Initializing Jarvis.")

    while True:
        try:
            print("Listening...")
            heard = listen(
                timeout=WAKE_WORD_TIMEOUT,
                phrase_time_limit=WAKE_WORD_PHRASE_LIMIT,
            )
            print("You:", heard)

            if heard.lower() != WAKE_WORD:
                continue

            speak("Yes?")

            print("Jarvis Active... Speak your command.")
            command = listen()
            print("Command:", command)

            process_command(command)

        except sr.WaitTimeoutError:
            print("No speech detected.")

        except sr.UnknownValueError:
            print("Could not understand.")

        except KeyboardInterrupt:
            print("\nShutting down Jarvis.")
            break

        except Exception as error:  # noqa: BLE001 - top-level safety net
            print("Error:", error)


if __name__ == "__main__":
    run()