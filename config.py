"""
Central configuration for the AI Receptionist.
Edit these values to match your clinic and machine setup.
"""

# ---- Ollama (local LLM) settings ----
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"          # any small/fast local model works, e.g. "phi3.5", "mistral"

# ---- Whisper (speech-to-text) settings ----
WHISPER_MODEL_SIZE = "base.en"     # "tiny.en" = fastest, "small.en"/"base.en" = more accurate
WHISPER_DEVICE = "cpu"             # "cuda" if you have an NVIDIA GPU set up
WHISPER_COMPUTE_TYPE = "int8"      # fast + low memory on CPU

# ---- Audio recording settings ----
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 500            # lower = more sensitive to quiet speech
SILENCE_DURATION = 1.5             # seconds of silence that ends a recording
MAX_RECORD_SECONDS = 20

# ---- Text-to-speech settings ----
TTS_RATE = 175                     # words per minute
TTS_VOLUME = 1.0

# ---- Clinic / scheduling settings ----
CLINIC_NAME = "Sunrise Family Clinic"
CALENDAR_ID = "primary"            # use "primary" for your main Google Calendar, or a specific calendar's ID
APPOINTMENT_LENGTH_MINUTES = 30
BUSINESS_START_HOUR = 9            # 9 AM
BUSINESS_END_HOUR = 17             # 5 PM
DAYS_TO_SEARCH_AHEAD = 7           # how many days forward to look for open slots
NUM_SLOTS_TO_OFFER = 3             # how many open slots to read out to the patient
TIMEZONE = "America/New_York"      # change to your clinic's timezone, e.g. "Asia/Kolkata"

# ---- Google Calendar auth files ----
GOOGLE_CREDENTIALS_FILE = "credentials.json"   # downloaded from Google Cloud Console
GOOGLE_TOKEN_FILE = "token.json"               # auto-created after first login
