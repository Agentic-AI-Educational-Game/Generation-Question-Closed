import streamlit as st
from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime

DB_NAME = "projet_lsi"

@st.cache_resource
def get_mongo_client():
    try:
        uri = st.secrets["mongo"]["uri"]
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        return client
    except Exception as e:
        st.sidebar.error(f"Erreur de connexion à MongoDB : {e}")
        return None

def get_db():
    client = get_mongo_client()
    if client is None: return None
    return client[DB_NAME]

def load_texts():
    db = get_db()
    if db is None: return []
    return list(db.textes.find())

def add_text(text_content, level, difficulty):
    db = get_db()
    if db is None: return None
    doc = {"texte": text_content, "niveau": level, "difficulty": difficulty, "created_at": datetime.datetime.utcnow()}
    return db.textes.insert_one(doc).inserted_id

def update_text(text_id, new_content, new_level, new_difficulty):
    db = get_db()
    if db is None: return None
    db.textes.update_one({"_id": ObjectId(text_id)}, {"$set": {"texte": new_content, "niveau": new_level, "difficulty": new_difficulty}})

def delete_text(text_id):
    db = get_db()
    if db is None: return None
    db.textes.delete_one({"_id": ObjectId(text_id)})

def load_questions(collection_name):
    db = get_db()
    if db is None: return []
    return list(db[collection_name].find())

def save_question(question_data, context, question_type):
    db = get_db()
    if db is None: raise ConnectionError("Connexion à la BDD échouée.")
    collection_name = "qcm_questions" if question_type == "QCM" else "fitb_questions"
    doc = {"question": question_data.get("question"), "option_A": question_data.get("A"), "option_B": question_data.get("B"), "option_C": question_data.get("C"), "option_D": question_data.get("D"), "correct_option": question_data.get("reponse"), "source_text": context, "created_at": datetime.datetime.utcnow()}
    db[collection_name].insert_one(doc)

def update_question(collection_name, q_id, new_data):
    db = get_db()
    if db is None: return None
    db[collection_name].update_one({"_id": ObjectId(q_id)}, {"$set": new_data})
    
def delete_question(collection_name, q_id):
    db = get_db()
    if db is None: return None
    db[collection_name].delete_one({"_id": ObjectId(q_id)})