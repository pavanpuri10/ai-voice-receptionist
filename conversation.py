"""
Conversation flow for the AI receptionist.

The flow itself is a plain state machine (reliable, predictable) -- the LLM's
job at each step is only to pull structured information out of what the
patient said (name, reason, which slot they picked), and to phrase the
question/confirmation for step naturally when needed.
"""

from tts import speak
from stt import listen
from llm import extract_json
import google_calendar as cal
from config import CLINIC_NAME


def ask_and_listen(prompt: str) -> str:
    speak(prompt)
    return listen()


def extract_name(spoken_text: str) -> str:
    system = (
        "You extract a person's name from what they said when asked for their name. "
        'Return JSON like {"name": "Jane Smith"}. '
        'If no clear name is present, return {"name": null}.'
    )
    result = extract_json(system, spoken_text)
    return result.get("name")


def extract_reason(spoken_text: str) -> str:
    system = (
        "You extract the medical reason for a clinic visit from what the patient said. "
        'Return JSON like {"reason": "annual checkup"}. '
        "Keep it short (a few words). "
        'If unclear, return {"reason": null}.'
    )
    result = extract_json(system, spoken_text)
    return result.get("reason")


def extract_slot_choice(spoken_text: str, num_options: int) -> int:
    """Returns a 1-based index into the offered slots, or None if unclear."""
    system = (
        f"The patient was offered {num_options} appointment time options, numbered 1 to {num_options}. "
        "Figure out which option number they chose from what they said "
        "(they might say 'the first one', 'option two', an actual time, etc). "
        'Return JSON like {"choice": 2}. If unclear, return {"choice": null}.'
    )
    result = extract_json(system, spoken_text)
    return result.get("choice")


def run_call():
    """Runs one full simulated phone call from greeting to confirmation."""
    speak(f"Thank you for calling {CLINIC_NAME}. May I have your name, please?")

    # ---- Step 1: get patient name ----
    name = None
    while not name:
        heard = listen()
        name = extract_name(heard)
        if not name:
            speak("Sorry, I didn't catch your name. Could you say it again?")

    # ---- Step 2: get reason for visit ----
    reason = None
    while not reason:
        heard = ask_and_listen(f"Thanks, {name}. What's the reason for your visit today?")
        reason = extract_reason(heard)
        if not reason:
            speak("Sorry, could you tell me a bit more about the reason for your visit?")

    # ---- Step 3: check availability ----
    speak("Let me check our available appointment times, one moment.")
    slots = cal.get_available_slots()

    if not slots:
        speak("I'm sorry, we don't have any open appointments in the next few days. "
              "Please call back later or try our online booking page.")
        return

    slot_descriptions = [cal.format_slot(s) for s in slots]
    options_text = "; ".join(f"option {i+1}: {desc}" for i, desc in enumerate(slot_descriptions))
    speak(f"Here are our next available appointments: {options_text}. Which works best for you?")

    # ---- Step 4: get slot choice ----
    choice_index = None
    while choice_index is None:
        heard = listen()
        choice_index = extract_slot_choice(heard, len(slots))
        if choice_index is None or not (1 <= choice_index <= len(slots)):
            speak(f"Sorry, could you repeat which option you'd like, 1 through {len(slots)}?")
            choice_index = None

    chosen_slot = slots[choice_index - 1]

    # ---- Step 5: book and confirm ----
    speak("Great, booking that appointment now.")
    try:
        cal.book_appointment(chosen_slot, name, reason)
        speak(
            f"You're all set, {name}. Your appointment is booked for "
            f"{cal.format_slot(chosen_slot)} for {reason}. "
            "We look forward to seeing you. Goodbye!"
        )
    except Exception as e:
        speak("I'm sorry, something went wrong while booking your appointment. "
              "Please call back or try again in a moment.")
        print(f"[error] booking failed: {e}")


if __name__ == "__main__":
    run_call()
