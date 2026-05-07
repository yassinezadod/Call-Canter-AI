import os
from groq import Groq
from dotenv import load_dotenv
from app.core.config import WHISPER_DARIJA_PROMPT

load_dotenv() # Charge les variables du fichier .env

# 1. Configuration du chemin FFmpeg (Indispensable pour Windows)
ffmpeg_path = r'C:\ffmpeg\bin'
if ffmpeg_path not in os.environ["PATH"]:
    os.environ["PATH"] += os.pathsep + ffmpeg_path

# 2. Initialisation du client Groq
# Note : Utilise un fichier .env pour cette clé dans un vrai projet
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def transcribe_audio(file_path: str) -> str:
    """
    Transcription hybride (Darija/Français) via Groq Cloud.
    Correction de l'erreur Pylance et optimisation du prompt.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Fichier introuvable : {file_path}")

    with open(file_path, "rb") as file:
        # Appel à l'API Groq avec Whisper Large-V3
        transcription = client.audio.transcriptions.create(
            file=(os.path.basename(file_path), file.read()),
            model="whisper-large-v3",
            response_format="json",
            # Le prompt aide l'IA à reconnaître le vocabulaire marocain et technique
            prompt=WHISPER_DARIJA_PROMPT
        )
    
    return transcription.text.strip()