# AI Doctor's Clinic Receptionist (Free, Local)

A voice AI that answers a simulated call, asks for the patient's name and
reason for visit, checks your Google Calendar for open slots, books the
appointment, and confirms it out loud.

**Cost: $0.** Everything (speech-to-text, the AI brain, text-to-speech) runs
on your own machine. Only the calendar uses a Google account (free tier).

> Note: this runs on your computer's microphone/speakers, simulating a call.
> Actually receiving real phone calls requires a telecom provider (e.g. Twilio)
> since connecting to the public phone network isn't something any free
> software alone can do. This project gets the entire AI brain built and
> tested for free -- wiring it to a real phone line is a separate, later step.

---

## 1. Install Ollama (the free local AI brain)

Ollama runs open-source language models on your own computer, no API key, no cost.

**Mac / Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:** download the installer from https://ollama.com/download

Then pull a small, fast model:
```bash
ollama pull llama3.2
```

Ollama runs a local server automatically on `http://localhost:11434`. You can
test it with:
```bash
ollama run llama3.2 "Say hello"
```

---

## 2. Install Python dependencies

Requires Python 3.9+.

```bash
cd ai-receptionist
python3 -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Linux users:** `pyttsx3` needs `espeak`:
```bash
sudo apt-get install espeak
```
**Mac users:** `pyttsx3` uses the built-in `say` voice, no extra install needed.

`sounddevice` needs `PortAudio`:
- Mac: `brew install portaudio`
- Linux: `sudo apt-get install portaudio19-dev`
- Windows: works out of the box

---

## 3. Set up Google Calendar (free)

1. Go to https://console.cloud.google.com/ and create a new project (any name).
2. In "APIs & Services" → "Library", search for **Google Calendar API** and enable it.
3. In "APIs & Services" → "Credentials", click **Create Credentials → OAuth client ID**.
   - If prompted, configure the OAuth consent screen first (choose "External", fill in
     just the required fields, you can leave it in "Testing" mode -- add your own
     Google account under "Test users").
   - For the OAuth client type, choose **Desktop app**.
4. Download the resulting JSON file, rename it to `credentials.json`, and place it in
   this project folder (same folder as `main.py`).
5. The first time you run the app, a browser tab will open asking you to log in
   and approve calendar access. After that, a `token.json` is saved so you won't
   need to log in again.

By default the app uses your **primary** Google Calendar (`CALENDAR_ID = "primary"`
in `config.py`). You can change this to a dedicated clinic calendar's ID if you'd
rather keep it separate -- just share/create that calendar in your Google account
and put its ID in `config.py`.

---

## 4. Configure your clinic details

Open `config.py` and adjust as needed:
- `CLINIC_NAME` -- what the AI says when it answers
- `BUSINESS_START_HOUR` / `BUSINESS_END_HOUR` -- working hours
- `APPOINTMENT_LENGTH_MINUTES` -- slot length
- `TIMEZONE` -- your clinic's timezone (e.g. `"Asia/Kolkata"`, `"America/New_York"`)
- `WHISPER_MODEL_SIZE` -- `"tiny.en"` for speed, `"small.en"` for more accuracy

---

## 5. Run it

```bash
python main.py
```

The AI will:
1. Greet you and ask your name
2. Ask why you're visiting
3. Look up real open slots on your Google Calendar
4. Read out the next available options
5. Book your chosen slot as a calendar event
6. Confirm the booking out loud

Speak naturally when prompted; the app listens until you pause, then processes
what you said. Press `Ctrl+C` at any time to end the call.

---

## Project structure

```
ai-receptionist/
├── main.py              # local mic/speaker version, run this to test
├── conversation.py       # call flow / state machine (local version)
├── app.py                # Flask app for REAL phone calls via Twilio
├── stt.py               # speech-to-text (faster-whisper, local version only)
├── tts.py               # text-to-speech (pyttsx3, local version only)
├── llm.py               # talks to local Ollama model (used by both versions)
├── google_calendar.py   # checks slots + books appointments (used by both)
├── config.py            # all settings live here
├── requirements.txt
└── credentials.json      # you add this (from Google Cloud Console)
```

---

## 6. Connect it to a real phone number (Twilio)

This part is the only piece that isn't free -- Twilio charges a small monthly
fee for the phone number plus a per-minute rate for calls, but a free trial
covers a good amount of testing. Everything else (the AI logic, calendar
booking) is unchanged and still free.

### 6.1 Create a Twilio account and number
1. Sign up at https://www.twilio.com/try-twilio (free trial credit included).
2. In the Console, get a phone number: **Phone Numbers → Manage → Buy a number**
   (a trial number is included free).
3. Note your **Account SID** and **Auth Token** from the Console dashboard
   (not required by `app.py` itself, but useful if you extend it later).

### 6.2 Expose your local app to the internet
Twilio needs a public URL to send call events to. The easiest way while
testing locally is [ngrok](https://ngrok.com/):
```bash
# one-time setup
ngrok config add-authtoken YOUR_NGROK_TOKEN   # free account needed

# every time you test
ngrok http 5000
```
This prints a public URL like `https://abcd1234.ngrok-free.app` — copy it.

### 6.3 Point Twilio at your app
1. In the Twilio Console, open your phone number's settings.
2. Under **Voice Configuration → A call comes in**, choose **Webhook**,
   paste `https://abcd1234.ngrok-free.app/voice`, method **HTTP POST**.
3. Save.

### 6.4 Run the app and call it
```bash
python app.py
```
Leave `ngrok` running in another terminal, then simply **call your Twilio
number from any phone**. The AI will answer, ask your name, ask the reason
for the visit, read out real open slots from your Google Calendar, book the
one you choose, and confirm out loud — over a real phone call.

### Notes on this version
- Speech-to-text and text-to-speech are handled by Twilio itself during the
  call (`<Gather input="speech">` and `<Say>`), which is more reliable over a
  phone line than local mic/speaker software — and it's included in Twilio's
  per-minute cost, so you don't need Whisper or pyttsx3 for this path.
- Call state (name, reason, offered slots) is kept in memory keyed by
  Twilio's Call SID. That's fine for one server process; if you ever deploy
  with multiple worker processes, swap the `call_state` dict for Redis or a
  small database table.
- For a permanent setup (not just testing), deploy `app.py` to a small always-on
  host (Render, Railway, Fly.io, or a cheap VPS all work) instead of ngrok, and
  point the Twilio webhook at that permanent URL.

---

## Upgrading later (still free or low-cost options)

- **More natural voice:** swap `pyttsx3` for [Piper TTS](https://github.com/rhasspy/piper)
  (also free, much better voice quality, still fully offline).
- **Better understanding:** try a larger Ollama model like `mistral` or `llama3.1:8b`
  if your machine has the RAM/CPU/GPU for it.
- **Real phone calls:** connect this logic to a phone number using Twilio's
  Programmable Voice (has a free trial credit, then pay-per-minute). The `conversation.py`
  logic can be reused almost as-is -- you'd swap `stt.py`/`tts.py` for Twilio's
  media streams instead of your local mic/speakers.

---

## Troubleshooting

- **"Could not reach Ollama"** → make sure Ollama is installed and running
  (`ollama serve` in a separate terminal, or check it's running in your system tray).
- **No audio detected / mic not working** → check your OS's microphone permissions
  for the terminal/Python, and confirm the correct input device is default.
- **Google Calendar auth errors** → delete `token.json` and run `main.py` again to
  re-authenticate; double check `credentials.json` is in the project folder.
- **Whisper is slow** → set `WHISPER_MODEL_SIZE = "tiny.en"` in `config.py`.
