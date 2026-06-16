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
    Analyse universelle, globale et agnostique d'un appel de supervision :
    - Nettoyage des hallucinations et fautes phonétiques de Whisper
    - Diarization sémantique abstraite basée sur les sauts de lignes (silences audio)
    - Grille de notation stricte basée uniquement sur des concepts comportementaux
    """
    
    # 1. Application des corrections phonétiques et nettoyage de Whisper
    if transcription_text:
        for mot_errone, mot_correct in WHISPER_CORRECTIONS.items():
            transcription_text = transcription_text.replace(mot_errone, mot_correct)
        
    # Nettoyage des espaces tout en conservant scrupuleusement les sauts de ligne (\n)
    if transcription_text:
        lines = [line.strip() for line in transcription_text.splitlines() if line.strip()]
        transcription_nettoyee = "\n".join(lines)
    else:
        transcription_nettoyee = ""

    # 2. Définition du prompt système ABSOLUMENT ABSTRAIT ET GLOBAL
    system_prompt = """
    Vous êtes un système expert d'assurance qualité et d'analyse NLP senior pour un réseau international de centres d'appels.
    Votre rôle est d'analyser une transcription textuelle découpée par lignes, où chaque ligne (\n) représente un bloc de parole isolé par un silence audio dans l'enregistrement.

    RÈGLES ABSOLUES DE DIARIZATION (SEGMENTATION DES LOCUTEURS) :
    Chaque retour à la ligne indique une transition potentielle de parole. Vous devez analyser la posture et l'intention logique de chaque ligne pour distribuer le texte dans le tableau 'conversation_segmentee' sans jamais fusionner des répliques distinctes.

    1. LOGIQUE COMPORTEMENTALE DE L'AGENT :
       - Il représente l'entité professionnelle qui fournit le service.
       - Postures types : Formules d'accueil de l'entreprise, réponses de politesse aux salutations de l'appelant, questions de diagnostic, demandes de validations/identifiants, propositions de solutions, excuses institutionnelles, ou gestion des indisponibilités et de la prise de congé.
       - RÈGLE SÉMANTIQUE : Les formules de bienvenue ou de réception de gratitude en fin d'échange appartiennent au représentant du service.

    2. LOGIQUE COMPORTEMENTALE DU CLIENT :
       - Il représente l'usager externe qui sollicite l'entité.
       - Postures types : Salutation initiale, exposition du besoin ou d'un dysfonctionnement, description d'un historique d'incidents, fourniture de données privées en réponse aux questions, ou expression d'un soulignement et d'un remerciement.
       - RÈGLE SÉMANTIQUE : Les expressions finales de satisfaction ou de gratitude appartiennent à l'usager.

    GRILLE DE NOTATION STRICTE (ZÉRO TOLÉRANCE POUR LE REPORT DE DEMANDE) :
    Évaluez la performance globale de l'agent sur une note de 0 à 100 :
    - ÉCHEC DE TRAITEMENT : Si le professionnel refuse la prise en charge, déclare ne pas être disponible, ou demande à l'usager de réitérer sa démarche ultérieurement (un autre jour ou plus tard) sans avoir effectué de diagnostic ni enregistré de dossier d'incident, la note doit STRICTEMENT être inférieure à 30/100. La politesse de la forme ne compense jamais un refus de traitement.

    Vous devez répondre EXCLUSIVEMENT sous la forme d'un objet JSON valide, respectant scrupuleusement la structure suivante :
    {
      "conversation_segmentee": [
        {"locuteur": "Agent" | "Client", "texte": "Extrait textuel exact de la ligne analysée"}
      ],
      "evaluation": {
        "sentiment_client": "Positif" ou "Neutre" ou "Négatif",
        "problematique_client": "Synthèse claire, concise et objective de l'objet de la demande",
        "note_agent": 0,
        "solutions_proposees_par_agent": ["Action, refus ou report formulé par l'agent"],
        "points_forts": ["Exemple de point fort ou 'Aucun' si la note est basse"],
        "axes_amelioration": ["Raison stricte et objective de la mauvaise note liée à la qualité de service"],
        "commentaire_global": "Synthèse managériale complète de la performance."
      }
    }
    """

    try:
        # 3. Appel à Groq avec Llama 3.3 70B
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Transcription découpée par silences à structurer :\n{transcription_nettoyee}"}
            ],
            temperature=0.0,  # Déterminisme total
            response_format={"type": "json_object"}
        )
        
        return json.loads(completion.choices[0].message.content)
        
    except Exception as e:
        print(f"❌ Erreur Évaluation Complète Agent : {e}")
        return {
          "conversation_segmentee": [],
          "evaluation": {
            "sentiment_client": "Neutre",
            "problematique_client": "Erreur d'extraction interne",
            "note_agent": 0,
            "solutions_proposees_par_agent": [],
            "points_forts": [],
            "axes_amelioration": [],
            "commentaire_global": "Échec de l'évaluation automatique suite à une erreur technique."
          }
        }