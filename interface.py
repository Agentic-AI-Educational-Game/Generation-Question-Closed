# interface.py
import streamlit as st
import requests
import json
from groq import Groq # Import Groq SDK

# --- PAGE CONFIGURATION (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(page_title="Générateur & Vérificateur de Questions", layout="wide")

# --- Configuration ---
FLASK_API_BASE_URL = "http://localhost:5000" # Ajustez si votre API Flask est ailleurs
QCM_ENDPOINT = f"{FLASK_API_BASE_URL}/generate_qcm"
FITB_ENDPOINT = f"{FLASK_API_BASE_URL}/generate_fitb"

# --- Initialize Groq Client ---
# This section will now run AFTER st.set_page_config
groq_client = None
GROQ_API_KEY = None

try:
    if "GROQ_API_KEY" in st.secrets:
        GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    else:
        st.sidebar.warning("GROQ_API_KEY non trouvé dans les secrets. Vérification désactivée.")

    if GROQ_API_KEY:
        groq_client = Groq(api_key=GROQ_API_KEY)
        st.sidebar.success("Client Groq initialisé.")
    elif "GROQ_API_KEY" in st.secrets: # Only show missing key warning if it was expected
        st.sidebar.warning("Client Groq non initialisé (problème de clé API).")

except Exception as e:
    st.sidebar.error(f"Erreur initialisation client Groq : {e}")
    groq_client = None


# --- Helper Function to Call Flask API ---
def call_flask_api(endpoint_url, text_input):
    payload = {"texte": text_input}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(endpoint_url, data=json.dumps(payload), headers=headers, timeout=180)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur de requête API : {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                st.error(f"Détails de l'erreur API : {error_details}")
                return {"error": str(e), "details": error_details, "raw_output": "Erreur API"}
            except json.JSONDecodeError:
                st.error(f"Contenu de l'erreur API (non JSON) : {e.response.text}")
                return {"error": str(e), "raw_output": e.response.text}
        return {"error": str(e), "raw_output": "Erreur de connexion API"}
    except json.JSONDecodeError:
        st.error("Erreur de décodage de la réponse JSON de l'API.")
        return {"error": "Erreur Décodage JSON", "raw_output": "JSON invalide de l'API"}

# --- Helper Function to Call Groq API for Verification (in French) ---
def call_groq_for_verification(context_text, generated_question_data, question_type):
    if not groq_client:
        return "Client Groq non initialisé. Veuillez vous assurer que GROQ_API_KEY est configuré dans .streamlit/secrets.toml et que le client est bien démarré."

    q_data = generated_question_data # raccourci
    prompt_parts = [
        f"Vous êtes un assistant IA expert en évaluation de questions pédagogiques ({question_type}). **Soyez direct, concis et répondez en français.** Évitez les phrases introductives ou les commentaires superflus.",
        "Analysez la question suivante basée sur le texte original fourni.",
        "\n**Texte Original Fourni :**",
        "--- TEXTE ORIGINAL DÉBUT ---",
        context_text,
        "--- TEXTE ORIGINAL FIN ---",
        "\n",
        f"**Question ({question_type}) Générée à Évaluer :**",
        f"Question : {q_data.get('question', 'N/A')}",
        f"Option A : {q_data.get('A', 'N/A')}",
        f"Option B : {q_data.get('B', 'N/A')}",
        f"Option C : {q_data.get('C', 'N/A')}",
        f"Option D : {q_data.get('D', 'N/A')}",
        f"Réponse Attendue (par l'IA génératrice) : {q_data.get('reponse', 'N/A')}",
        "\n",
        "**Critères d'Évaluation (Répondez de manière concise pour chaque point) :**",
        "1.  **Exactitude & Justification :** La question et la réponse attendue sont-elles exactes par rapport au texte ? Justifiez brièvement.",
        "2.  **Clarté & Ambiguïté :** La question est-elle claire ? Y a-t-il des ambiguïtés ?",
        "3.  **Pertinence :** La question est-elle pertinente par rapport aux informations clés du texte ?",
        "4.  **Qualité des Options (Distracteurs) :** Les distracteurs sont-ils plausibles mais incorrects ? Y a-t-il des problèmes avec les options ?",
        "5.  **Spécificités FITB (si applicable) :** Le blanc est-il bien choisi ? La phrase est-elle naturelle ?",
        "\n",
        "**Format de Réponse Exigé (Direct et Structuré, en français) :**",
        "   - **Avis Général Concis :** (Ex: Excellente, Bonne avec réserves, Médiocre, Problématique - ajouter 1-2 mots clés si besoin).",
        "   - **Analyse Point par Point (Directe) :**",
        "     1.  Exactitude : [Votre évaluation concise]",
        "     2.  Clarté : [Votre évaluation concise]",
        "     3.  Pertinence : [Votre évaluation concise]",
        "     4.  Options : [Votre évaluation concise]",
        "     5.  FITB (si applicable) : [Votre évaluation concise]",
        "   - **Problèmes Principaux (Liste à puces si besoin) :**",
        "     - [Problème 1 s'il y en a]",
        "     - [Problème 2 s'il y en a]",
        "   - **Suggestions d'Amélioration (Si et seulement si nécessaire, soyez bref) :**",
        "     *   Question Révisée : [Nouvelle question si besoin]",
        "     *   Options Révisées : A) ..., B) ..., C) ..., D) ...",
        "     *   Réponse Corrigée : [Lettre]",
        "     (Si aucune amélioration majeure n'est nécessaire, indiquez 'Original satisfaisant' ou similaire).",
        "\n**Priorité à la concision et à la pertinence. Évitez toute formulation excessive.**"
    ]
    full_prompt = "\n".join(prompt_parts)

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Vous êtes un évaluateur IA de questions. Soyez analytique, direct, concis et répondez uniquement en français. Fournissez des évaluations structurées sans phrases inutiles."
                },
                {
                    "role": "user",
                    "content": full_prompt,
                }
            ],
            model="llama3-70b-8192", # llama3-8b-8192 might also work and be faster if 70b is too slow
            temperature=0.1, # Very low temperature for factual, less "creative" or verbose responses
            max_tokens=1500, # Should be enough for a concise but complete analysis
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Erreur lors de l'appel à l'API Groq : {str(e)}"
    if not groq_client:
        return "Client Groq non initialisé. Veuillez vous assurer que GROQ_API_KEY est configuré dans .streamlit/secrets.toml et que le client est bien démarré."

    q_data = generated_question_data # raccourci
    prompt_parts = [
        f"Vous êtes un assistant IA expert, spécialisé dans l'évaluation de la qualité des questions pédagogiques ({question_type}) générées à partir d'un texte fourni. **Veuillez répondre impérativement et intégralement en français.**",
        "Voici le texte original sur lequel la question est basée :",
        "--- TEXTE ORIGINAL DÉBUT ---",
        context_text,
        "--- TEXTE ORIGINAL FIN ---",
        "\n",
        f"Voici la question de type '{question_type}' générée par une autre IA :",
        f"Question : {q_data.get('question', 'N/A')}",
        f"Option A : {q_data.get('A', 'N/A')}",
        f"Option B : {q_data.get('B', 'N/A')}",
        f"Option C : {q_data.get('C', 'N/A')}",
        f"Option D : {q_data.get('D', 'N/A')}",
        f"L'IA génératrice affirme que la bonne réponse est : {q_data.get('reponse', 'N/A')}",
        "\n",
        "Votre tâche est d'évaluer de manière critique cette question générée. Veuillez considérer les points suivants :",
        "1.  **Exactitude et Justification :** La question est-elle factuellement correcte en se basant *uniquement* sur le texte fourni ? La 'bonne réponse' indiquée est-elle vraiment correcte selon le texte ? Expliquez votre raisonnement.",
        "2.  **Clarté et Ambiguïté :** La question est-elle formulée de manière claire et sans ambiguïté ? Y a-t-il des termes qui pourraient être mal interprétés ?",
        "3.  **Pertinence :** La question teste-t-elle une information ou un concept significatif du texte, ou est-elle triviale ?",
        "4.  **Qualité des Options (Distracteurs) :**",
        "    *   Les options incorrectes (distracteurs) sont-elles suffisamment plausibles pour défier quelqu'un qui n'a pas bien compris le texte, mais clairement fausses pour quelqu'un qui l'a compris ?",
        "    *   Certains distracteurs sont-ils trop évidemment faux ou trop proches d'être corrects (ce qui pourrait rendre la question confuse ou avoir plusieurs 'bonnes' réponses d'un certain point de vue) ?",
        "5.  **Spécificités FITB (si applicable) :** S'il s'agit d'une question à compléter (Texte à Trous), le blanc cible-t-il un mot-clé ou un concept approprié ? La structure de la phrase autour du blanc est-elle naturelle ?",
        "\n",
        "**Exigences pour la Réponse (en français) :**",
        "Veuillez structurer votre analyse comme suit :",
        "   - **Avis Général :** Un bref résumé de la qualité de la question (par exemple, Excellente, Bonne, Passable, Médiocre, Problématique).",
        "   - **Analyse Détaillée :** Abordez chacun des points numérotés ci-dessus avec des commentaires spécifiques et des justifications basées sur le texte.",
        "   - **Problèmes Identifiés :** Listez clairement tous les problèmes que vous avez trouvés (par exemple, 'La bonne réponse est en fait B, et non A, d'après la phrase X', 'L'option C est trop vague', 'La question n'est pas pertinente par rapport au thème principal').",
        "   - **Suggestions d'Amélioration (Si Nécessaire) :**",
        "     *   Si la question présente des défauts, suggérez une version révisée de la question, des options ou de la bonne réponse.",
        "     *   Si vous suggérez de nouvelles options, assurez-vous qu'elles conservent le format QCM/FITB.",
        "     *   Si la question originale est bonne, indiquez qu'aucune amélioration significative n'est nécessaire.",
        "\nCommencez votre réponse par votre avis général. **Répondez intégralement en français.**"
    ]
    full_prompt = "\n".join(prompt_parts)

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Vous êtes un assistant IA qui évalue des questions pédagogiques. Fournissez des commentaires détaillés et des suggestions exclusivement en français."
                },
                {
                    "role": "user",
                    "content": full_prompt,
                }
            ],
            model="llama3-70b-8192",
            temperature=0.2,
            max_tokens=2000,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Erreur lors de l'appel à l'API Groq : {str(e)}"

# --- Streamlit App Layout (Actual page content starts here) ---
st.title("📝 Générateur de Questions avec Vérification IA")
st.markdown("Générez des QCM ou des Textes à Trous, puis demandez à une IA (Groq) de les analyser.")

# --- Session State ---
if 'text_input' not in st.session_state:
    st.session_state.text_input = ""
if 'question_type' not in st.session_state:
    st.session_state.question_type = "QCM"
if 'generated_data' not in st.session_state:
    st.session_state.generated_data = None
if 'raw_model_output' not in st.session_state:
    st.session_state.raw_model_output = ""
if 'verification_response' not in st.session_state:
    st.session_state.verification_response = None
if 'last_text_for_generation' not in st.session_state:
    st.session_state.last_text_for_generation = ""


# --- Input Area ---
st.subheader("1. Fournissez votre texte :")
text_area_input = st.text_area("Collez ou écrivez votre texte ici :",
                               value=st.session_state.text_input,
                               height=250,
                               key="text_input_area")

if text_area_input != st.session_state.text_input:
    st.session_state.text_input = text_area_input
    st.session_state.generated_data = None
    st.session_state.raw_model_output = ""
    st.session_state.verification_response = None
    st.session_state.last_text_for_generation = ""

st.subheader("2. Choisissez le type de question :")
question_type_options = ('QCM (Question à Choix Multiples)', 'FITB (Texte à Trous / Fill-in-the-Blank)')
current_qt_index = 0 if st.session_state.question_type == "QCM" else 1
question_type_selection = st.radio(
    "Quel type de question souhaitez-vous générer ?",
    question_type_options,
    index=current_qt_index,
    key="question_type_radio"
)

new_question_type = "QCM" if question_type_selection == question_type_options[0] else "FITB"
if new_question_type != st.session_state.question_type:
    st.session_state.question_type = new_question_type
    st.session_state.generated_data = None
    st.session_state.raw_model_output = ""
    st.session_state.verification_response = None

# --- Generate Button ---
if st.button("🚀 Générer la question", type="primary", use_container_width=True):
    if not st.session_state.text_input.strip():
        st.warning("Veuillez entrer un texte avant de générer une question.")
    else:
        st.session_state.verification_response = None
        st.session_state.last_text_for_generation = st.session_state.text_input

        endpoint_to_call = QCM_ENDPOINT if st.session_state.question_type == "QCM" else FITB_ENDPOINT
        with st.spinner(f"Génération de la question {st.session_state.question_type} en cours..."):
            api_response = call_flask_api(endpoint_to_call, st.session_state.text_input)
            st.session_state.generated_data = api_response
            st.session_state.raw_model_output = api_response.get("raw_output", "Aucune sortie brute disponible.")
            if "error" in api_response:
                 st.session_state.last_text_for_generation = "" # Don't allow verification if generation failed
            st.rerun()

# --- Display Area for Generated Question ---
if st.session_state.generated_data:
    st.divider()
    st.subheader(f"Résultat de la Génération ({st.session_state.question_type})")

    data = st.session_state.generated_data

    if "error" in data and data["error"] != "Erreur de connexion API":
        error_message = data.get('details', {}).get('error', data.get('error', 'Erreur inconnue'))
        st.error(f"Erreur de l'API de génération: {error_message}")
        raw_output_key = "raw_output_on_error" if "raw_output_on_error" in data.get("details", {}) else "raw_output"
        raw_output_val = None
        if isinstance(data.get("details"), dict) and raw_output_key in data["details"]:
            raw_output_val = data["details"].get(raw_output_key)
        elif raw_output_key in data:
             raw_output_val = data.get(raw_output_key)
        
        if raw_output_val and raw_output_val != "Erreur API": # Avoid showing "Erreur API" as raw output if that's the content
            st.text_area("Sortie brute de l'API (sur erreur):", value=str(raw_output_val), height=150, disabled=True)

    elif data.get("question") and not data["question"].startswith("Could not parse"): # "Could not parse" is from your Flask app
        st.markdown(f"**Question :** {data.get('question', 'N/A')}")
        cols = st.columns(2)
        cols[0].markdown(f"**A)** {data.get('A', 'N/A')}")
        cols[0].markdown(f"**B)** {data.get('B', 'N/A')}")
        cols[1].markdown(f"**C)** {data.get('C', 'N/A')}")
        cols[1].markdown(f"**D)** {data.get('D', 'N/A')}")
        st.markdown(f"**Réponse correcte (par le modèle générateur) :** <span style='color:green; font-weight:bold;'>{data.get('reponse', 'N/A')}</span>", unsafe_allow_html=True)

        if groq_client and st.session_state.last_text_for_generation:
            if st.button("🔍 Vérifier avec l'IA (Groq)", key="verify_button", use_container_width=True):
                with st.spinner("L'IA de vérification analyse la question... (cela peut prendre un moment)"):
                    verification_result = call_groq_for_verification(
                        st.session_state.last_text_for_generation,
                        st.session_state.generated_data,
                        st.session_state.question_type
                    )
                    # Check if Groq call itself returned an error message
                    if verification_result.startswith("Erreur lors de l'appel à l'API Groq") or \
                       verification_result.startswith("Client Groq non initialisé"):
                        st.session_state.verification_response = None 
                        st.error(verification_result) 
                    else:
                        st.session_state.verification_response = verification_result
                    st.rerun()
        elif not groq_client:
            st.caption("Service de vérification IA (Groq) non disponible (vérifiez la clé API et le démarrage du client).")
        elif not st.session_state.last_text_for_generation:
             st.caption("Générez d'abord une question avec succès pour activer la vérification.")

    elif "raw_output" in data and data["raw_output"] and \
         data["raw_output"] not in ["Erreur de connexion API", "Erreur API", "Aucune sortie brute disponible.", "JSON invalide de l'API"]:
        st.warning("La génération a produit une sortie, mais elle n'a pas pu être structurée correctement. Vérifiez la sortie brute.")
    # Avoid showing generic error if a specific API error was already shown
    elif not ("error" in data and data["error"] != "Erreur de connexion API"): 
        if not (data.get("question") and not data["question"].startswith("Could not parse")): # If not already handled by successful display
            st.error("Aucune question n'a pu être générée ou parsée. Vérifiez la sortie brute si disponible.")


    if st.session_state.raw_model_output and \
       st.session_state.raw_model_output not in ["Erreur de connexion API", "Erreur API", "Aucune sortie brute disponible.", "JSON invalide de l'API"]:
        with st.expander("Afficher la sortie brute du modèle générateur", expanded=False):
            st.text_area("Sortie brute du générateur:", value=st.session_state.raw_model_output, height=200, disabled=True, key="raw_output_display")

# --- Display Area for Verification Response ---
if st.session_state.verification_response:
    st.divider()
    st.subheader("🕵️‍♂️ Analyse de l'IA de Vérification (Groq)")
    st.markdown(st.session_state.verification_response)


if not st.session_state.text_input and not st.session_state.generated_data:
    st.info("Entrez un texte et cliquez sur 'Générer la question' pour commencer.")

st.divider()
st.markdown("---")
st.markdown("<p style='text-align: center;'>Développé avec Streamlit, llama.cpp & Groq</p>", unsafe_allow_html=True)

if st.button("🧹 Effacer et recommencer", use_container_width=True, key="clear_all"):
    st.session_state.text_input = ""
    st.session_state.question_type = "QCM"
    st.session_state.generated_data = None
    st.session_state.raw_model_output = ""
    st.session_state.verification_response = None
    st.session_state.last_text_for_generation = ""
    st.rerun()