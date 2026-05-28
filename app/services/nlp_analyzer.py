import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def analyze_call_content(transcription_text: str):
    prompt = f"""
    Tu es un analyste expert pour un centre d'appels E-commerce au Maroc. 
    Analyse cette transcription (mélange de Darija et Français) et extrais les informations exactes.
    Ne devine pas de problèmes techniques si l'utilisateur parle de livraison ou de commande.

    Texte de l'appel : "{transcription_text}"

    Réponds UNIQUEMENT en JSON avec :
    - sentiment: (Positif, Neutre, ou Négatif)
    - problemes: (liste des problèmes RÉELS cités)
    - solutions_proposees: (recommandations logiques pour l'agent)
    - resume: (résumé fidèle en une phrase)
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant", # Ou "llama-3.1-8b-instant" selon tes préférences sur Groq
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"❌ Erreur NLP : {e}")
        return {
            "sentiment": "Inconnu",
            "problemes": [],
            "solutions_proposees": [],
            "resume": "Erreur lors de l'analyse."
        }