import streamlit as st
import requests # To make HTTP requests to your Flask API
import json # To handle JSON data

# --- Configuration ---
FLASK_API_BASE_URL = "http://localhost:5000"  # Adjust if your Flask app runs elsewhere
QCM_ENDPOINT = f"{FLASK_API_BASE_URL}/generate_qcm"
FITB_ENDPOINT = f"{FLASK_API_BASE_URL}/generate_fitb"

# --- Helper Function to Call Flask API ---
def call_flask_api(endpoint_url, text_input):
    """Calls the Flask API and returns the JSON response or an error message."""
    payload = {"texte": text_input}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(endpoint_url, data=json.dumps(payload), headers=headers, timeout=120) # Increased timeout
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Request Error: {e}")
        # Try to get more details if it's an HTTPError with a JSON body
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                st.error(f"API Error Details: {error_details}")
                return {"error": str(e), "details": error_details, "raw_output": "API Error"}
            except json.JSONDecodeError:
                st.error(f"API Error Content (not JSON): {e.response.text}")
                return {"error": str(e), "raw_output": e.response.text}
        return {"error": str(e), "raw_output": "API Connection Error"}
    except json.JSONDecodeError:
        st.error("Error decoding JSON response from API. The API might not be returning valid JSON.")
        return {"error": "JSON Decode Error", "raw_output": "Invalid JSON from API"}


# --- Streamlit App Layout ---
st.set_page_config(page_title="Générateur de Questions", layout="wide")

st.title("📝 Générateur de Questions (QCM & Texte à Trous)")
st.markdown("Utilisez cette interface pour générer des questions à partir d'un texte fourni, en utilisant le modèle fine-tuné.")

# --- Session State to keep track of inputs and outputs ---
if 'text_input' not in st.session_state:
    st.session_state.text_input = ""
if 'question_type' not in st.session_state:
    st.session_state.question_type = "QCM"
if 'generated_data' not in st.session_state:
    st.session_state.generated_data = None
if 'raw_model_output' not in st.session_state:
    st.session_state.raw_model_output = ""


# --- Input Area ---
st.subheader("1. Fournissez votre texte :")
text_area_input = st.text_area("Collez ou écrivez votre texte ici :",
                               value=st.session_state.text_input,
                               height=200,
                               key="text_input_area")
st.session_state.text_input = text_area_input # Update session state on change

st.subheader("2. Choisissez le type de question :")
question_type_selection = st.radio(
    "Quel type de question souhaitez-vous générer ?",
    ('QCM (Question à Choix Multiples)', 'FITB (Texte à Trous / Fill-in-the-Blank)'),
    index=0 if st.session_state.question_type == "QCM" else 1,
    key="question_type_radio"
)
# Map selection to a simpler key for API call
if question_type_selection == 'QCM (Question à Choix Multiples)':
    st.session_state.question_type = "QCM"
else:
    st.session_state.question_type = "FITB"


# --- Generate Button ---
if st.button("🚀 Générer la question", type="primary", use_container_width=True):
    if not st.session_state.text_input.strip():
        st.warning("Veuillez entrer un texte avant de générer une question.")
    else:
        endpoint_to_call = QCM_ENDPOINT if st.session_state.question_type == "QCM" else FITB_ENDPOINT
        with st.spinner(f"Génération de la question {st.session_state.question_type} en cours... Veuillez patienter."):
            api_response = call_flask_api(endpoint_to_call, st.session_state.text_input)
            st.session_state.generated_data = api_response
            if api_response and "raw_output" in api_response:
                st.session_state.raw_model_output = api_response.get("raw_output", "Aucune sortie brute disponible.")
            else:
                st.session_state.raw_model_output = "Erreur lors de la récupération de la sortie brute."
            st.rerun() # Rerun to update the display with new data

# --- Display Area ---
if st.session_state.generated_data:
    st.divider()
    st.subheader(f"Résultat de la Génération ({st.session_state.question_type})")

    data = st.session_state.generated_data

    if "error" in data and data["error"] != "API Connection Error": # If there was an API error but we got some response
        if "details" in data and "raw_output_on_error" in data["details"]:
             st.error(f"Erreur de l'API: {data.get('details', {}).get('error', 'Erreur inconnue')}")
             st.text_area("Sortie brute de l'API (sur erreur):", value=data["details"]["raw_output_on_error"], height=150, disabled=True)
        elif "raw_output" in data and data["raw_output"] not in ["API Connection Error", "API Error"]:
            st.error(f"Erreur de l'API: {data.get('error', 'Erreur inconnue')}")
            st.text_area("Sortie brute de l'API (sur erreur):", value=data["raw_output"], height=150, disabled=True)
        # else, the error was already displayed by call_flask_api

    elif data.get("question") and not data["question"].startswith("Could not parse"):
        st.markdown(f"**Question :** {data.get('question', 'N/A')}")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**A)** {data.get('A', 'N/A')}")
            st.markdown(f"**B)** {data.get('B', 'N/A')}")
        with col2:
            st.markdown(f"**C)** {data.get('C', 'N/A')}")
            st.markdown(f"**D)** {data.get('D', 'N/A')}")

        st.markdown(f"**Réponse correcte :** <span style='color:green; font-weight:bold;'>{data.get('reponse', 'N/A')}</span>", unsafe_allow_html=True)
    elif "raw_output" in data and data["raw_output"] and data["raw_output"] not in ["API Connection Error", "API Error", "Aucune sortie brute disponible."]:
        st.warning("La génération a produit une sortie, mais elle n'a pas pu être structurée correctement. Vérifiez la sortie brute.")
    elif not ("error" in data and data["error"] == "API Connection Error"): # Avoid double error message
        st.error("Aucune question n'a pu être générée ou parsée. Vérifiez la sortie brute si disponible.")


    # Expander for Raw Model Output
    if st.session_state.raw_model_output:
        with st.expander("Afficher la sortie brute du modèle", expanded=False):
            st.text_area("", value=st.session_state.raw_model_output, height=200, disabled=True, key="raw_output_display")
else:
    st.info("Entrez un texte et cliquez sur 'Générer la question' pour voir les résultats ici.")

st.divider()
st.markdown("---")
st.markdown("Développé avec Streamlit & llama.cpp")

# Button to clear everything and start over
if st.button("Effacer et recommencer", use_container_width=True):
    st.session_state.text_input = ""
    st.session_state.question_type = "QCM" # Default back to QCM
    st.session_state.generated_data = None
    st.session_state.raw_model_output = ""
    # st.experimental_rerun() # For older streamlit versions
    st.rerun()