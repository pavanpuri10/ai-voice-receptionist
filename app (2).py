import os
import time
import tempfile
import traceback
import requests
from dotenv import load_dotenv
from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse
from faster_whisper import WhisperModel

load_dotenv()

app = Flask(__name__)

TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]

# Load once at startup — "base" is a good speed/accuracy balance to start with
print("[startup] Loading Whisper model, this can take a while on first run...")
whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
print("[startup] Whisper model loaded. Ready for calls.")


@app.route("/voice", methods=["POST"])
def voice():
    try:
        response = VoiceResponse()
        response.say("Hello, thanks for calling. How can I help you today?", voice="Polly.Joanna")
        response.record(
            action="/process_recording",
            method="POST",
            max_length=10,
            play_beep=True,
            trim="trim-silence",
        )
        return str(response), 200, {"Content-Type": "text/xml"}
    except Exception:
        # Always print the real error to the terminal so it's never hidden.
        traceback.print_exc()
        response = VoiceResponse()
        response.say("Sorry, something went wrong on our end. Goodbye.")
        response.hangup()
        return str(response), 200, {"Content-Type": "text/xml"}


@app.route("/process_recording", methods=["POST"])
def process_recording():
    try:
        recording_url = request.form.get("RecordingUrl")

        if not recording_url:
            # Nothing was recorded (e.g. caller stayed silent and it got trimmed to 0).
            response = VoiceResponse()
            response.say("I didn't catch anything. Let's try again.", voice="Polly.Joanna")
            response.record(
                action="/process_recording",
                method="POST",
                max_length=10,
                play_beep=True,
                trim="trim-silence",
            )
            return str(response), 200, {"Content-Type": "text/xml"}

        # The recording can take a moment to finish encoding on Twilio's side
        # even after the action callback fires. Retry briefly if the file
        # isn't ready yet instead of failing immediately.
        audio_resp = None
        for attempt in range(3):
            audio_resp = requests.get(
                recording_url + ".wav",
                auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            )
            if audio_resp.status_code == 200 and len(audio_resp.content) > 0:
                break
            time.sleep(1)

        if audio_resp is None or audio_resp.status_code != 200:
            raise RuntimeError(
                f"Could not download recording (status "
                f"{audio_resp.status_code if audio_resp else 'no response'})"
            )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_resp.content)
            audio_path = f.name

        try:
            segments, _ = whisper_model.transcribe(audio_path)
            caller_text = " ".join(seg.text for seg in segments).strip()
        finally:
            os.remove(audio_path)

        print(f"[caller said]: {caller_text}")

        reply_text = f"I heard you say: {caller_text}. Let me help with that."

        response = VoiceResponse()
        response.say(reply_text, voice="Polly.Joanna")
        response.record(
            action="/process_recording",
            method="POST",
            max_length=10,
            play_beep=True,
            trim="trim-silence",
        )
        return str(response), 200, {"Content-Type": "text/xml"}

    except Exception:
        # This is the key fix: NEVER let an exception fall through to Flask's
        # default 500 page, because Twilio can't parse that and just plays
        # "an application error has occurred." Always return valid TwiML,
        # and print the real traceback here so we can see what broke.
        traceback.print_exc()
        response = VoiceResponse()
        response.say("Sorry, I had trouble processing that. Let's try once more.", voice="Polly.Joanna")
        response.record(
            action="/process_recording",
            method="POST",
            max_length=10,
            play_beep=True,
            trim="trim-silence",
        )
        return str(response), 200, {"Content-Type": "text/xml"}


if __name__ == "__main__":
    app.run(port=5000, debug=True)
