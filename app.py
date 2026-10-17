"""
Twilio webhook app -- this is what lets a REAL phone call reach your AI.

How it fits together:
  Caller dials your Twilio number
    -> Twilio calls this app's /voice endpoint (HTTP webhook)
    -> This app replies with TwiML (<Say> to speak, <Gather> to listen)
    -> Twilio does the actual speech-to-text and text-to-speech for the call
       (built into Twilio Voice, included in the per-minute cost)
    -> This app uses the SAME llm.py + google_calendar.py logic from the
       local version to understand the caller and book the appointment.

Run with:
    python app.py
Then expose it publicly (e.g. with ngrok) and point your Twilio number's
"A call comes in" webhook at https://<your-ngrok-url>/voice
See README.md for the full step-by-step setup.
"""

from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Gather

from llm import extract_json
import google_calendar as cal
from config import CLINIC_NAME

app = Flask(__name__)

# In-memory state per call. Fine for a single-process deployment;
# for multiple workers/instances, swap this for Redis or a database.
call_state = {}


def get_state(call_sid):
    if call_sid not in call_state:
        call_state[call_sid] = {}
    return call_state[call_sid]


def extract_name(spoken_text):
    system = (
        "You extract a person's name from what they said when asked for their name. "
        'Return JSON like {"name": "Jane Smith"}. '
        'If no clear name is present, return {"name": null}.'
    )
    return extract_json(system, spoken_text).get("name")


def extract_reason(spoken_text):
    system = (
        "You extract the medical reason for a clinic visit from what the patient said. "
        'Return JSON like {"reason": "annual checkup"}. Keep it short. '
        'If unclear, return {"reason": null}.'
    )
    return extract_json(system, spoken_text).get("reason")


def extract_slot_choice(spoken_text, num_options):
    system = (
        f"The patient was offered {num_options} appointment time options, numbered 1 to {num_options}. "
        "Figure out which option number they chose from what they said "
        "(they might say 'the first one', 'option two', an actual time, etc). "
        'Return JSON like {"choice": 2}. If unclear, return {"choice": null}.'
    )
    return extract_json(system, spoken_text).get("choice")


def gather_response(say_text, action_url):
    """Build a TwiML response that speaks `say_text` then listens for speech."""
    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action=action_url,
        method="POST",
        speech_timeout="auto",
        language="en-US",
    )
    gather.say(say_text)
    response.append(gather)
    # If the caller doesn't say anything, Twilio moves past the <Gather> to here.
    response.say("I didn't catch that. Let's try again.")
    response.redirect(request.url)
    return str(response)


@app.route("/voice", methods=["POST"])
def voice():
    """First webhook Twilio hits when a call comes in."""
    call_sid = request.form.get("CallSid")
    call_state[call_sid] = {}
    twiml = gather_response(
        f"Thank you for calling {CLINIC_NAME}. May I have your name, please?",
        "/handle_name",
    )
    return twiml, 200, {"Content-Type": "text/xml"}


@app.route("/handle_name", methods=["POST"])
def handle_name():
    call_sid = request.form.get("CallSid")
    speech_result = request.form.get("SpeechResult", "")
    state = get_state(call_sid)

    name = extract_name(speech_result)
    if not name:
        twiml = gather_response(
            "Sorry, I didn't catch your name. Could you say it again?",
            "/handle_name",
        )
        return twiml, 200, {"Content-Type": "text/xml"}

    state["name"] = name
    twiml = gather_response(
        f"Thanks, {name}. What's the reason for your visit today?",
        "/handle_reason",
    )
    return twiml, 200, {"Content-Type": "text/xml"}


@app.route("/handle_reason", methods=["POST"])
def handle_reason():
    call_sid = request.form.get("CallSid")
    speech_result = request.form.get("SpeechResult", "")
    state = get_state(call_sid)

    reason = extract_reason(speech_result)
    if not reason:
        twiml = gather_response(
            "Sorry, could you tell me a bit more about the reason for your visit?",
            "/handle_reason",
        )
        return twiml, 200, {"Content-Type": "text/xml"}

    state["reason"] = reason

    slots = cal.get_available_slots()
    if not slots:
        response = VoiceResponse()
        response.say(
            "I'm sorry, we don't have any open appointments in the next few days. "
            "Please call back later. Goodbye."
        )
        response.hangup()
        return str(response), 200, {"Content-Type": "text/xml"}

    state["slots"] = [s.isoformat() for s in slots]
    slot_descriptions = [cal.format_slot(s) for s in slots]
    options_text = "; ".join(f"option {i+1}: {desc}" for i, desc in enumerate(slot_descriptions))

    twiml = gather_response(
        f"Here are our next available appointments: {options_text}. Which works best for you?",
        "/handle_slot",
    )
    return twiml, 200, {"Content-Type": "text/xml"}


@app.route("/handle_slot", methods=["POST"])
def handle_slot():
    import datetime

    call_sid = request.form.get("CallSid")
    speech_result = request.form.get("SpeechResult", "")
    state = get_state(call_sid)

    slots_iso = state.get("slots", [])
    slots = [datetime.datetime.fromisoformat(s) for s in slots_iso]

    choice_index = extract_slot_choice(speech_result, len(slots))
    if choice_index is None or not (1 <= choice_index <= len(slots)):
        twiml = gather_response(
            f"Sorry, could you repeat which option you'd like, 1 through {len(slots)}?",
            "/handle_slot",
        )
        return twiml, 200, {"Content-Type": "text/xml"}

    chosen_slot = slots[choice_index - 1]
    name = state.get("name", "the patient")
    reason = state.get("reason", "a visit")

    response = VoiceResponse()
    try:
        cal.book_appointment(chosen_slot, name, reason)
        response.say(
            f"You're all set, {name}. Your appointment is booked for "
            f"{cal.format_slot(chosen_slot)} for {reason}. "
            "We look forward to seeing you. Goodbye!"
        )
    except Exception as e:
        print(f"[error] booking failed: {e}")
        response.say(
            "I'm sorry, something went wrong while booking your appointment. "
            "Please call back or try again in a moment. Goodbye."
        )
    response.hangup()

    call_state.pop(call_sid, None)
    return str(response), 200, {"Content-Type": "text/xml"}


if __name__ == "__main__":
    app.run(port=5000, debug=True)
