import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.api.routes.webhooks import _extract_text

payload2 = {
    "waId": "123",
    "eventType": "message",
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
print(f"payload2: '{_extract_text(payload2)}'")