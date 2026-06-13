# app/core/hallucinations.py

# Dictionnaire de correction des erreurs de transcription et phonétiques de Whisper
WHISPER_CORRECTIONS = {
    # ==========================================================================
    # 1. CORRECTIONS PHONÉTIQUES & BUGS D'ÉCOUTE (DARIJA / ARABE)
    # ==========================================================================
    # --- Cas Test 1 : Problème de connexion internet ---
    "غطف الصباح": "غدا ف الصباح",
    "غطف": "غدا ف",
    "مخدمش ليجاع": "ما خداماش ليا كاع",
    "عفك": "عفاك",
    "عن التكنيسيان": "عندك التكنيسيان",
    
    # --- Cas Test 2 : Double Facturation / Remboursement ---
    "البروموسيون دابا": "الرمبورسومون دابا",
    "لنصيط لك": "لونصيت ليك",
    "الغالط": "الغلط",
    "ربعة وعشرين": "24",
    
    # --- Cas Test 3 : Mauvais Agent / Modem en panne ---
    "بالريش": "بالحمر",          # Whisper entend "Voyant Ryche" au lieu de "Voyant rouge/Hmar"
    "وابغتش": "وما بغاتش",
    "قاعها ديومين": "كاع هادي يومين",
    "اول شنو": "إيوا أشنو",
    "شركت مزيان": "راكب مزيان",
    "هاتش شي": "هادشي",
    "تقدرت تدوز": "تقدر تدوز",
    "طيح": "طايح",
    "ماخدت نديرلك": "ما عندي ما ندير ليك",
    "بعدو عاوض": "بعد وعاود",

    # ==========================================================================
    # 2. SUPPRESSION DES VRAIES HALLUCINATIONS (Remplacées par du vide)
    # ==========================================================================
    # --- Hallucinations Réseaux Sociaux Arabe ---
    "اشتركوا في القناة": "",
    "اشتركوا ف القناة": "",
    "اشترك في القناة": "",
    "اشترك ف القناة": "",
    "اضغط على زر الجرس": "",
    "فعلوا الجرس": "",
    "لايك وفولو": "",
    "شكرا على المشاهدة": "",
    "شكرا للمشاهدة": "",
    
    # --- Hallucinations Réseaux Sociaux Français / Anglais ---
    "Abonnez-vous à la chaîne": "",
    "Abonnez-vous": "",
    "Laissez un pouce bleu": "",
    "Merci d'avoir regardé": "",
    "Thank you for watching": "",
    "Subscribe to the channel": "",
    "Subscribe": "",
    
    # --- Résidus et sous-titres fantômes Whisper ---
    "Sous-titres réalisés par": "",
    "Sous-titrage": "",
    "Transcrit par": "",
    "Subtitles by": ""
}