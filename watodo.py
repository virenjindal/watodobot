from flask import Flask, request
import requests
import firebase_admin
from firebase_admin import credentials, firestore
import datetime
import os
import sys

app = Flask(__name__)

# Firebase setup
cred = credentials.Certificate("firebase-adminsdk.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# WhatsApp credentials from environment
WHATSAPP_TOKEN = os.environ["WHATSAPP_TOKEN"]
PHONE_NUMBER_ID = os.environ["PHONE_NUMBER_ID"]

DEFAULT_TODOS = ["Focus & Hardwork","Drink 1L water","LinkedIn Posts","Meditate", "9pm Walk","Call Home"]

def send_message(phone, text):
    print("Sending to:", phone, "->", text, flush=True)  # <- Add this line
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "text": {"body": text}
    }
    requests.post(url, headers=headers, json=payload)
    print(f"Sent message to {phone}, status: {response.status_code}, response: {response.text}")

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    print("Webhook POST received")
    sys.stdout.flush()
    if request.method == "GET":
        # Webhook verification
        if request.args.get("hub.verify_token") == "testtoken":
            return request.args.get("hub.challenge")
        return "Verification failed", 403

    if request.method == "POST":
        data = request.get_json()
        print("Incoming webhook data:", data, flush=True)
        try:
            phone = data["entry"][0]["changes"][0]["value"]["messages"][0]["from"]
            msg = data["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"].strip().lower()

            today = datetime.date.today().isoformat()
            todos_ref = db.collection("users").document(phone).collection("todos").document(today)

            doc = todos_ref.get()
            if not doc.exists:
                todos_ref.set({"items": DEFAULT_TODOS})

            todos = todos_ref.get().to_dict()["items"]

            if msg == "list":
                if not todos:
                    send_message(phone, "All tasks done!")
                else:
                    send_message(phone, "Your to-dos:\n" + "\n".join(f"- {todo}" for todo in todos))
            elif msg.startswith("done "):
                done_item = msg[5:].strip()
                if done_item in todos:
                    todos.remove(done_item)
                    todos_ref.set({"items": todos})
                    send_message(phone, f"Marked '{done_item}' as done!")
                else:
                    send_message(phone, f"'{done_item}' not found in today's list.")
            elif msg.startswith("add "):
                new_item = msg[4:].strip()
                if new_item not in todos:
                    todos.append(new_item)
                    todos_ref.set({"items": todos})
                    send_message(phone, f"Added: {new_item}")
                else:
                    send_message(phone, f"'{new_item}' is already on your list.")
            else:
                send_message(phone, "Available commands:\n- list\n- done <task>\n- add <task>")
        except Exception as e:
            print("Error:", e)
        return "OK", 200

@app.route("/", methods=["GET"])
def index():
    return "WhatsApp To-Do Bot is running!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
