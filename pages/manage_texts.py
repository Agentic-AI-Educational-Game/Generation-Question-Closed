import streamlit as st
from db_utils import load_texts, add_text, update_text, delete_text, get_mongo_client

st.set_page_config(page_title="Gérer les Textes", layout="wide")
st.title("📚 Gérer la Bibliothèque de Textes")
get_mongo_client()

with st.expander("➕ Ajouter un nouveau texte"):
    with st.form("new_text_form", clear_on_submit=True):
        new_content = st.text_area("Contenu du texte", height=150)
        col1, col2 = st.columns(2)
        new_level = col1.text_input("Niveau (ex: CE1)")
        new_difficulty = col2.text_input("Difficulté (ex: facile)")
        if st.form_submit_button("Sauvegarder le texte") and new_content:
            add_text(new_content, new_level, new_difficulty)
            st.success("Texte ajouté !")
            st.rerun()

st.divider()
st.subheader("Textes Existants")

for text in load_texts():
    text_id_str = str(text["_id"])
    with st.expander(f"Niveau: {text.get('niveau', 'N/A')} | Texte: {text['texte'][:50].replace(chr(10), ' ')}..."):
        
        # ### CORRECTION : On définit les colonnes AVANT le formulaire ###
        update_col, delete_col = st.columns([4, 1])

        # La colonne de mise à jour contient le formulaire
        with update_col:
            with st.form(f"update_form_{text_id_str}"):
                updated_content = st.text_area("Contenu", value=text['texte'], key=f"content_{text_id_str}", height=150)
                ucol1, ucol2 = st.columns(2)
                updated_level = ucol1.text_input("Niveau", value=text.get('niveau', ''), key=f"level_{text_id_str}")
                updated_difficulty = ucol2.text_input("Difficulté", value=text.get('difficulty', ''), key=f"difficulty_{text_id_str}")
                
                if st.form_submit_button("Enregistrer les modifications", use_container_width=True):
                    update_text(text_id_str, updated_content, updated_level, updated_difficulty)
                    st.success("Texte mis à jour !")
                    st.rerun()
        
        # La colonne de suppression contient le bouton, en dehors du formulaire
        with delete_col:
            st.write("") # Espace pour l'alignement visuel
            st.write("")
            if st.button("🗑️ Supprimer", key=f"delete_{text_id_str}", type="secondary", use_container_width=True):
                delete_text(text_id_str)
                st.success("Texte supprimé !")
                st.rerun()