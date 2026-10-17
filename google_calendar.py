"""
Google Calendar integration (free tier, personal account is fine).

One-time setup required (see README.md):
  1. Create a Google Cloud project and enable the "Google Calendar API".
  2. Create an OAuth Client ID (type: Desktop app) and download it as
     credentials.json into this project folder.
  3. The first time you run the app, a browser window will open asking you
     to log in and grant calendar access. This creates token.json, which is
     reused automatically after that (no login needed again).
"""

import datetime
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import (
    CALENDAR_ID,
    APPOINTMENT_LENGTH_MINUTES,
    BUSINESS_START_HOUR,
    BUSINESS_END_HOUR,
    DAYS_TO_SEARCH_AHEAD,
    NUM_SLOTS_TO_OFFER,
    TIMEZONE,
    GOOGLE_CREDENTIALS_FILE,
    GOOGLE_TOKEN_FILE,
)

SCOPES = ["https://www.googleapis.com/auth/calendar"]

_service = None


def _get_service():
    """Authenticate (using cached token if available) and return a Calendar API client."""
    global _service
    if _service is not None:
        return _service

    creds = None
    try:
        creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_FILE, SCOPES)
    except FileNotFoundError:
        creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(GOOGLE_TOKEN_FILE, "w") as token_file:
            token_file.write(creds.to_json())

    _service = build("calendar", "v3", credentials=creds)
    return _service


def _business_hours_slots(days_ahead: int):
    """Generate every possible appointment slot in business hours for the next N days."""
    tz = ZoneInfo(TIMEZONE)
    now = datetime.datetime.now(tz)
    slots = []
    for day_offset in range(days_ahead):
        day = now + datetime.timedelta(days=day_offset)
        # Skip weekends (Saturday=5, Sunday=6)
        if day.weekday() >= 5:
            continue
        day_start = day.replace(hour=BUSINESS_START_HOUR, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=BUSINESS_END_HOUR, minute=0, second=0, microsecond=0)
        slot_start = max(day_start, now) if day_offset == 0 else day_start
        while slot_start + datetime.timedelta(minutes=APPOINTMENT_LENGTH_MINUTES) <= day_end:
            slots.append(slot_start)
            slot_start += datetime.timedelta(minutes=APPOINTMENT_LENGTH_MINUTES)
    return slots


def get_available_slots(limit: int = NUM_SLOTS_TO_OFFER):
    """Return up to `limit` open appointment slots (as datetime objects) from the calendar."""
    service = _get_service()
    tz = ZoneInfo(TIMEZONE)
    now = datetime.datetime.now(tz)
    window_end = now + datetime.timedelta(days=DAYS_TO_SEARCH_AHEAD)

    freebusy = service.freebusy().query(body={
        "timeMin": now.isoformat(),
        "timeMax": window_end.isoformat(),
        "timeZone": TIMEZONE,
        "items": [{"id": CALENDAR_ID}],
    }).execute(num_retries=3)

    busy_periods = freebusy["calendars"][CALENDAR_ID]["busy"]
    busy_ranges = [
        (datetime.datetime.fromisoformat(b["start"]), datetime.datetime.fromisoformat(b["end"]))
        for b in busy_periods
    ]

    candidate_slots = _business_hours_slots(DAYS_TO_SEARCH_AHEAD)
    available = []
    for slot in candidate_slots:
        slot_end = slot + datetime.timedelta(minutes=APPOINTMENT_LENGTH_MINUTES)
        overlaps = any(slot < b_end and slot_end > b_start for b_start, b_end in busy_ranges)
        if not overlaps:
            available.append(slot)
        if len(available) >= limit:
            break

    return available


def book_appointment(start_time: datetime.datetime, patient_name: str, reason: str) -> str:
    """Create a calendar event for the appointment. Returns the created event's link."""
    service = _get_service()
    end_time = start_time + datetime.timedelta(minutes=APPOINTMENT_LENGTH_MINUTES)

    event = {
        "summary": f"Appointment: {patient_name}",
        "description": f"Reason for visit: {reason}",
        "start": {"dateTime": start_time.isoformat(), "timeZone": TIMEZONE},
        "end": {"dateTime": end_time.isoformat(), "timeZone": TIMEZONE},
    }
    created = service.events().insert(calendarId=CALENDAR_ID, body=event).execute(num_retries=3)
    return created.get("htmlLink", "")


def format_slot(slot: datetime.datetime) -> str:
    """Human-friendly description of a slot, e.g. 'Monday, July 27 at 2:30 PM'."""
    return slot.strftime("%A, %B %d at %I:%M %p").replace(" 0", " ")
