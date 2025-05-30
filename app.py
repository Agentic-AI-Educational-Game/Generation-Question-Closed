# app.py
import os
from huggingface_hub import hf_hub_download
from flask import Flask, jsonify, request
from llama_cpp import Llama
import re
import traceback # Import for better error logging

app = Flask(__name__)

MODEL_LOADED = False
LLM_INSTANCE = None
GGUF_PATH = None

# --- Configuration for the new QCM+FITB model ---
NEW_MODEL_REPO_ID = "goalaphx/outputs_qcm_then_fitb"
NEW_MODEL_FILENAME = "qwen2_5_1.5B_instruct_finetuned_fr_qcm_fitb.q8_0.gguf"
# --- End Configuration ---

def load_model():
    global MODEL_LOADED, LLM_INSTANCE, GGUF_PATH
    if MODEL_LOADED:
        print("Model already loaded.")
        return

    print("Checking if QCM+FITB model is already downloaded...")
    try:
        target_dir = os.path.expanduser(f"./models_{NEW_MODEL_REPO_ID.replace('/', '_')}")
        os.makedirs(target_dir, exist_ok=True)
        model_path = os.path.join(target_dir, NEW_MODEL_FILENAME)

        if os.path.exists(model_path):
            GGUF_PATH = model_path
            print(f"QCM+FITB Model already exists at: {GGUF_PATH}")
        else:
            print(f"QCM+FITB Model not found at {model_path}, downloading from {NEW_MODEL_REPO_ID}...")
            GGUF_PATH = hf_hub_download(
                repo_id=NEW_MODEL_REPO_ID,
                filename=NEW_MODEL_FILENAME,
                local_dir=target_dir,
                local_dir_use_symlinks=False
            )
            print(f"QCM+FITB Model downloaded to: {GGUF_PATH}")

        if GGUF_PATH and os.path.exists(GGUF_PATH):
            print(f"Loading Llama instance from: {GGUF_PATH}")
            LLM_INSTANCE = Llama(
                model_path=GGUF_PATH,
                n_ctx=2048,
                n_gpu_layers=-1,
                n_threads=max(1, os.cpu_count() // 2),
                chat_format="chatml",
                verbose=True
            )
            MODEL_LOADED = True
            print("QCM+FITB Model loaded successfully using llama.cpp.")
        else:
            print(f"GGUF_PATH is not valid or model download failed: {GGUF_PATH}")
            MODEL_LOADED = False

    except Exception as e:
        print(f"Error loading QCM+FITB model: {e}")
        traceback.print_exc()
        MODEL_LOADED = False

@app.route('/')
def home():
    status = "Model Loaded" if MODEL_LOADED else "Model NOT Loaded (or loading failed)"
    return f"QCM and FITB Generation API. Status: {status}. Use /generate_qcm or /generate_fitb POST endpoints."

def parse_generated_output(full_response):
    """
    Helper function to parse QCM/FITB output.
    Returns a dictionary of parsed components.
    """
    question_match = re.search(r"Question\s*:\s*(.+?)(?=\n\s*Options:|\n\s*[Aa]\.)", full_response, re.DOTALL | re.IGNORECASE)
    options_block_match = re.search(r"Options\s*:\s*\n(.*?)(?=\n\s*Réponse:)", full_response, re.DOTALL | re.IGNORECASE)

    option_a, option_b, option_c, option_d = None, None, None, None
    options_text_for_parsing = ""
    if options_block_match:
        options_text_for_parsing = options_block_match.group(1).strip()
    elif question_match: # If "Options:" header is missing, try to parse from after question
        start_options_search_index = question_match.end()
        # Look for a plausible start of options (e.g., A), B), etc.)
        # This part might need more robust regex if formats vary widely
        potential_options_block = full_response[start_options_search_index:]
        # Crude check: if it looks like options, use it.
        if re.search(r"^[Aa]\s*[.)]", potential_options_block.strip(), re.MULTILINE | re.IGNORECASE):
             options_text_for_parsing = potential_options_block.split("Réponse:")[0].strip()


    if options_text_for_parsing:
        # More robust option parsing: allow for variations in list format and ensure they start at the beginning of a line.
        # Ensure we capture until the next option or end of string.
        a_match = re.search(r"^[Aa]\s*[.)]?\s*(.+?)(?=\n\s*[Bb]\s*[.)]?|\Z)", options_text_for_parsing, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        b_match = re.search(r"^[Bb]\s*[.)]?\s*(.+?)(?=\n\s*[Cc]\s*[.)]?|\Z)", options_text_for_parsing, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        c_match = re.search(r"^[Cc]\s*[.)]?\s*(.+?)(?=\n\s*[Dd]\s*[.)]?|\Z)", options_text_for_parsing, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        d_match = re.search(r"^[Dd]\s*[.)]?\s*(.+?)(?=\Z|\n\s*Réponse:)", options_text_for_parsing, re.MULTILINE | re.DOTALL | re.IGNORECASE) # Match D to end or before Réponse

        option_a = a_match.group(1).strip() if a_match else None
        option_b = b_match.group(1).strip() if b_match else None
        option_c = c_match.group(1).strip() if c_match else None
        option_d = d_match.group(1).strip() if d_match else None

    answer_match = re.search(r"Réponse\s*:\s*([A-Da-d])", full_response, re.IGNORECASE)

    return {
        "question": question_match.group(1).strip() if question_match else "Could not parse question.",
        "A": option_a if option_a else "Could not parse option A.",
        "B": option_b if option_b else "Could not parse option B.",
        "C": option_c if option_c else "Could not parse option C.",
        "D": option_d if option_d else "Could not parse option D.",
        "reponse": answer_match.group(1).upper().strip() if answer_match else "Could not parse answer.",
        "raw_output": full_response
    }


@app.route('/generate_qcm', methods=['POST'])
def generate_qcm():
    global MODEL_LOADED, LLM_INSTANCE
    if not MODEL_LOADED:
        print("Attempting to load model for QCM request...")
        load_model()
        if not MODEL_LOADED:
            return jsonify({"error": "Model could not be loaded. Check server logs."}), 500
    if LLM_INSTANCE is None:
        return jsonify({"error": "LLM_INSTANCE is None, model loading issue."}), 500

    data = request.get_json(force=True)
    texte = data.get("texte", "").strip()
    if not texte:
        return jsonify({"error": "Input 'texte' is missing or empty."}), 400

    prompt_qcm = f"""<|im_start|>system
Tu es un assistant expert en génération de questions à choix multiples (QCM) en français, basées sur un texte fourni.
Le format de sortie doit être :
Question: [Ta question]
Options:
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]
Réponse: [Lettre de la bonne réponse, e.g., A]<|im_end|>
<|im_start|>user
Texte: {texte}

Génère un QCM à partir de ce texte.<|im_end|>
<|im_start|>assistant
"""
    print(f"\n--- QCM Prompt for Llama.cpp ---\n{prompt_qcm}\n---------------------------------")
    full_response = ""

    try:
        output_stream = LLM_INSTANCE(
            prompt_qcm,
            max_tokens=350, # Increased slightly for potentially longer options/questions
            temperature=0.5,
            top_p=0.9,
            stop=["<|im_end|>", "assistant"], # Added "assistant" as a potential stop
            stream=True
        )

        print("Streaming QCM response: ", end="")
        for chunk in output_stream:
            token_text = chunk["choices"][0]["text"]
            full_response += token_text
            print(token_text, end="", flush=True)
        print("\n--- End of QCM Stream ---")

        full_response = full_response.strip()
        print(f"Raw QCM full_response from model:\n{full_response}")

        result = parse_generated_output(full_response)

    except Exception as e:
        print(f"Error during QCM generation or parsing: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error during QCM generation: {str(e)}",
                        "raw_output_on_error": full_response}), 500

    response = jsonify(result)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response


@app.route('/generate_fitb', methods=['POST'])
def generate_fitb():
    global MODEL_LOADED, LLM_INSTANCE
    if not MODEL_LOADED:
        print("Attempting to load model for FITB request...")
        load_model()
        if not MODEL_LOADED:
            return jsonify({"error": "Model could not be loaded. Check server logs."}), 500
    if LLM_INSTANCE is None:
        return jsonify({"error": "LLM_INSTANCE is None, model loading issue."}), 500

    data = request.get_json(force=True)
    texte = data.get("texte", "").strip()
    if not texte:
        return jsonify({"error": "Input 'texte' is missing or empty."}), 400

    prompt_fitb = f"""<|im_start|>system
Tu es un assistant expert en génération de questions de type 'compléter la phrase' (fill-in-the-blank) en français, basées sur un texte fourni, avec quatre options de réponse et la bonne réponse indiquée.
Le format de sortie doit être :
Question: [Ta question avec un ______ pour le blanc]
Options:
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]
Réponse: [Lettre de la bonne réponse, e.g., B]<|im_end|>
<|im_start|>user
Texte: {texte}

Génère une question 'compléter la phrase' avec des options (A, B, C, D) et la réponse à partir de ce texte.<|im_end|>
<|im_start|>assistant
"""
    print(f"\n--- FITB Prompt for Llama.cpp ---\n{prompt_fitb}\n---------------------------------")
    full_response = ""

    try:
        output_stream = LLM_INSTANCE(
            prompt_fitb,
            max_tokens=350, # Increased slightly
            temperature=0.5,
            top_p=0.9,
            stop=["<|im_end|>", "assistant"], # Added "assistant" as a potential stop
            stream=True
        )

        print("Streaming FITB response: ", end="")
        for chunk in output_stream:
            token_text = chunk["choices"][0]["text"]
            full_response += token_text
            print(token_text, end="", flush=True)
        print("\n--- End of FITB Stream ---")

        full_response = full_response.strip()
        print(f"Raw FITB full_response from model:\n{full_response}")

        result = parse_generated_output(full_response)

    except Exception as e:
        print(f"Error during FITB generation or parsing: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error during FITB generation: {str(e)}",
                        "raw_output_on_error": full_response}), 500

    response = jsonify(result)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response

if __name__ == '__main__':
    print("Application starting...")
    if not MODEL_LOADED:
        load_model()

    if MODEL_LOADED:
        print(f"Flask app starting with model loaded from {GGUF_PATH}")
    else:
        print("Flask app starting WITHOUT model pre-loaded. Will attempt load on first request.")
        print("If model loading fails repeatedly, check paths, model file, and llama.cpp setup.")

    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)