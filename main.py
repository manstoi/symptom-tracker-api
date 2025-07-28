from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

file_path = "c:/Users/manue/Desktop/ai-project-rag/medical.txt"

try: 
    with open(file_path, "r") as file:
        file_content = file.read()
except FileNotFoundError:
    print("File not found. Please check the path.")
    exit()

user_input = input("Enter your question: ")

messages = [
    {"role": "system", "content": "You are a helpful assistant that reviews files and answers questions based on their content."},
    {"role": "user", "content": f"The file content is: \n{file_content}\n\nMy question is: {user_input}"}
]

response = client.chat.completions.create(
    model="gpt-4o",
    messages = messages
)

print("AI response:", response.choices[0].message.content)