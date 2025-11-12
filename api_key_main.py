
import os
import io
import uuid
import mimetypes
import asyncio
from openai import OpenAI
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Form,Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse,StreamingResponse
from utils.cm_functions import appointment_gpt,insurance_gpt
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Text-Response"],
)
print("Loaded API key:", os.getenv("OPENAI_API_KEY"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY") )




def speech_to_text(file_path: str) -> str:
    """
    Convert audio to text using GPT-4o-mini-transcribe.
    """
    mime_type = mimetypes.guess_type(file_path)[0] or "audio/mpeg"

    with open(file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=(os.path.basename(file_path), audio_file, mime_type),
        )

    return transcript.text.title()
def text_to_speech(text: str, voice: str) -> io.BytesIO:
    """
    Convert text to speech using gpt-4o-mini-tts via the OpenAI client.
    Returns an in-memory bytes buffer containing the audio.
    """
    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=text
    )

    # Read the raw audio bytes
    audio_bytes = response.read()

    # Return as an in-memory buffer
    return io.BytesIO(audio_bytes)


#       ******************ALL API'S******************


@app.get("/")
async def root():
    return {"message": "Online Voice AI API Ready ✅"}

@app.get("/start")
async def start_greeting(bot: str = "appointment"):
    """
    Single greeting endpoint for both bots.
    Query param `bot` decides which bot: 'appointment' or 'insurance'.
    """
    if bot.lower() == "appointment":
        greeting = "Hi, this is the Healthcare Center. How can I help you?"
        voice = "alloy"  # Female voice
    elif bot.lower() == "insurance":
        # Greeting for Insurance Assistance Center
        greeting = "Hello! This is the Insurance Assistance Center. How can I assist you?"
        voice = "echo"  # Male voice
    else:
        return JSONResponse(
            content={"error": "Invalid bot type. Use 'appointment' or 'insurance'."},
            status_code=400
        )

    print(f"🤖 {bot.capitalize()} bot greeting...")
#  'Verse'. Supported values are: 'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer', 'coral', 'verse', 'ballad', 'ash', 'sage', 'marin', and 'cedar'."
    # Generate TTS audio
    audio_buffer = text_to_speech(greeting, voice=voice)
    audio_buffer.seek(0)

    return StreamingResponse(
        audio_buffer,
        media_type="audio/mpeg",
        headers={"X-Text-Response": greeting}
    )
    

@app.post("/appointment")
async def appointment_(file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    try:
        print("🎤 Audio received...")

        # Save uploaded file temporarily
        unique_id = uuid.uuid4().hex
        temp_audio = f"temp_{unique_id}.wav"

        with open(temp_audio, "wb") as f:
            f.write(await file.read())

        # STEP 1: STT (blocking → thread)
        print("about to do stt")
        user_text = await asyncio.to_thread(speech_to_text, temp_audio)
        print("🧑 User said:", user_text)

        if not user_text.strip():
            user_text = "Silent audio detected"

        # STEP 2: GPT reply
        bot_reply = await asyncio.to_thread(appointment_gpt, user_text)
        print("🤖 Bot reply:", bot_reply)

        # STEP 3: TTS
        audio_out = await asyncio.to_thread(text_to_speech, bot_reply,"alloy")

        output_file = f"reply_{unique_id}.mp3"
        with open(output_file, "wb") as f:
             f.write(audio_out.getvalue())

        # Cleanup temp files
        background_tasks.add_task(lambda: os.remove(temp_audio))
        background_tasks.add_task(lambda: os.remove(output_file))

        return FileResponse(
            output_file,
            media_type="audio/mpeg",
            filename="response.mp3",
            headers={"X-Text-Response": bot_reply}
        )

    except Exception as e:
        print("❌ Error:", e)
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/insurance")
async def insurance_chat(file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    try:
        print("🎤 Audio received...")

        # Save uploaded file temporarily
        unique_id = uuid.uuid4().hex
        temp_audio = f"temp_{unique_id}.wav"

        with open(temp_audio, "wb") as f:
            f.write(await file.read())

        # STEP 1: STT (blocking → thread)
        user_text = await asyncio.to_thread(speech_to_text, temp_audio)
        print("🧑 User said:", user_text)
   
        if not user_text.strip():
            user_text = "Silent audio detected"

        # STEP 2: GPT reply
        bot_reply = await asyncio.to_thread(insurance_gpt, user_text)
        # bot_reply = insurance_gpt(user_text)
        print("🤖 Bot reply:", bot_reply)

        # STEP 3: TTS
        audio_out = await asyncio.to_thread(text_to_speech, bot_reply,"echo")

        output_file = f"reply_{unique_id}.mp3"
        with open(output_file, "wb") as f:
            f.write(audio_out.getvalue())

        # Cleanup temp files
        background_tasks.add_task(lambda: os.remove(temp_audio))
        background_tasks.add_task(lambda: os.remove(output_file))

        return FileResponse(
            output_file,
            media_type="audio/mpeg",
            filename="response.mp3",
            headers={"X-Text-Response": bot_reply}
        )

    except Exception as e:
        print("❌ Error:", e)
        return JSONResponse(content={"error": str(e)}, status_code=500)
