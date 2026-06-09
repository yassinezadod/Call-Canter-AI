import os
import shutil
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
from app.services.nlp_analyzer import analyze_call_content
from dotenv import load_dotenv


# Import de tes services
from app.services.whisper_stt import transcribe_audio
from app.services.storage import upload_audio
from bson import ObjectId

# 1. Chargement des variables d'environnement
load_dotenv()

app = FastAPI(title="AI Call Center Analytics")

# 2. NOUVEAU : CONFIGURATION DU MIDDLEWARE CORS
# Pour autoriser ton Next.js (port 3000) à appeler ton FastAPI (port 8000)
# ------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],  # Les URLs de ton application Next.js
    allow_credentials=True,
    allow_methods=["*"],  # Autorise toutes les requêtes (GET, POST, OPTIONS...)
    allow_headers=["*"],  # Autorise tous les headers HTTP
)
# ------------------------------------------------------------------

# 2. Configuration MongoDB avec Fallback
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

client = AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB_NAME]
calls_collection = db.calls
analyses_collection = db.analyses

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.on_event("startup")
async def startup_event():
    print(f"🚀 Serveur démarré !")
    print(f"🔗 MongoDB URI: {MONGO_URI}")
    print(f"📂 Database: {MONGO_DB_NAME}")

@app.post("/upload")
async def upload_and_transcribe(file: UploadFile = File(...)):
    # Vérification format
    if file.content_type not in ["audio/mpeg", "audio/wav", "audio/x-wav"]:
        raise HTTPException(status_code=400, detail="Seuls les fichiers MP3 et WAV sont acceptés.")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    # --- NOUVEAU : Calcul de la taille et récupération du type ---
    # file.size donne la taille en octets (bytes)
    # On la convertit en Mo (Megabytes) pour que ce soit plus lisible
    file_size_bytes = file.size
    file_size_mb = round(file_size_bytes / (1024 * 1024), 2)
    file_type = file.content_type
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'écriture locale : {str(e)}")
        
    try:
        # ÉTAPE 1 : Supabase (S3)
        s3_url = upload_audio(file_path)
        if not s3_url:
            raise HTTPException(status_code=500, detail="Échec de l'upload vers Supabase.")

        # ÉTAPE 2 : Transcription
        text_result = transcribe_audio(file_path)

        # --- ÉTAPE 3 : ANALYSE NLP (Qwen) ---
        analysis_result = analyze_call_content(text_result)
        
        # ÉTAPE 4 : MongoDB Local (Enregistrement enrichi)
        call_document = {
            "filename": file.filename,
            "s3_url": s3_url,
            "transcription": text_result,
            "file_size": f"{file_size_mb} MB", # On stocke la taille lisible
            "content_type": file_type,         # On stocke le type MIME
            "created_at": datetime.utcnow(),
            "status": "completed"
        }
        
        await calls_collection.update_one(
            {"filename": file.filename},  
            {"$set": call_document},      
            upsert=True                   
        )

        # On récupère le document pour avoir son _id (clé étrangère)
        saved_call = await calls_collection.find_one({"filename": file.filename})
        call_id = str(saved_call["_id"])


        # 2. On insère l'analyse dans 'analyses' liée par call_id
        analysis_document = {
            "call_id": call_id, # Clé étrangère vers la collection 'calls'
            "sentiment": analysis_result.get("sentiment"),
            "problemes": analysis_result.get("problemes"),
            "solutions": analysis_result.get("solutions"),
            "resume": analysis_result.get("resume"),
            "analyzed_at": datetime.utcnow()
        }

        await analyses_collection.update_one(
            {"call_id": call_id},
            {"$set": analysis_document},
            upsert=True
        )
        
        # ÉTAPE 5 : Nettoyage local
        if os.path.exists(file_path):
            os.remove(file_path) 
        
        return {
            "filename": file.filename,
            "size": f"{file_size_mb} MB",
            "type": file_type,
            "s3_url": s3_url,
            "transcription": text_result,
            "status": "Succès"
        }
        
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        print(f"❌ Erreur lors du traitement : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement : {str(e)}")

@app.get("/calls")
async def get_all_calls():
    calls = []
    try:
        async for call in calls_collection.find().sort("created_at", -1):
            call["_id"] = str(call["_id"]) 
            calls.append(call)
        return calls
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur BDD : {str(e)}")
    
@app.get("/analyses")
async def get_all_analyses():
    """Récupère toutes les analyses de calls"""
    analyses = []
    try:
        async for analysis in analyses_collection.find().sort("analyzed_at", -1):
            analysis["_id"] = str(analysis["_id"])
            analyses.append(analysis)
        return analyses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analyses/{call_id}")
async def get_analysis_by_call(call_id: str):
    """Récupère l'analyse spécifique d'un call via sa clé étrangère"""
    analysis = await analyses_collection.find_one({"call_id": call_id})
    if analysis:
        analysis["_id"] = str(analysis["_id"])
        return analysis
    raise HTTPException(status_code=404, detail="Analyse non trouvée")

@app.get("/calls/{call_id}")
async def get_single_call(call_id: str):
    """
    Récupère un appel spécifique (métadonnées + transcription) via son _id MongoDB
    """
    try:
        # Vérification si le format de l'ID est un ObjectId MongoDB valide
        if not ObjectId.is_valid(call_id):
            raise HTTPException(status_code=400, detail="Format de call_id invalide.")

        # Recherche du document dans la collection 'calls'
        call = await calls_collection.find_one({"_id": ObjectId(call_id)})
        
        if not call:
            raise HTTPException(status_code=404, detail="Document audio introuvable.")

        # Conversion de l'ObjectId en chaîne de caractères pour le JSON Next.js
        call["_id"] = str(call["_id"])
        return call

    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        print(f"❌ Erreur lors de la récupération du call : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne du serveur : {str(e)}")