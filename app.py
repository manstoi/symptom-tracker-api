from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from datetime import datetime
from flask import Flask, request, jsonify
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
# AUDIO TRANSCRIPTION
# -----------------------------
def transcribe_audio(filename="input.wav"):
    print(f"Transcribing audio from {filename}...")
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
    print("Parsing transcript with GPT...")

    prompt = f"""
    Extract the following information from the user input and return it as a JSON object:
    1. Meals or food mentioned
    2. GERD symptoms described (such as heartburn, chest pain, etc.)
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

    structured_output = response.choices[0].message.content
    return structured_output

# -----------------------------
# SAVE ENTRY TO MONGODB
# -----------------------------
def save_entry(data_str):
    try:
        data = json.loads(data_str)
    except json.JSONDecodeError:
        print("GPT output was not valid JSON.")
        return

    entry = {
        "timestamp": datetime.now().isoformat(),
        "data": data
    }

    # Save to MongoDB
    entries_collection.insert_one(entry)
    print("Entry saved to MongoDB.")

# -----------------------------
# ANALYZE TRENDS FROM MONGODB
# -----------------------------
def analyze_trends():
    today_str = datetime.now().strftime("%Y-%m-%d")
    entries = list(entries_collection.find({
        "timestamp": {"$regex": f"^{today_str}"}
    }))

    if not entries:
        return "No entries found to analyze."

    logs_text = "\n".join(
        f"{entry['timestamp']} - {entry['data']}" for entry in entries
    )

    prompt = f"""
    You are a health assistant analyzing a user's daily health logs related to GERD, diet, sleep, and symptoms.

    Here are the entries for today:
    {logs_text}

    Based on this data, please:
    - Identify any patterns (e.g., food triggering symptoms)
    - Correlate sleep or medication use with symptoms
    - Suggest one or two practical insights

    Respond conversationally, but clearly.
    """

    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )

    insights = response.choices[0].message.content
    return insights

# -----------------------------
# API ROUTES
# -----------------------------
@app.route("/upload", methods=["POST"])
def upload_audio():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    audio_file.save("input.wav")

    transcript = transcribe_audio("input.wav")
    parsed_data = parse_transcript(transcript)
    save_entry(parsed_data)
    insights = analyze_trends()

    return jsonify({
        "transcript": transcript,
        "parsed_data": parsed_data,
        "insights": insights
    })

@app.route("/entries", methods=["GET"])
def get_entries():
    """Return all past symptom tracker entries from MongoDB."""
    entries = list(entries_collection.find({}, {"_id": 0}))
    return jsonify(entries)

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
