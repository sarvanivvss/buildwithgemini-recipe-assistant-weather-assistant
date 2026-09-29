# Smart Weather & Lifestyle Assistant

A conversational AI agent built with Google's **Agent Development Kit (ADK)** that helps users plan daily activities and outfits based on real-time weather forecasts, air quality index (AQI), geocoded places, custom generative images and videos, and saved location preferences.

![Smart Weather Agent Demo](./demo.gif)

---

## 🌟 Implemented Capabilities

Every capability listed below is fully implemented and wired up in this repository (`app/` and `frontend/`):

### 1. 🌤️ Weather & Air Quality Real-Time Intelligence
- **Live Forecasts**: Fetches real-time temperature, weather conditions, and wind speed using Open-Meteo (`get_live_weather`).
- **Air Quality Index (AQI)**: Retrieves real-time US AQI scores, PM2.5 densities, and health recommendations (`get_air_quality`).

### 2. 🗺️ Google Maps & Places Integration
- **Geocoding**: Converts place names and street addresses into exact latitude and longitude coordinates via Google Maps Geocoding API (`geocode_address`).
- **Nearby Places Search**: Finds nearby parks, cafes, museums, or attractions around coordinates via Google Places API (New) (`find_nearby_places`).

### 3. 🎨 Generative Image & Video Models
- **Generative Outfit & Scenery Images**: Creates custom weather outfit recommendations and scenery artwork using `gemini-3.1-flash-lite-image` in the `global` region (`generate_weather_lifestyle_image`).
- **Atmospheric Scenery Videos**: Generates short weather scenery videos using Google's Omni model (`gemini-omni-flash-preview`) in the `global` region (`generate_weather_scenery_video`).

### 4. 🗄️ Google Cloud Services & Storage
- **Vertex AI Memory Bank**: Automatically records and remembers queried cities across sessions (`VertexAiMemoryBankService`).
- **Google Cloud Firestore**: Persists favorite locations and user weather preferences in Firestore (`save_favorite_location`, `get_saved_locations`).
- **Google Cloud Storage (GCS)**: Stores generated outfit images and scenery videos in a public Cloud Storage bucket.
- **Agent Engine Code Executor**: Runs safe Python code in a sandboxed Cloud Agent Engine environment (`AgentEngineSandboxCodeExecutor`).

### 5. 🎨 A2UI Rich Card Rendering & Frontend
- **A2UI Protocol (v0.8)**: Generates structured, responsive A2UI cards (Card, Column, Row, Text, Image, Icon) returned via A2A protocol.
- **Chat UI & Proxy**: Minimal FastAPI proxy utilizing `a2a-sdk` with a responsive chat interface and one-tap prompt chips.

---

## 🚀 Local Setup & Running Instructions

### Prerequisites
- Python 3.10+
- [`uv`](https://github.com/astral-sh/uv) package manager
- Google Cloud Project with Vertex AI, Firestore, and Google Maps API enabled
- `GOOGLE_MAPS_API_KEY` environment variable set

### 1. Install Dependencies
```bash
uv sync
```

### 2. Run Agent Playground Locally
Start the ADK playground server to test tools, A2UI cards, and Memory Bank:
```bash
uv run adk web . --port 8080 --reload_agents
```

### 3. Run FastAPI Proxy Frontend Locally
Navigate to the `frontend/` directory and launch the web server:
```bash
cd frontend
pip install -r requirements.txt
uvicorn main:app --port 8080 --reload
```

---

## 📁 Repository Structure

```
.
├── app/
│   ├── agent.py          # Main ADK Agent, tools, Memory Bank, and A2UI callbacks
│   └── a2ui_utils.py     # A2UI response formatting callback handler
├── frontend/
│   ├── main.py           # FastAPI server proxy communicating over A2A protocol
│   ├── static/index.html # Web chat UI with A2UI renderer & prompt chips
│   └── requirements.txt  # Frontend dependencies
├── agents-cli-manifest.yaml # Agent configuration manifest
├── demo.gif              # Demonstration animation of the application
└── README.md             # Project documentation
```
