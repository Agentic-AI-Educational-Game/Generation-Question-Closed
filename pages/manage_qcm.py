import streamlit as st
from db_utils import load_questions, update_question, delete_question, get_mongo_client

st.set_page_config(page_title="Gérer les QCM", layout="wide")
st.title("❓ Gérer les Questions à Choix Multiples (QCM)")
get_mongo_client()

COLLECTION_NAME = "qcm_questions"
all_questions = load_questions(COLLECTION_NAME)

if not all_questions:
    st.info("Aucun QCM trouvé. Générez-en depuis la page principale.")
else:
    for q in all_questions:
        q_id_str = str(q["_id"])
        with st.expander(f"Question: {q['question'][:80].replace(chr(10), ' ')}..."):

            # ### CORRECTION : On définit les colonnes AVANT le formulaire ###
            update_col, delete_col = st.columns([4, 1])

            # La colonne de mise à jour contient le formulaire
            with update_col:
                with st.form(f"form_{q_id_str}"):
                    new_q_text = st.text_area("Question", value=q['question'], key=f"q_{q_id_str}")
                    c1, c2 = st.columns(2)
                    new_a = c1.text_input("Option A", value=q.get('option_A', ''), key=f"a_{q_id_str}")
                    new_b = c2.text_input("Option B", value=q.get('option_B', ''), key=f"b_{q_id_str}")
                    new_c = c1.text_input("Option C", value=q.get('option_C', ''), key=f"c_{q_id_str}")
                    new_d = c2.text_input("Option D", value=q.get('option_D', ''), key=f"d_{q_id_str}")
                    
                    index = "ABCD".find(q.get('correct_option', 'A'))
                    new_ans = st.radio("Bonne réponse", ["A", "B", "C", "D"], index=index if index != -1 else 0, key=f"ans_{q_id_str}", horizontal=True)
                    
                    if st.form_submit_button("Enregistrer", use_container_width=True):
                        updated_data = {"question": new_q_text, "option_A": new_a, "option_B": new_b, "option_C": new_c, "option_D": new_d, "correct_option": new_ans}
                        update_question(COLLECTION_NAME, q_id_str, updated_data)
                        st.success("Question mise à jour !")
                        st.rerun()
            
            # La colonne de suppression contient le bouton, en dehors du formulaire
            with delete_col:
                st.write("") # Espace pour l'alignement visuel
                st.write("")
                if st.button("🗑️ Supprimer", key=f"del_{q_id_str}", type="secondary", use_container_width=True):
                    delete_question(COLLECTION_NAME, q_id_str)
                    st.success("Question supprimée !")
                    st.rerun()