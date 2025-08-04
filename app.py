from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory, Response
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
    2. GERD symptoms described (Globus, heartburn, acid reflux, etc.)
    3. Sleep duration or quality
    4. Medication mentioned (pantoprazole, famotidine, etc.)
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
def save_entry(transcript_text, data_str):
    try:
        data = json.loads(data_str)
    except json.JSONDecodeError:
        print("[DEBUG] Failed to parse JSON from parsed_data")
        return

    entry = {
        "timestamp": datetime.now().isoformat(),
        "transcript": transcript_text,
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

        save_entry(transcript, parsed_data)

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
    for entry in entries:
        entry[" _id"] = str(entry["_id"])
    return jsonify(entries)


@app.route("/run_weekly_analysis", methods=["GET"])
def run_weekly_analysis():
    try:
        # 1. Get Monday–Sunday range
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)

        # 2. Query Mongo for entries in that week
        entries = list(entries_collection.find({
            "timestamp": {
                "$gte": monday.isoformat(),
                "$lte": sunday.isoformat()
            }
        }, {"_id": 0}).sort("timestamp", 1))

        if not entries:
            return jsonify({"message": "No entries found for this week"}), 404

        # 3. Summarize with GPT
        prompt = f"""
        Here are the full journal entries for the week of {monday.date()} to {sunday.date()}:

        Each entry contains:
            - The original transcript (free text)
            - The structured parsed data

        {entries}

        Please briefly summarize:
        - Main trends
        - Triggers or patterns
        - Any improvements or worsening
        - 1–2 actionable suggestions
        """
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        analysis_text = response.choices[0].message.content

        # 4. Save to Mongo
        weekly_collection = db["weekly_analysis"]
        weekly_collection.insert_one({
            "week_start": monday.isoformat(),
            "week_end": sunday.isoformat(),
            "analysis": analysis_text,
            "created_at": datetime.now().isoformat()
        })

        return Response(analysis_text, mimetype="text/plain")

    except Exception as e:
        return jsonify({"error": str(e)}), 500

from flask import Response

@app.route("/run_monthly_analysis", methods=["GET"])
def run_monthly_analysis():
    try:
        now = datetime.now()
        first_day_of_month = datetime(now.year, now.month, 1)

        entries = list(entries_collection.find({
            "timestamp": {"$gte": first_day_of_month.isoformat()}
        }, {"_id": 0}).sort("timestamp", 1))

        if not entries:
            return Response("No entries found for this month.", mimetype="text/plain")

        prompt = f"""
        Here is the complete health log for the current month:
        {entries}

        Please:
        - Summarize the main trends over the month
        - Identify recurring triggers or patterns
        - Note any improvements or worsening over time
        - Suggest 1–2 actionable recommendations
        """

        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )

        analysis_text = response.choices[0].message.content.strip()

        # Save to Mongo
        monthly_analysis_collection = db["monthly_analysis"]
        monthly_analysis_collection.insert_one({
            "month": now.strftime("%Y-%m"),
            "analysis": analysis_text,
            "created_at": now.isoformat()
        })

        return Response(analysis_text, mimetype="text/plain")

    except Exception as e:
        return Response(f"Error: {str(e)}", mimetype="text/plain")



# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
