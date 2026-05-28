import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Charge les variables d'environnement
load_dotenv()

# Configuration Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY")
BUCKET_NAME = os.getenv("SUPABASE_BUCKET", "call-center-audio")

# Initialisation du client Supabase
# On vérifie que les clés sont présentes pour éviter les crashs
if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️ Attention : SUPABASE_URL ou SUPABASE_SECRET_KEY manquante dans le .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_audio(file_path: str):
    """
    Prend un chemin de fichier local et l'envoie sur le bucket Supabase.
    Retourne l'URL publique du fichier.
    """
    if not os.path.exists(file_path):
        print(f"❌ Fichier local introuvable : {file_path}")
        return None

    file_name = os.path.basename(file_path)

    try:
        # Ouverture du fichier en mode binaire
        with open(file_path, 'rb') as f:
            print(f"⏳ Upload de {file_name} vers Supabase S3...")
            
            # On utilise upsert=True pour pouvoir renvoyer le même fichier sans erreur
            supabase.storage.from_(BUCKET_NAME).upload(
                path=file_name,
                file=f,
                file_options={
                    "content-type": "audio/mpeg",
                    "x-upsert": "true"
                }
            )
        
        # On génère l'URL publique pour ton dashboard
        response = supabase.storage.from_(BUCKET_NAME).get_public_url(file_name)
        
        print(f"✅ Fichier disponible sur : {response}")
        return response

    except Exception as e:
        print(f"❌ Erreur critique lors de l'upload Supabase : {str(e)}")
        return None