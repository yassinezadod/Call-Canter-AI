import os
from groq import Groq
from dotenv import load_dotenv
from app.core.config import WHISPER_DARIJA_PROMPT

load_dotenv()  # Charge les variables du fichier .env

# 1. Configuration du chemin FFmpeg (Indispensable pour Windows)
ffmpeg_path = r'C:\ffmpeg\bin'
if ffmpeg_path not in os.environ["PATH"]:
    os.environ["PATH"] += os.pathsep + ffmpeg_path

# 2. Initialisation du client Groq
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def transcribe_audio(file_path: str) -> str:
    """
    Transcription hybride (Darija/Français) via Groq Cloud.
    Découpage automatique basé sur les silences et pauses audio.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Fichier introuvable : {file_path}")

    with open(file_path, "rb") as file:
        # 🌟 Passage en verbose_json pour récupérer la structure temporelle des silences
        transcription = client.audio.transcriptions.create(
            file=(os.path.basename(file_path), file.read()),
            model="whisper-large-v3",
            response_format="verbose_json",  # ✨ Récupère les segments de silences
            prompt=WHISPER_DARIJA_PROMPT
        )
    
    # 🌟 Reconstruction du texte : chaque segment (séparé par un silence) va à la ligne
    segments_detectes = []
    
    # On vérifie si les segments existent dans la réponse de Groq
    if hasattr(transcription, 'segments') and transcription.segments:
        for segment in transcription.segments:
            # segment est généralement un dictionnaire ou un objet possédant la clé 'text'
            text_line = segment.get('text', '').strip() if isinstance(segment, dict) else segment.text.strip()
            if text_line:
                segments_detectes.append(text_line)
        
        # Renvoie un bloc de texte propre où chaque blanc audio crée un saut de ligne \n
        return "\n".join(segments_detectes)
        
    # Sécurité au cas où la structure verbose_json échoue
    return transcription.text.strip()