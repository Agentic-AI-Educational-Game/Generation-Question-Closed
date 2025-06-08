import streamlit as st
import requests
import json
import re
from groq import Groq
from db_utils import load_texts, save_question, get_mongo_client

# --- CONFIG & INITIALIZATION ---
st.set_page_config(page_title="Générateur de Questions", layout="wide")
get_mongo_client()

# --- CONSTANTS ---
FLASK_API_BASE_URL = "http://localhost:5000"
QCM_ENDPOINT = f"{FLASK_API_BASE_URL}/generate_qcm"
FITB_ENDPOINT = f"{FLASK_API_BASE_URL}/generate_fitb"

# --- GROQ CLIENT INITIALIZATION ---
groq_client = None
try:
    if "groq" in st.secrets and "GROQ_API_KEY" in st.secrets["groq"]:
        api_key = st.secrets["groq"]["GROQ_API_KEY"]
        if api_key:
            groq_client = Groq(api_key=api_key)
            st.sidebar.success("Client Groq initialisé.")
        else:
            st.sidebar.warning("Clé API Groq est vide. Vérification IA désactivée.")
    else:
        st.sidebar.warning("GROQ_API_KEY non trouvée sous [groq] dans secrets.toml.")
except Exception as e:
    st.sidebar.error(f"Erreur initialisation Groq: {e}")

# --- HELPER FUNCTIONS ---
def call_flask_api(endpoint_url, text_input):
    payload = {"texte": text_input}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(endpoint_url, data=json.dumps(payload), headers=headers, timeout=180)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_details = {"error": f"Erreur de requête API: {e}", "raw_output": "Erreur de connexion API"}
        if hasattr(e, 'response') and e.response is not None:
            try: error_details.update(e.response.json())
            except json.JSONDecodeError: error_details["raw_output"] = e.response.text
        return error_details
    except json.JSONDecodeError:
        return {"error": "Erreur Décodage JSON", "raw_output": "JSON invalide reçu de l'API"}

def call_groq_for_verification(context_text, q_data, question_type):
    if not groq_client: return "Vérification IA non disponible (client Groq non initialisé)."
    
    prompt_parts_base = [f"Vous êtes un assistant IA expert, extrêmement rigoureux, spécialisé dans l'évaluation et l'amélioration de questions pédagogiques ({question_type}). **Votre réponse doit être en français, structurée et directement exploitable.**", "\n**Contexte de la Question :**\n---\n" + context_text + "\n---", f"\n**Question Générée à Évaluer :**", f"  - **Type :** {question_type}", f"  - **Question :** {q_data.get('question', 'N/A')}", f"  - **Options :** A) {q_data.get('A', 'N/A')}, B) {q_data.get('B', 'N/A')}, C) {q_data.get('C', 'N/A')}, D) {q_data.get('D', 'N/A')}", f"  - **Réponse Attendue :** {q_data.get('reponse', 'N/A')}", "\n" + "="*40, "**VOTRE MISSION : ANALYSE ET CORRECTION**", "="*40,]
    instructions, response_format = [], ["   - **Avis Général:** [Un seul mot: Excellente, Bonne, Médiocre, ou Invalide].", "   - **Analyse Point par Point:**"]
    if question_type == "FITB":
        instructions.append("**1. Validation du Format (Critique) :** La question contient-elle un blanc visible (comme `______`) ? Si NON, signalez-le comme ERREUR CRITIQUE.")
        instructions.append("\n**2. Analyse Détaillée de la Qualité :**")
        response_format.append("     - **Validation Format :** [Votre évaluation. Ex: 'OK' ou 'ERREUR CRITIQUE: Aucun blanc trouvé.']")
    else: instructions.append("\n**1. Analyse Détaillée de la Qualité :**")
    instructions.extend(["   - **Exactitude :** La réponse attendue est-elle factuellement correcte selon le contexte ?", "   - **Clarté :** La question est-elle sans ambiguïté ?", "   - **Qualité des Options :** Les mauvais choix (distracteurs) sont-ils plausibles mais clairement incorrects ?", "   - **Pertinence :** La question porte-t-elle sur un point important du texte ?",])
    response_header_number = 3 if question_type == "FITB" else 2
    instructions.append(f"\n**{response_header_number}. Format de Réponse Exigé (Structure Impérative) :**")
    response_format.extend(["     - **Exactitude :** [Votre évaluation]", "     - **Clarté :** [Votre évaluation]", "     - **Qualité Options :** [Votre évaluation]", "\n   - **Suggestions d'Amélioration :**", "     *Si la question originale est 'Excellente', écrivez simplement 'Aucune amélioration nécessaire.'.*", "     *SINON, fournissez OBLIGATOIREMENT une version corrigée complète (Question, Options, Réponse, Justification).*"])
    full_prompt = "\n".join(prompt_parts_base + instructions + response_format)
    try:
        chat_completion = groq_client.chat.completions.create(messages=[{"role": "user", "content": full_prompt}], model="llama3-70b-8192", temperature=0.0)
        return chat_completion.choices[0].message.content
    except Exception as e: return f"Erreur lors de l'appel à l'API Groq : {e}"

def chunk_text_by_paragraph(text):
    if not text: return []
    return [p.strip() for p in re.split(r'\n\s*\n', text.strip()) if p.strip()]

def display_highlighted_context(full_text, current_chunk):
    highlighted_text = full_text.replace(current_chunk, f"<mark>{current_chunk}</mark>").replace('\n', '<br>')
    st.markdown(f"<h4>Texte Complet (Source surlignée)</h4><div style='border:1px solid #ddd; padding:10px; border-radius:5px; max-height:200px; overflow-y:auto;'>{highlighted_text}</div>", unsafe_allow_html=True)

# --- SESSION STATE ---
for key in ['full_text', 'current_context', 'last_selected']:
    if key not in st.session_state: st.session_state[key] = ""
if 'question_type' not in st.session_state: st.session_state.question_type = "QCM"
if 'chunks' not in st.session_state: st.session_state.chunks = []
if 'generated_data' not in st.session_state: st.session_state.generated_data = None
if 'verification_response' not in st.session_state: st.session_state.verification_response = None
if 'current_chunk_index' not in st.session_state: st.session_state.current_chunk_index = -1
if 'question_saved_status' not in st.session_state: st.session_state.question_saved_status = {}

# --- INTERFACE ---
st.title("📝 Générateur de Questions Itératif")
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("1. Source du Texte")
    db_texts = load_texts()
    text_options = {f"{t.get('niveau', 'N/A')} - {t['texte'][:40].replace(chr(10), ' ')}...": t['texte'] for t in db_texts}
    options_list = ["-- Entrée Manuelle --"] + list(text_options.keys())
    
    selected_label = st.selectbox("Choisir un texte ou entrer manuellement", options_list, key="text_selector")
    if st.session_state.get('last_selected') != selected_label:
        st.session_state.last_selected = selected_label
        st.session_state.full_text = text_options.get(selected_label, "")
        for key in ['chunks', 'generated_data', 'current_context', 'verification_response', 'question_saved_status']: 
            st.session_state[key] = {} if key == 'question_saved_status' else None
        st.session_state.current_chunk_index = -1
        st.rerun()

    text_input = st.text_area("Texte à utiliser :", value=st.session_state.full_text, height=250, key="text_input_area")
    if text_input != st.session_state.full_text:
        st.session_state.full_text = text_input

    st.subheader("2. Configuration")
    question_type_options = ('QCM', 'FITB')
    old_q_type = st.session_state.question_type
    q_type_index = 1 if old_q_type == "FITB" else 0
    new_q_type = st.radio("Type de question :", question_type_options, index=q_type_index, horizontal=True)
    if new_q_type != old_q_type:
        st.session_state.question_type = new_q_type
        st.session_state.generated_data = None
        st.session_state.verification_response = None
        st.rerun()

    if st.button("🚀 Préparer le Texte", use_container_width=True, disabled=not st.session_state.full_text.strip()):
        st.session_state.chunks = chunk_text_by_paragraph(st.session_state.full_text)
        st.session_state.current_chunk_index = -1
        st.session_state.generated_data = None
        if st.session_state.chunks: st.success(f"{len(st.session_state.chunks)} segments trouvés.")
        else: st.warning("Aucun segment trouvé.")
        st.rerun()

with col2:
    st.subheader("3. Génération & Résultats")
    if not st.session_state.chunks: st.info("⬅️ Préparez un texte pour commencer.")
    else:
        total = len(st.session_state.chunks)
        is_last = st.session_state.current_chunk_index >= total - 1
        
        if st.button("➡️ Générer la Question Suivante", type="primary", use_container_width=True, disabled=is_last):
            st.session_state.current_chunk_index += 1
            idx = st.session_state.current_chunk_index
            st.session_state.current_context = st.session_state.chunks[idx]
            st.session_state.verification_response = None
            endpoint = QCM_ENDPOINT if st.session_state.question_type == "QCM" else FITB_ENDPOINT
            with st.spinner("Génération..."):
                st.session_state.generated_data = call_flask_api(endpoint, st.session_state.current_context)
            st.rerun()

        st.progress((st.session_state.current_chunk_index + 1) / total if total > 0 else 0)

        if st.session_state.generated_data:
            st.divider()
            data = st.session_state.generated_data
            if "error" in data:
                st.error(f"Erreur API: {data.get('error')}")
                if 'raw_output' in data: st.text_area("Sortie brute sur erreur:", value=str(data.get('raw_output')), height=150, disabled=True)
            elif data.get("question") and not data["question"].startswith("Could not parse"):
                st.markdown(f"**Source:** *{st.session_state.current_context[:100].replace(chr(10), ' ')}...*")
                st.markdown(f"**Question :** {data.get('question', 'N/A')}")
                opt_cols = st.columns(2)
                opt_cols[0].markdown(f"**A)** {data.get('A', 'N/A')}")
                opt_cols[0].markdown(f"**B)** {data.get('B', 'N/A')}")
                opt_cols[1].markdown(f"**C)** {data.get('C', 'N/A')}")
                opt_cols[1].markdown(f"**D)** {data.get('D', 'N/A')}")
                st.markdown(f"**Réponse correcte :** <span style='color:green; font-weight:bold;'>{data.get('reponse', 'N/A')}</span>", unsafe_allow_html=True)
                
                idx = st.session_state.current_chunk_index
                
                # --- ### CORRECTION DÉFINITIVE DU BUG ### ---
                # On crée une clé unique en combinant l'index ET le type de question
                save_status_key = (idx, st.session_state.question_type)
                
                if not st.session_state.question_saved_status.get(save_status_key, False):
                    if st.button("💾 Enregistrer dans la BDD", use_container_width=True, key=f"save_{idx}_{st.session_state.question_type}"):
                        save_question(data, st.session_state.current_context, st.session_state.question_type)
                        # On met à jour le statut en utilisant la clé unique
                        st.session_state.question_saved_status[save_status_key] = True
                        st.success("Question enregistrée !")
                        st.rerun()
                else: 
                    st.info("✔️ Cette question a déjà été enregistrée.")
                
                if groq_client:
                    if st.button("🔍 Analyser et Corriger avec l'IA", use_container_width=True, key=f"verify_{idx}"):
                        with st.spinner("Analyse par l'IA..."):
                            st.session_state.verification_response = call_groq_for_verification(st.session_state.current_context, data, st.session_state.question_type)
                        st.rerun()
                
                if 'raw_output' in data:
                    with st.expander("Afficher la sortie brute du modèle"):
                        st.text_area("Sortie brute:", value=str(data['raw_output']), height=150, disabled=True, key=f"raw_{idx}")
            else:
                st.warning("La sortie du modèle n'a pas pu être structurée.")
                st.json(data)

if st.session_state.verification_response:
    st.divider()
    st.subheader("🕵️‍♂️ Analyse de l'IA")
    st.markdown(st.session_state.verification_response)

if st.session_state.full_text and st.session_state.current_context:
    st.divider()
    display_highlighted_context(st.session_state.full_text, st.session_state.current_context)

st.sidebar.divider()
if st.sidebar.button("🧹 Effacer & Recommencer", use_container_width=True):
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()