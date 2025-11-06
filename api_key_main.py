import asyncio
import os
import tempfile
import shutil
from fastapi import FastAPI, UploadFile, File
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()
client = None

@app.on_event("startup")
async def startup_event():
    global client
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    models = client.models.list()
    for m in models.data:
        print(m.id)

@app.get("/")
async def root():
    return {"message": "Welcome to the GPT-4o AI chatbot API!"}


def transcribe_file(file_path):
    with open(file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=audio_file
       
        )
    return transcription.text

def get_gpt_response(prompt: str) -> str:
    """Send a user message to GPT-4o / GPT-4o-mini and get the response"""
    response = client.chat.completions.create(
        model="gpt-4o-mini-transcribe",  # or "gpt-4o"
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content
              

@app.post("/stt")
async def transcribe_audio(file: UploadFile = File(...)):
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
        shutil.copyfileobj(file.file, temp_file)
        temp_path = temp_file.name
    # Run blocking Whisper call in background thread
    text = await asyncio.to_thread(transcribe_file, temp_path)
    
    ai_response = await asyncio.to_thread(get_gpt_response, text)

    return {"text": text,
            "ai_response": ai_response
            }




