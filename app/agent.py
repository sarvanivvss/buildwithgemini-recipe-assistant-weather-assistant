# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import datetime
import json
import os
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from google import genai
from google.cloud import firestore, storage
from google.adk.tools import ToolContext, load_memory, preload_memory
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.memory.memory_entry import MemoryEntry

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from .a2ui_utils import a2ui_callback

# Load local .env environment variables
load_dotenv()

# IMPORTANT: Hardcode project ID and bucket name as strings.
# Do NOT use google.auth.default() or GOOGLE_CLOUD_PROJECT env var.
GCP_PROJECT_ID = "qwiklabs-gcp-02-6bcd5cb9c516"
BUCKET_NAME = "smart-weather-assets-qwiklabs-02"
COLLECTION_NAME = "saved_locations"
REASONING_ENGINE_SHORT_ID = "7295487798956523520"

DEPLOYMENT_META_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "deployment_metadata.json"
)


def _get_agent_engine_resource_name() -> str:
    try:
        if os.path.exists(DEPLOYMENT_META_PATH):
            with open(DEPLOYMENT_META_PATH, "r") as f:
                meta = json.load(f)
                engine_id = meta.get("remote_agent_runtime_id")
                if engine_id:
                    return engine_id
    except Exception:
        pass
    return f"projects/{GCP_PROJECT_ID}/locations/us-central1/reasoningEngines/{REASONING_ENGINE_SHORT_ID}"


def _get_firestore_client():
    return firestore.Client(project=GCP_PROJECT_ID)


# Memory Bank Service for future Agent Platform redeployments
memory_service = VertexAiMemoryBankService(
    project=GCP_PROJECT_ID,
    location="us-central1",
    agent_engine_id=REASONING_ENGINE_SHORT_ID,
)


def _record_city_memory(city: str, tool_context: ToolContext = None):
    """Helper to record requested city into Memory Bank."""
    if tool_context and hasattr(tool_context, "add_memory"):
        try:
            entry = MemoryEntry(
                content=types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text=f"User requested city: {city}"
                        )
                    ],
                )
            )
            coro = tool_context.add_memory(memories=[entry])
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(coro)
            except RuntimeError:
                asyncio.run(coro)
        except Exception:
            pass


def remember_requested_city(city: str, tool_context: ToolContext) -> str:
    """Explicitly records and remembers a user requested city in the Memory Bank.

    Args:
        city: The city name to remember (e.g. "Seattle", "Paris", "Tokyo").
        tool_context: ADK ToolContext automatically supplied by framework.

    Returns:
        Confirmation message that the city was recorded in memory.
    """
    _record_city_memory(city, tool_context)
    return f"City '{city}' has been remembered in your Memory Bank."


def generate_weather_lifestyle_image(
    prompt: str, tool_context: ToolContext
) -> str:
    """Generates a visual artwork, outfit recommendation, or weather scenery image based on a prompt using the gemini-3.1-flash-lite-image model in global region.

    Saves the image into Playground Artifacts via tool_context.save_artifact and uploads the bytes directly to a public Cloud Storage bucket.

    Args:
        prompt: Detailed image prompt description (e.g. "A stylish raincoat outfit for a rainy day in Tokyo").
        tool_context: ADK ToolContext automatically supplied by the framework.

    Returns:
        The public HTTPS URL of the uploaded image in Cloud Storage (https://storage.googleapis.com/<bucket>/<object>).
    """
    try:
        client = genai.Client(
            vertexai=True, location="global", project=GCP_PROJECT_ID
        )
        res = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
        )

        image_bytes = None
        mime_type = "image/jpeg"

        if res.candidates and res.candidates[0].content.parts:
            for part in res.candidates[0].content.parts:
                if part.inline_data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    break

        if not image_bytes:
            return "Error: No image content returned by gemini-3.1-flash-lite-image model."

        file_ext = "jpg" if "jpeg" in mime_type else "png"
        filename = f"weather_image_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_ext}"

        # 1. Save artifact for Playground Artifacts panel
        artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload image bytes directly to public GCS bucket
        storage_client = storage.Client(project=GCP_PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
        return public_url
    except Exception as e:
        return f"Error generating or uploading image: {str(e)}"


def generate_weather_scenery_video(
    prompt: str, tool_context: ToolContext
) -> str:
    """Generates a short atmospheric weather scenery or lifestyle video based on a prompt using Google's Omni model (gemini-omni-flash-preview) in the global region.

    Saves the video into Playground Artifacts via tool_context.save_artifact and uploads the video bytes directly to a public Cloud Storage bucket.

    Args:
        prompt: Detailed video prompt description (e.g. "A short video of rain falling on a cozy cafe window in Paris").
        tool_context: ADK ToolContext automatically supplied by the framework.

    Returns:
        The public HTTPS URL of the uploaded video in Cloud Storage (https://storage.googleapis.com/<bucket>/<object>).
    """
    try:
        client = genai.Client(
            vertexai=True, location="global", project=GCP_PROJECT_ID
        )
        res = client.models.generate_content(
            model="gemini-omni-flash-preview",
            contents=prompt,
        )

        video_bytes = None
        mime_type = "video/mp4"

        if res.candidates and res.candidates[0].content.parts:
            for part in res.candidates[0].content.parts:
                if part.inline_data:
                    video_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "video/mp4"
                    break

        if not video_bytes:
            return "Error: No video content returned by gemini-omni-flash-preview model."

        file_ext = "mp4" if "mp4" in mime_type else "webm"
        filename = f"weather_video_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_ext}"

        # 1. Save artifact for Playground Artifacts panel
        artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
        tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload video bytes directly to public GCS bucket
        storage_client = storage.Client(project=GCP_PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
        return public_url
    except Exception as e:
        return f"Error generating or uploading video: {str(e)}"


def geocode_address(address: str, tool_context: ToolContext = None) -> dict:
    """Converts a location or street address into geographic coordinates (latitude and longitude) using Google Maps Geocoding API.

    Args:
        address: The location or address string to geocode (e.g. "San Francisco, CA", "Eiffel Tower").
        tool_context: Optional ADK ToolContext to record memory.

    Returns:
        A dictionary with keys "address", "latitude", and "longitude".
    """
    _record_city_memory(address, tool_context)
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable not set."}

    try:
        encoded_addr = urllib.parse.quote(address)
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_addr}&key={api_key}"
        req = urllib.request.Request(
            url, headers={"User-Agent": "SmartWeatherAgent/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        if data.get("status") == "OK" and data.get("results"):
            result = data["results"][0]
            loc = result["geometry"]["location"]
            return {
                "address": result.get("formatted_address", address),
                "latitude": loc["lat"],
                "longitude": loc["lng"],
            }
        return {"error": f"Geocoding failed for address '{address}'."}
    except Exception as e:
        return {"error": f"Error geocoding address '{address}': {str(e)}"}


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "park",
    radius_meters: float = 5000.0,
) -> list[dict]:
    """Finds nearby places of a given type around coordinates using Google Places API (New).

    Args:
        latitude: Latitude coordinate.
        longitude: Longitude coordinate.
        place_type: Type of place to search for (e.g. "park", "restaurant", "tourist_attraction", "cafe", "museum").
        radius_meters: Search radius in meters (default 5000 meters / ~3 miles).

    Returns:
        A list of dictionaries containing key fields (name, address, location).
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY environment variable not set."}]

    try:
        url = "https://places.googleapis.com/v1/places:searchNearby"
        payload = {
            "includedTypes": [place_type],
            "maxResultCount": 5,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius": radius_meters,
                }
            },
        }
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": (
                "places.displayName,places.formattedAddress,places.location"
            ),
        }
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        places_list = []
        for place in data.get("places", []):
            name = place.get("displayName", {}).get("text", "Unknown")
            addr = place.get("formattedAddress", "")
            loc = place.get("location", {})
            places_list.append(
                {
                    "name": name,
                    "address": addr,
                    "location": {
                        "latitude": loc.get("latitude"),
                        "longitude": loc.get("longitude"),
                    },
                }
            )
        return places_list
    except Exception as e:
        return [{"error": f"Error finding nearby places: {str(e)}"}]


def get_live_weather(city: str, tool_context: ToolContext = None) -> str:
    """Fetches real-time live weather data for any city using the Open-Meteo API. Automatically remembers the city in Memory Bank.

    Args:
        city: Name of the city to look up live weather for (e.g. "San Francisco", "Paris", "Tokyo").
        tool_context: Optional ADK ToolContext to record memory.

    Returns:
        A string summary of live temperature, weather conditions, and wind speed.
    """
    _record_city_memory(city, tool_context)
    try:
        encoded_city = urllib.parse.quote(city)
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_city}&count=1&language=en&format=json"
        req = urllib.request.Request(
            geo_url, headers={"User-Agent": "SmartWeatherAgent/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            geo_data = json.loads(resp.read().decode())

        if not geo_data.get("results"):
            return f"Could not find coordinates for '{city}'."

        location = geo_data["results"][0]
        lat = location["latitude"]
        lon = location["longitude"]
        loc_name = location.get("name", city)
        country = location.get("country", "")

        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&temperature_unit=fahrenheit"
        w_req = urllib.request.Request(
            weather_url, headers={"User-Agent": "SmartWeatherAgent/1.0"}
        )
        with urllib.request.urlopen(w_req, timeout=5) as resp:
            w_data = json.loads(resp.read().decode())

        cw = w_data.get("current_weather", {})
        temp = cw.get("temperature")
        wind = cw.get("windspeed")
        code = cw.get("weathercode", 0)

        if code == 0:
            cond = "Clear sky"
        elif code in (1, 2, 3):
            cond = "Partly cloudy"
        elif code in (45, 48):
            cond = "Foggy"
        elif code in (51, 53, 55, 61, 63, 65, 80, 81, 82):
            cond = "Rainy"
        elif code in (71, 73, 75, 85, 86):
            cond = "Snowy"
        elif code in (95, 96, 99):
            cond = "Thunderstorm"
        else:
            cond = "Overcast"

        location_str = f"{loc_name}, {country}" if country else loc_name
        return f"Live weather for {location_str}: {temp}°F, {cond}, wind speed {wind} mph."
    except Exception as e:
        return f"Error fetching live weather for {city}: {str(e)}"


def get_air_quality(city: str, tool_context: ToolContext = None) -> str:
    """Fetches real-time Air Quality Index (AQI) and PM2.5 pollution levels for any city using the Open-Meteo Air Quality API. Automatically remembers the city in Memory Bank.

    Args:
        city: Name of the city to check air quality for (e.g. "San Francisco", "Paris", "Tokyo").
        tool_context: Optional ADK ToolContext to record memory.

    Returns:
        A string summary of current US Air Quality Index (AQI), PM2.5 density, and health advice.
    """
    _record_city_memory(city, tool_context)
    try:
        encoded_city = urllib.parse.quote(city)
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_city}&count=1&language=en&format=json"
        req = urllib.request.Request(
            geo_url, headers={"User-Agent": "SmartWeatherAgent/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            geo_data = json.loads(resp.read().decode())

        if not geo_data.get("results"):
            return f"Could not find coordinates for '{city}'."

        location = geo_data["results"][0]
        lat = location["latitude"]
        lon = location["longitude"]
        loc_name = location.get("name", city)
        country = location.get("country", "")

        aq_url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=us_aqi,pm2_5"
        aq_req = urllib.request.Request(
            aq_url, headers={"User-Agent": "SmartWeatherAgent/1.0"}
        )
        with urllib.request.urlopen(aq_req, timeout=5) as resp:
            aq_data = json.loads(resp.read().decode())

        current = aq_data.get("current", {})
        us_aqi = current.get("us_aqi")
        pm25 = current.get("pm2_5")

        if us_aqi is None:
            return f"Air quality data unavailable for {city}."

        if us_aqi <= 50:
            category = "Good (ideal for outdoor activities)"
        elif us_aqi <= 100:
            category = "Moderate (acceptable for most people)"
        elif us_aqi <= 150:
            category = "Unhealthy for Sensitive Groups"
        elif us_aqi <= 200:
            category = "Unhealthy"
        else:
            category = "Very Unhealthy / Hazardous"

        location_str = f"{loc_name}, {country}" if country else loc_name
        return f"Live Air Quality for {location_str}: US AQI {us_aqi} - {category}. PM2.5: {pm25} µg/m³."
    except Exception as e:
        return f"Error fetching air quality for {city}: {str(e)}"


def get_current_time(query: str) -> str:
    """Gets current local time for a city.

    Args:
        query: City name to look up time for.

    Returns:
        Current local time string.
    """
    q = query.lower()
    if "sf" in q or "san francisco" in q:
        tz_identifier = "America/Los_Angeles"
    elif "ny" in q or "new york" in q:
        tz_identifier = "America/New_York"
    elif "tokyo" in q:
        tz_identifier = "Asia/Tokyo"
    elif "paris" in q:
        tz_identifier = "Europe/Paris"
    else:
        tz_identifier = "UTC"

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time in {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}."


def get_saved_locations() -> list[dict]:
    """Retrieves saved favorite locations and user weather preferences from Firestore.

    Returns:
        A list of dictionary objects containing saved location details (city, state_country, temperature_pref, activity, notes).
    """
    db = _get_firestore_client()
    docs = db.collection(COLLECTION_NAME).stream()
    locations = []
    for doc in docs:
        data = doc.to_dict()
        locations.append(data)
    return locations


def save_favorite_location(
    city: str,
    temperature_pref: str = "moderate",
    activity: str = "Sightseeing",
    notes: str = "",
    state_country: str = "",
    tool_context: ToolContext = None,
) -> str:
    """Saves or updates a favorite location and weather preference in Firestore, and records it in Memory Bank.

    Args:
        city: City name to save (e.g. "Paris").
        temperature_pref: Preferred weather condition or temperature (e.g. "warm", "mild", "cool").
        activity: Preferred activity for this location (e.g. "Running", "Museums", "Dining").
        notes: Optional extra notes about preferences.
        state_country: Optional state or country specification (e.g. "France").
        tool_context: Optional ADK ToolContext to record memory.

    Returns:
        Confirmation message that the location was saved.
    """
    _record_city_memory(city, tool_context)
    db = _get_firestore_client()
    doc_id = city.lower().replace(" ", "_")
    doc_data = {
        "city": city,
        "state_country": state_country,
        "temperature_pref": temperature_pref,
        "activity": activity,
        "notes": notes,
        "saved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    db.collection(COLLECTION_NAME).document(doc_id).set(doc_data)
    return f"Successfully saved '{city}' to your favorite locations in Firestore!"


agent_engine_id = _get_agent_engine_resource_name()

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are the Smart Weather & Lifestyle Assistant. "
        "You help users check real-time weather forecasts, live air quality index (AQI), geocode addresses, and find nearby parks or attractions using Google Maps & Places APIs. "
        "You automatically remember and record every city requested or inquired by the user into the Memory Bank. "
        "Whenever a user asks about previously queried or requested cities, call load_memory or check preload_memory to recall all user requested cities. "
        "You can also generate custom weather outfit images or short atmospheric scenery videos using Google's image and omni models, run python code safely in an Agent Engine Sandbox executor for weather/lifestyle calculations, and manage favorite locations in Firestore."
    ),
    workflow_description="Analyze the user request and return structured UI cards when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property (\'h1\', \'h2\', \'body\') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    after_model_callback=a2ui_callback,
    code_executor=AgentEngineSandboxCodeExecutor(
        agent_engine_resource_name=agent_engine_id
    ),
    tools=[
        load_memory,
        preload_memory,
        remember_requested_city,
        generate_weather_lifestyle_image,
        generate_weather_scenery_video,
        geocode_address,
        find_nearby_places,
        get_live_weather,
        get_air_quality,
        get_current_time,
        get_saved_locations,
        save_favorite_location,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
