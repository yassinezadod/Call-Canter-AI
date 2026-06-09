import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def analyze_call_content(transcription_text: str) -> dict:
    """
    Analyseur universel Darija/Français utilisant Llama 3.3 70B.
    Clés JSON strictement synchronisées avec le Front-end Next.js.
    """
    
    system_prompt = """
    Vous êtes un système d'extraction d'entités et d'analyse de sentiment pour un centre d'appels multi-services au Maroc. 
    Votre rôle est de traiter des transcriptions contenant un mélange de Français et de Darija (arabe marocain).

    CONSIGNES LINGUISTIQUES POUR LA DARIJA :
    1. Ne traduisez pas mot à mot de manière littérale, interprétez le sens contextuel marocain.
    2. Identifiez les mots techniques phonétiques (ex: "ليكتريسيتي" = électricité, "الكونيكسيون" = connexion, "التكنيسيان" = technicien, "الشركة/الشارقة" = l'entreprise/la société).
    3. Identifiez les expressions de mécontentement, d'absence ou de panne (ex: "ما كينش" = absent/pas là, "ما كنلقاش" = je ne trouve pas, "تقطع" = coupure).

    RÈGLES D'ANALYSE STRICTES :
    - Évaluez le sentiment (Positif, Neutre, Négatif) en vous basant sur la gravité des faits décrits (ex: la répétition d'un problème ou l'indisponibilité répétée d'un responsable implique un sentiment Négatif).
    - Extrayez dans 'problemes' uniquement les faits RÉELS explicitement mentionnés dans le texte.
    - Générez dans 'solutions' des recommandations concrètes, logiques et exploitables pour l'agent ou l'entreprise afin de résoudre le litige du client.
    - Générez un résumé fidèle d'une seule phrase.

    Vous devez répondre EXCLUSIVEMENT sous la forme d'un objet JSON valide en français, respectant scrupuleusement la structure suivante :
    {
      "sentiment": "Positif" ou "Neutre" ou "Négatif",
      "resume": "votre résumé",
      "problemes": ["Problème 1", "Problème 2"],
      "solutions": ["Action recommandée 1", "Action recommandée 2"]
    }
    """

    user_content = f"Analyse cette transcription brute et génère l'objet JSON correspondant :\n\"{transcription_text}\""

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.0,  # Déterminisme total : élimine les hallucinations
            response_format={"type": "json_object"}
        )
        
        response_content = completion.choices[0].message.content
        if not response_content:
            raise ValueError("Réponse vide du modèle.")
            
        return json.loads(response_content)
        
    except Exception as e:
        print(f"❌ Erreur NLP Groq : {e}")
        return {
            "sentiment": "Neutre",
            "problemes": ["Erreur lors de l'extraction des données"],
            "solutions": ["Veuillez regénérer l'analyse"],
            "resume": "Impossible de traiter la transcription."
        }