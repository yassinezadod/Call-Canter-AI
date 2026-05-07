from fastapi import FastAPI, UploadFile, File, HTTPException
from app.services.whisper_stt import transcribe_audio # Import du nouveau service
import os
import shutil

app = FastAPI(title="AI Call Center Analytics")

UPLOAD_DIR = "uploads"

@app.post("/upload")
async def upload_and_transcribe(file: UploadFile = File(...)):
    # 1. Vérification format (Contrainte technique 7)
    if file.content_type not in ["audio/mpeg", "audio/wav"]:
        raise HTTPException(status_code=400, detail="MP3 ou WAV uniquement.")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    # 2. Sauvegarde locale
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # 3. Transcription via Whisper (Cahier des charges section 4.2)
        text_result = transcribe_audio(file_path)
        
        # 4. Nettoyage (optionnel : supprimer le fichier après transcription)
        # os.remove(file_path) 
        
        return {
            "filename": file.filename,
            "transcription": text_result,
            "status": "Succès"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la transcription : {str(e)}")