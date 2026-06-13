import os
import json
from groq import Groq
from dotenv import load_dotenv

# Import du dictionnaire de correction phonétique et nettoyage
from app.core.hallucinations import WHISPER_CORRECTIONS

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def evaluate_agent_performance(transcription_text: str) -> dict:
    """
    Analyse complète d'un appel de supervision :
    - Correction phonétique et nettoyage des hallucinations Whisper
    - Segmentation du dialogue (Agent/Client)
    - Extraction des métriques de performance unifiées sous la clé globale 'evaluation'
    """
    
    # 1. Application des corrections phonétiques et nettoyage de Whisper
    if transcription_text:
        for mot_errone, mot_correct in WHISPER_CORRECTIONS.items():
            transcription_text = transcription_text.replace(mot_errone, mot_correct)
        
    # Nettoyage des espaces multiples résiduels
    transcription_text = " ".join(transcription_text.split()).strip()

    # 2. Définition du prompt système pour Llama 3.3 70B
    system_prompt = """
    Vous êtes un expert en assurance qualité et un analyste NLP senior pour un centre d'appels au Maroc.
    Votre rôle est d'analyser une transcription brute (Français/Darija) et d'en extraire un rapport d'évaluation complet.

    CONSIGNES D'ANALYSE ET COUVERTURE DES DONNÉES :
    1. SEGMENTATION : Identifiez qui parle. L'Agent salue, diagnostique et aide. Le Client expose sa situation et réclame.
    2. SENTIMENT CLIENT : Évaluez l'humeur et le sentiment du CLIENT uniquement (Positif, Neutre, Négatif).
    3. PROBLÉMATIQUE : Synthétisez le problème principal ou la réclamation initiale exprimée par le client.
    4. SOLUTIONS DE L'AGENT : Extrayez la ou les solutions concrètes que l'agent a données ou programmées pour le client durant l'échange.
    5. ÉVALUATION DE L'AGENT : Donnez une note stricte sur 100. 
       ATTENTION : Soyez extrêmement sévère sur la qualité de service (ZÉRO TOLÉRANCE). Si l'agent fait preuve d'arrogance, manque de politesse, refuse ouvertement d'aider le client sans motif valable, ou raccroche au nez de manière abrupte, la note doit STRICTEMENT être inférieure à 30/100. 
       Détaillez ses points forts (mettez "Aucun" si l'agent a été mauvais ou non professionnel) et ses axes d'amélioration.

    Vous devez répondre EXCLUSIVEMENT sous la forme d'un objet JSON valide en français, respectant scrupuleusement la structure suivante :
    {
      "conversation_segmentee": [
        {"locuteur": "Agent", "texte": "Phrase de l'agent"},
        {"locuteur": "Client", "texte": "Phrase du client"}
      ],
      "evaluation": {
        "sentiment_client": "Positif" ou "Neutre" ou "Négatif",
        "problematique_client": "Description claire du problème du client",
        "note_agent": 85,
        "solutions_proposees_par_agent": ["Solution 1", "Solution 2"],
        "points_forts": ["Exemple de point fort"],
        "axes_amelioration": ["Exemple d'axe d'amélioration"],
        "commentaire_global": "Synthèse managériale de la performance de l'agent."
      }
    }
    """

    try:
        # 3. Appel de l'API Groq avec le modèle Llama 3.3 70B
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Transcription brute à analyser :\n\"{transcription_text}\""}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        # Renvoie le dictionnaire JSON parsé directement utilisable par main.py
        return json.loads(completion.choices[0].message.content)
        
    except Exception as e:
        print(f"❌ Erreur Évaluation Complète Agent : {e}")
        # Fallback sécurisé respectant la structure de données pour éviter le plantage du serveur
        return {
          "conversation_segmentee": [],
          "evaluation": {
            "sentiment_client": "Neutre",
            "problematique_client": "Erreur d'extraction",
            "note_agent": 0,
            "solutions_proposees_par_agent": [],
            "points_forts": [],
            "axes_amelioration": [],
            "commentaire_global": "Échec de l'évaluation automatique suite à une erreur interne."
          }
        }