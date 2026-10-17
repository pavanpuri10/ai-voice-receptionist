import os
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

account_sid = os.environ["TWILIO_ACCOUNT_SID"]
auth_token = os.environ["TWILIO_AUTH_TOKEN"]
client = Client(account_sid, auth_token)

call = client.calls.create(
    to="+919502020405",
    from_="+13203732477",
    url="https://excavator-prowler-earpiece.ngrok-free.dev/voice",
)

print("Call started, SID:", call.sid)
