import asyncio
import os
import whisper
import uuid
import pyttsx3
from fuzzywuzzy import fuzz
from gtts import gTTS
from fastapi.responses import Response
from fastapi import FastAPI, UploadFile, File,BackgroundTasks,Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse,FileResponse
from utils.common_function import text_to_speech,local_gpt,cleanup_file,clean_text

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ['http://localhost:5173'] 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Text-Response"],  
)
CONV_FOLDER = "conv"
os.makedirs(CONV_FOLDER, exist_ok=True)
stt_model = None
def transcribe_file(file_path: str) -> str:
    result = stt_model.transcribe(file_path)
    print(result["text"],"000000000000")
    return result["text"]

@app.on_event("startup")
async def load_model_on_startup():
    global stt_model
    print("⏳ Loading Whisper model in background...")
    stt_model = await asyncio.to_thread(whisper.load_model, "tiny")
    print("✅ Whisper model loaded!")

@app.get("/")
async def root():
    return {"message": "Welcome to the offline GPT-4o AI chatbot API!!!!"}



@app.get("/start")
async def start_conversation():
    greeting = "Hi, this is the Healthcare Center. How can I help you ?"
    greeting_audio = "greeting.mp3"

    # Convert text greeting to audio using gTTS
    text_to_speech(greeting, greeting_audio)
    print("🤖 Starting conversation with greeting...")

    # ✅ Read audio bytes manually so we can safely include custom header
    with open(greeting_audio, "rb") as f:
        audio_bytes = f.read()

    headers = {"X-Text-Response": greeting}
    print(headers)
    return Response(content=audio_bytes, media_type="audio/mpeg", headers=headers)

@app.post("/stt")
async def transcribe_audio(file: UploadFile = File(...), text: str = Form(None),background_tasks: BackgroundTasks = BackgroundTasks()):
    print("initiated")
    try:
        unique_id = str(uuid.uuid4())
        temp_file = os.path.join(CONV_FOLDER, f"temp_{unique_id}_{file.filename}")
        
        with open(temp_file, "wb") as f:
            f.write(await file.read())

        # STT
        print("🎤 Starting transcription...")
        # result = await asyncio.to_thread(stt_model.transcribe, temp_file)
        user_message = text
        print(f"🗣️ User said: '{user_message}' (length: {len(user_message)})")
        
        # Check if transcription is empty
        if not user_message:
            print("⚠️ Empty transcription - audio might be silent or invalid format")
            user_message = "silent audio detected"

        # GPT
        response = local_gpt(user_message)
        display,bot_reply=clean_text(response)
        print(f"🤖 Bot reply: {bot_reply}")

        # TTS
        output_tts_path = os.path.join(CONV_FOLDER, f"response_{unique_id}.mp3")
        await asyncio.to_thread(text_to_speech, bot_reply, output_tts_path)

        # Clean up input file
        os.remove(temp_file)

        # Schedule cleanup of output file after response is sent
        background_tasks.add_task(cleanup_file, output_tts_path)
        print(FileResponse(
            output_tts_path,
            media_type="audio/mpeg",
            filename="response.mp3",
            headers={"X-Text-Response": display}
        )
        
        )

        return FileResponse(
            output_tts_path,
            media_type="audio/mpeg",
            filename="response.mp3",
            headers={"X-Text-Response": display}
        )

    except Exception as e:
        print(f"❌ Error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
    
