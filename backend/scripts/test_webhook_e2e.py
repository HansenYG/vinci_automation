import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_supabase

client = TestClient(app)

db = get_supabase()

# 1. Find a pending offer
offers = db.table("lesson_tutor_offers").select("*").eq("offer_status", "pending").execute().data
if not offers:
    print("No pending offers found.")
    sys.exit(0)

offer = offers[0]
print(f"Testing with pending offer: lesson_id={offer['lesson_id']}, teacher_id={offer['teacher_id']}")

# 2. Get teacher's phone number
teacher = db.table("teachers").select("whatsapp_number").eq("teacher_id", offer["teacher_id"]).execute().data[0]
phone = teacher["whatsapp_number"]
print(f"Teacher phone: {phone}")

# 3. Construct payload (nested WATI structure)
payload = {
    "waId": phone,
    "eventType": "message",
    "owner": False,
    "message": {
        "type": "interactive",
        "interactive": {
            "type": "button_reply",
            "button_reply": {
                "id": "1",
                "title": "Accept"
            }
        }
    }
}

# 4. Send request
response = client.post("/api/webhooks/wati?secret=beta-webhook-secret-change-me", json=payload)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")

# 5. Check DB again
updated_offer = db.table("lesson_tutor_offers").select("*").eq("lesson_id", offer["lesson_id"]).eq("teacher_id", offer["teacher_id"]).execute().data[0]
print(f"Updated offer status: {updated_offer['offer_status']}")
