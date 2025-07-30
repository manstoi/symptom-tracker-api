from openai import OpenAI
from dotenv import load_dotenv
import os
import sounddevice as sd
from scipy.io.wavfile import write
import json
from datetime import datetime 
from flask import Flask, request, jsonify
from flask_cors import CORS

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def record_audio(filename="input.wav", duration=20, fs=44100):
    print(f"Recording audio for {duration} seconds... Speak now!")
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()  # Wait until recording is finished
    write(filename, fs, audio)  # Save as WAV file
    print(f"Audio saved to {filename}")


def transcribe_audio(filename="input.wav"):
    print(f"Transcribing audio from {filename}...")
    with open(filename, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    return transcript


def parse_transcript(transcript_text):
    print("Parsing transcript with GPT...")

    prompt = f"""
    Extract the following information from the user input and return it as a JSON object:
    1. Meals or food mentioned
    2. GERD, or Gastroesophageal Reflux Disease, symptoms described (such as heartburn, chest pain, etc.)
    3. Sleep duration or quality
    4. Medication mentioned
    5. Any other relevant notes

    User input: "{transcript_text}"

    Respond only with the JSON object.
    """

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    
    )

    structured_output = response.choices[0].message.content
    return structured_output

def save_entry(data_str):
    try:
        data = json.loads(data_str)
    except json.JSONDecodeError:
        print("GPT output was not valid JSON.")
        return
    
    # Format filename by date
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"health_log_{today}.json"

    # Load existing entries if the file exists
    if os.path.exists(filename):
        with open(filename, "r") as f:
            existing_data = json.load(f)
    else:
        existing_data = []

    # Append new entry
    entry = {
        "timestamp": datetime.now().isoformat(),
        "data": data
    }
    existing_data.append(entry)

    #save back to file
    with open(filename, "w") as f:
        json.dump(existing_data, f, indent=4)

    print(f"Entry saved to {filename}")


def analyze_trends(filename):
    if not os.path.exists(filename):
        print(f"No data file found: {filename}")
        return

    with open(filename, "r") as f:
        entries = json.load(f)

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

    Respond conversationally, but clearly
    """

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )

    insights = response.choices[0].message.content
    print("Health Insights: ", insights)



#checks how the script is being run
if __name__ == "__main__":
    record_audio()
    transcription = transcribe_audio()
    parsed_data = parse_transcript(transcription)
    save_entry(parsed_data)

    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"health_log_{today}.json"
    analyze_trends(filename)


app = Flask(__name__)
CORS(app) # Allow access from any frontend

@app.route("/upload", methods=["POST"])
def upload_audio():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    audio_file = request.files["audio"]
    audio_file.save("input.wav")

    # Transcribe, parse, save, analyze
    transcript = transcribe_audio("input.wav")
    parsed_data = parse_transcript(transcript)
    save_entry(parsed_data)

    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"health_log_{today}.json"
    insights = analyze_trends(filename)

    return jsonify({
        "transcript": transcript,
        "parsed_data": parsed_data,
        "insights": insights
    })