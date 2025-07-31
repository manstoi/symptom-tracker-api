from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient

load_dotenv()

# OpenAI Client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Flask App
app = Flask(__name__)
CORS(app)  # Allow access from any frontend

# MongoDB Connection
mongo_client = MongoClient(os.getenv("MONGODB_URI"))
db = mongo_client["symptom_tracker"]
entries_collection = db["entries"]

# -----------------------------
# HOME ROUTE (should be first)
# -----------------------------
@app.route("/", methods=["GET"])
def home():
    return send_from_directory("static", "index.html")

# -----------------------------
# AUDIO TRANSCRIPTION
# -----------------------------
def transcribe_audio(filename="input.wav"):
    with open(filename, "rb") as audio_file:
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    return transcript

# -----------------------------
# PARSE TRANSCRIPT WITH GPT
# -----------------------------
def parse_transcript(transcript_text):
    prompt = f"""
    Extract the following information from the user input and return it as a JSON object:
    1. Meals or food mentioned
    2. GERD symptoms described
    3. Sleep duration or quality
    4. Medication mentioned
    5. Any other relevant notes

    User input: "{transcript_text}"

    Respond only with the JSON object.
    """
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response.choices[0].message.content

# -----------------------------
# SAVE ENTRY TO MONGODB
# -----------------------------
def save_entry(data_str):
    try:
        data = json.loads(data_str)
    except json.JSONDecodeError:
        return

    entry = {
        "timestamp": datetime.now().isoformat(),
        "data": data
    }
    entries_collection.insert_one(entry)

# -----------------------------
# ANALYZE TRENDS
# -----------------------------
def analyze_trends():
    entries = list(entries_collection.find({}, {"_id": 0}))
    if not entries:
        return "No entries found."

    today_str = datetime.now().strftime("%Y-%m-%d")
    today_entries = [e for e in entries if e["timestamp"].startswith(today_str)]

    prompt = f"""
    Here is the complete health log:
    {entries}

    Today's entries:
    {today_entries}

    Based on this full history:
    - Identify recurring patterns or triggers
    - Note if today's symptoms match past patterns
    - Suggest 1–2 practical tips for managing symptoms
    """
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    return response.choices[0].message.content

# -----------------------------
# API ROUTES
# -----------------------------
@app.route("/upload", methods=["POST"])
def upload_audio():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    audio_path = "input.wav"
    audio_file.save(audio_path)

    transcript = transcribe_audio(audio_path)
    parsed_data = parse_transcript(transcript)
    save_entry(parsed_data)
    insights = analyze_trends()

    # Delete the temporary file
    os.remove(audio_path)

    return jsonify({
        "transcript": transcript,
        "parsed_data": parsed_data,
        "insights": insights
    })

@app.route("/entries", methods=["GET"])
def get_entries():
    entries = list(entries_collection.find({}, {"_id": 0}))
    return jsonify(entries)

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
