from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
import certifi
import traceback

load_dotenv()

# -----------------------------
# OpenAI Client
# -----------------------------
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -----------------------------
# Flask App
# -----------------------------
app = Flask(__name__)
CORS(app)  # Allow access from any frontend

# -----------------------------
# MongoDB Connection
# -----------------------------
MONGO_URI = os.getenv("MONGODB_URI")
mongo_client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = mongo_client["symptom_tracker"]
entries_collection = db["entries"]

# -----------------------------
# HOME ROUTE
# -----------------------------
@app.route("/", methods=["GET"])
def home():
    return send_from_directory("static", "index.html")

# -----------------------------
# AUDIO TRANSCRIPTION
# -----------------------------
def transcribe_audio(filename="input.wav"):
    size = os.path.getsize(filename)
    print(f"[DEBUG] Transcribing file: {filename}, size: {size} bytes")

    with open(filename, "rb") as audio_file:
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )

    print(f"[DEBUG] Transcript result: {transcript}")
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
        print("[DEBUG] Failed to parse JSON from parsed_data")
        return

    entry = {
        "timestamp": datetime.now().isoformat(),
        "data": data
    }
    entries_collection.insert_one(entry)
    print("[DEBUG] Entry saved to MongoDB.")


# -----------------------------
# API ROUTES
# -----------------------------
@app.route("/upload", methods=["POST"])
def upload_audio():
    try:
        if "audio" not in request.files:
            return jsonify({"error": "No audio file provided"}), 400

        # Save uploaded audio temporarily
        audio_file = request.files["audio"]
        audio_path = "input.wav"
        audio_file.save(audio_path)
        print(f"[DEBUG] Saved audio to {audio_path}, size: {os.path.getsize(audio_path)} bytes")

        # Process audio
        transcript = transcribe_audio(audio_path)
        print(f"[DEBUG] Transcript: {transcript}")

        parsed_data = parse_transcript(transcript)
        print(f"[DEBUG] Parsed Data: {parsed_data}")

        save_entry(parsed_data)

        os.remove(audio_path)
        print("[DEBUG] Temporary audio file removed.")

        return jsonify({
            "transcript": transcript,
            "parsed_data": parsed_data,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/entries", methods=["GET"])
def get_entries():
    entries = list(entries_collection.find({}, {"_id": 0}).sort("timestamp", -1))
    return jsonify(entries)

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
