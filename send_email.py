import smtplib
import requests
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dateutil import parser

import firebase_admin
from firebase_admin import credentials, firestore

# --- Ladda Firebase-nyckeln från GitHub Secret ---
firebase_key_json = os.environ["FIREBASE_KEY"]
firebase_key_dict = json.loads(firebase_key_json)

with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
    json.dump(firebase_key_dict, f)
    key_path = f.name

cred = credentials.Certificate(key_path)
firebase_admin.initialize_app(cred)
db = firestore.client()

# --- Hämta alla användare från Firestore ---
users_ref = db.collection("users").stream()
users = []
for doc in users_ref:
    data = doc.to_dict()
    if data.get("email") and data.get("area"):
        users.append(data)

if not users:
    print("Inga användare i Firestore.")
    exit()

print(f"Hittade {len(users)} användare.")

# --- Hämta skickade händelser ---
SKICKADE_FIL = "skickade.json"
if os.path.exists(SKICKADE_FIL):
    with open(SKICKADE_FIL, "r") as f:
        skickade = set(json.load(f))
else:
    skickade = set()

# --- Hämta polishändelser ---
nu = datetime.now(timezone.utc)
polisapi = requests.get("https://polisen.se/api/events")
polisdata = polisapi.json()

# Samla nya händelser per stad
nya_per_stad = {}

for data in polisdata:
    event_id = str(data["id"])
    if event_id in skickade:
        continue

    event_tid = parser.parse(data["datetime"])
    if event_tid.tzinfo is None:
        event_tid = event_tid.replace(tzinfo=timezone.utc)

    alder_timmar = (nu - event_tid).total_seconds() / 3600
    if alder_timmar > 24:
        continue

    plats = data["location"]["name"].lower()
    text = (data["name"] + " " + data.get("summary", "")).lower()

    irrelevant = any(x in text for x in [
        "övning", "övar", "träning", "information", "samverkan"
    ])

    brott = any(x in text for x in [
        "misshandel", "stöld", "rån", "rattfylleri",
        "narkotika", "våld", "brand", "inbrott", "bedrägeri"
    ])

    if not brott or irrelevant:
        continue

    # Matcha mot städer
    stad = data["location"]["name"]  # ex: "Stockholm"
    if stad not in nya_per_stad:
        nya_per_stad[stad] = []
    nya_per_stad[stad].append(data)

# --- Skicka mail till rätt användare ---
nya_skickade_ids = set()

for user in users:
    user_email = user["email"]
    user_area = user["area"]  # ex: "Stockholm"

    # Hitta händelser som matchar användarens stad
    matchande = []
    for stad, händelser in nya_per_stad.items():
        if stad.lower().startswith(user_area.lower()):
            matchande.extend(händelser)

    if not matchande:
        print(f"Inga nya händelser för {user_email} ({user_area})")
        continue

    email_text = ""
    for event in matchande:
        tid = parser.parse(event["datetime"])
        tid_str = tid.strftime("%d %b %H:%M")
        email_text += f"{tid_str}\n"
        email_text += f"{event['name']}\n"
        email_text += f"{event.get('summary', '')}\n"
        email_text += f"Plats: {event['location']['name']}\n\n"
        nya_skickade_ids.add(str(event["id"]))

    # Skicka mail
    email_sender = "blake.joeseph08@gmail.com"
    email_password = os.environ.get("EMAIL_PASSWORD", "rtmanuhhdoegvixq")

    message = MIMEMultipart()
    message["From"] = email_sender
    message["To"] = user_email
    message["Subject"] = f"NYA BROTT {user_area.upper()} – {len(matchande)} händelser"
    message.attach(MIMEText(email_text, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(email_sender, email_password)
        server.sendmail(email_sender, user_email, message.as_string())
        server.quit()
        print(f"Mail skickat till {user_email} med {len(matchande)} händelser!")
    except Exception as e:
        print(f"Kunde inte skicka till {user_email}: {e}")

# --- Spara nya ID:n och pusha ---
if nya_skickade_ids:
    skickade.update(nya_skickade_ids)
    with open(SKICKADE_FIL, "w") as f:
        json.dump(list(skickade), f)

    subprocess.run(["git", "config", "user.email", "action@github.com"])
    subprocess.run(["git", "config", "user.name", "GitHub Action"])
    subprocess.run(["git", "add", SKICKADE_FIL])
    subprocess.run(["git", "commit", "-m", "Uppdatera skickade händelser"])
    subprocess.run(["git", "push"])
    print("skickade.json uppdaterad och pushad.")
else:
    print("Inga nya händelser.")
