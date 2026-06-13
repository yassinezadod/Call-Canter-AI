import os
import shutil
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Importation de tes services applicatifs
from app.services.nlp_analyzer import analyze_call_content
from app.services.whisper_stt import transcribe_audio
from app.services.agent_evaluator import evaluate_agent_performance
from app.services.storage import upload_audio
from bson import ObjectId

# 1. Chargement des variables d'environnement
load_dotenv()

frontend_origins_raw = os.getenv("FRONTEND_URL")
if not frontend_origins_raw:
    raise RuntimeError("❌ ERREUR : La variable FRONTEND_URL est manquante dans le fichier .env")

ALLOWED_ORIGINS = [origin.strip() for origin in frontend_origins_raw.split(",")]

# 2. Gestion moderne du cycle de vie (Lifespan) de l'application
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Serveur CallCenterAI démarré avec succès !")
    print(f"🔗 CORS Allowed Origins: {ALLOWED_ORIGINS}")
    print(f"📂 Base de données MongoDB connectée : {os.getenv('MONGO_DB_NAME')}")
    yield
    # Logique exécutée à l'arrêt du serveur
    client.close()
    print("🛑 Connexions à la base de données MongoDB fermées avec succès.")

app = FastAPI(title="AI Call Center Analytics", lifespan=lifespan)

# 3. Configuration du middleware CORS pour ton écosystème Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],  # Autorise toutes les méthodes (GET, POST, OPTIONS...)
    allow_headers=["*"],  # Autorise tous les en-têtes HTTP
)

# 4. Configuration et initialisation du client MongoDB
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

client = AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB_NAME]
calls_collection = db.calls
analyses_collection = db.analyses
evaluations_collection = db.evaluations

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ==============================================================================
# FLUX A : TUNNEL ANALYTIQUE CLIENT & SENTIMENTS (FLUX TRADITIONNEL)
# ==============================================================================

@app.post("/upload")
async def upload_and_transcribe(file: UploadFile = File(...)):
    """
    Ingère un appel client classique, le stocke, le transcrit,
    et génère une analyse globale sémantique des sentiments et des problèmes.
    """
    if file.content_type not in ["audio/mpeg", "audio/wav", "audio/x-wav"]:
        raise HTTPException(status_code=400, detail="Seuls les fichiers MP3 et WAV sont acceptés.")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    file_size_bytes = file.size
    file_size_mb = round(file_size_bytes / (1024 * 1024), 2)
    file_type = file.content_type
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'écriture locale : {str(e)}")
        
    try:
        # ÉTAPE 1 : Supabase (S3 Cloud Storage)
        s3_url = upload_audio(file_path)
        if not s3_url:
            raise HTTPException(status_code=500, detail="Échec de l'upload vers Supabase.")

        # ÉTAPE 2 : Transcription Audio via Whisper
        text_result = transcribe_audio(file_path)

        # ÉTAPE 3 : Analyse Sémantique Client via Llama 3.3
        analysis_result = analyze_call_content(text_result)
        
        # ÉTAPE 4 : Enregistrement enrichi des métadonnées de l'appel
        call_document = {
            "filename": file.filename,
            "s3_url": s3_url,
            "transcription": text_result,
            "file_size": f"{file_size_mb} MB",
            "content_type": file_type,         
            "created_at": datetime.utcnow(),
            "status": "completed"
        }
        
        await calls_collection.update_one(
            {"filename": file.filename},  
            {"$set": call_document},      
            upsert=True                   
        )

        saved_call = await calls_collection.find_one({"filename": file.filename})
        call_id = str(saved_call["_id"])

        # ÉTAPE 5 : Liaison croisée avec l'analyse (Clé Étrangère call_id)
        analysis_document = {
            "call_id": call_id,
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
        print(f"❌ Erreur lors du traitement analytique : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement : {str(e)}")


@app.get("/calls")
async def get_all_calls():
    """Récupère l'ensemble de l'historique des appels triés par date décroissante"""
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
    """Récupère la liste de toutes les analyses de sentiments extraites"""
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
    """Récupère l'analyse sémantique d'un appel via sa clé étrangère call_id"""
    analysis = await analyses_collection.find_one({"call_id": call_id})
    if analysis:
        analysis["_id"] = str(analysis["_id"])
        return analysis
    raise HTTPException(status_code=404, detail="Analyse introuvable pour ce call_id.")


@app.get("/calls/{call_id}")
async def get_single_call(call_id: str):
    """Récupère les détails d'un document audio spécifique via son _id MongoDB"""
    try:
        if not ObjectId.is_valid(call_id):
            raise HTTPException(status_code=400, detail="Format de call_id invalide.")

        call = await calls_collection.find_one({"_id": ObjectId(call_id)})
        if not call:
            raise HTTPException(status_code=404, detail="Document audio introuvable.")

        call["_id"] = str(call["_id"])
        return call
    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        print(f"❌ Erreur lors de la récupération du call : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne du serveur : {str(e)}")
    

# ==============================================================================
# FLUX B : EVALUATION DE LA PERFORMANCE & QUALITÉ DE SERVICE AGENT
# ==============================================================================

@app.post("/evaluate-agent")
async def upload_and_evaluate_agent(file: UploadFile = File(...)):
    """
    Endpoint pour ingérer un appel de supervision, segmenter automatiquement
    les locuteurs Agent/Client, corriger Whisper et auditer l'agent.
    """
    if file.content_type not in ["audio/mpeg", "audio/wav", "audio/x-wav"]:
        raise HTTPException(status_code=400, detail="Seuls les fichiers MP3 et WAV sont acceptés.")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    file_size_bytes = file.size
    file_size_mb = round(file_size_bytes / (1024 * 1024), 2)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'écriture locale : {str(e)}")
        
    try:
        # 1. Stockage Cloud (Supabase)
        s3_url = upload_audio(file_path)
        if not s3_url:
            raise HTTPException(status_code=500, detail="Échec de l'upload vers Supabase.")

        # 2. Transcription Audio via Whisper
        text_result = transcribe_audio(file_path)

        # 3. Évaluation IA via Llama 3.3 (avec dictionnaire de lissage phonétique)
        evaluation_result = evaluate_agent_performance(text_result)
        
        # 4. Préparation du document pour MongoDB (Aucun risque de clé 'null')
        evaluation_document = {
            "filename": file.filename,
            "s3_url": s3_url,
            "transcription_brute": text_result,
            "file_size": f"{file_size_mb} MB",
            "conversation_segmentee": evaluation_result.get("conversation_segmentee"),
            "evaluation": evaluation_result.get("evaluation"),  
            "created_at": datetime.utcnow()
        }
        
        await evaluations_collection.update_one(
            {"filename": file.filename},
            {"$set": evaluation_document},
            upsert=True
        )
        
        if os.path.exists(file_path):
            os.remove(file_path)
            
        return {
            "status": "Succès",
            "filename": file.filename,
            "data": evaluation_document
        }
        
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        print(f"❌ Erreur lors de l'évaluation de l'agent : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement : {str(e)}")


@app.get("/agent-evaluations")
async def get_all_agent_evaluations():
    """Récupère l'ensemble de l'historique des audits de performance des agents"""
    evaluations = []
    try:
        async for eval_doc in evaluations_collection.find().sort("created_at", -1):
            eval_doc["_id"] = str(eval_doc["_id"])
            evaluations.append(eval_doc)
        return evaluations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agent-evaluations/{evaluation_id}")
async def get_single_agent_evaluation(evaluation_id: str):
    """
    Récupère une fiche de notation d'agent spécifique via son _id MongoDB.
    Indispensable pour l'affichage et la navigation dynamique côté Frontend [id].
    """
    try:
        if not ObjectId.is_valid(evaluation_id):
            raise HTTPException(status_code=400, detail="Format d'evaluation_id invalide.")

        evaluation = await evaluations_collection.find_one({"_id": ObjectId(evaluation_id)})
        if not evaluation:
            raise HTTPException(status_code=404, detail="Fiche d'évaluation introuvable.")

        evaluation["_id"] = str(evaluation["_id"])
        return evaluation
    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        print(f"❌ Erreur lors de la récupération de la fiche agent : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne du serveur : {str(e)}")