from pymongo import MongoClient
import datetime

# --- CONFIGURATION ---
# URI pour une connexion locale. Pas besoin de secrets ici.
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "projet_lsi"

# --- DONNÉES D'EXEMPLE ---

# Textes longs avec des paragraphes distincts
SAMPLE_TEXTS = [
    {
        "texte": (
            "Le cycle de l'eau, également connu sous le nom de cycle hydrologique, est le processus par lequel l'eau circule entre l'océan, l'atmosphère et la terre. Ce cycle est essentiel à la vie sur Terre.\n\n"
            "La première étape majeure est l'évaporation. Le soleil chauffe l'eau des océans, des lacs et des rivières, la transformant en vapeur d'eau qui monte dans l'atmosphère. Les plantes contribuent également à ce processus par la transpiration.\n\n"
            "Ensuite vient la condensation. En altitude, la vapeur d'eau se refroidit et se transforme en de minuscules gouttelettes d'eau ou des cristaux de glace, formant ainsi les nuages.\n\n"
            "La dernière étape est la précipitation. Lorsque les gouttelettes d'eau dans les nuages deviennent trop lourdes, elles tombent sur la Terre sous forme de pluie, de neige, de grêle ou de grésil. Une partie de cette eau s'infiltre dans le sol, tandis que l'autre ruisselle vers les cours d'eau pour retourner à l'océan."
        ),
        "niveau": "CM1",
        "difficulty": "moyenne"
    },
    {
        "texte": (
            "La photosynthèse est le processus biochimique fondamental qui permet aux plantes vertes, aux algues et à certaines bactéries de convertir l'énergie lumineuse du soleil en énergie chimique. Cette énergie est stockée sous forme de glucides, comme le glucose.\n\n"
            "Pour réaliser la photosynthèse, les plantes ont besoin de trois éléments principaux : la lumière du soleil, l'eau (absorbée par les racines) et le dioxyde de carbone (CO2) (absorbé par les feuilles). Le processus se déroule dans des organites cellulaires appelés chloroplastes, qui contiennent un pigment vert, la chlorophylle.\n\n"
            "L'un des sous-produits les plus importants de la photosynthèse est l'oxygène (O2). Ce gaz, indispensable à la respiration de la plupart des êtres vivants, y compris les humains, est libéré dans l'atmosphère."
        ),
        "niveau": "6ème",
        "difficulty": "moyenne"
    }
]

# Exemples de questions QCM
SAMPLE_QCM = [
    {
        "question": "Quelle est la première étape majeure du cycle de l'eau mentionnée dans le texte ?",
        "option_A": "La condensation",
        "option_B": "La précipitation",
        "option_C": "L'évaporation",
        "option_D": "L'infiltration",
        "correct_option": "C",
        "source_text": "La première étape majeure est l'évaporation. Le soleil chauffe l'eau des océans, des lacs et des rivières, la transformant en vapeur d'eau qui monte dans l'atmosphère.",
        "created_at": datetime.datetime.utcnow()
    },
    {
        "question": "Où se déroule principalement le processus de la photosynthèse dans une plante ?",
        "option_A": "Dans les racines",
        "option_B": "Dans les chloroplastes des cellules",
        "option_C": "Dans les fleurs",
        "option_D": "Dans la sève",
        "correct_option": "B",
        "source_text": "Le processus se déroule dans des organites cellulaires appelés chloroplastes, qui contiennent un pigment vert, la chlorophylle.",
        "created_at": datetime.datetime.utcnow()
    },
    {
        "question": "Quel gaz est un sous-produit essentiel de la photosynthèse, libéré dans l'atmosphère ?",
        "option_A": "Le dioxyde de carbone",
        "option_B": "L'azote",
        "option_C": "L'hydrogène",
        "option_D": "L'oxygène",
        "correct_option": "D",
        "source_text": "L'un des sous-produits les plus importants de la photosynthèse est l'oxygène (O2). Ce gaz, indispensable à la respiration de la plupart des êtres vivants, y compris les humains, est libéré dans l'atmosphère.",
        "created_at": datetime.datetime.utcnow()
    }
]

# Exemples de questions FITB (Texte à trous)
SAMPLE_FITB = [
    {
        "question": "Le processus par lequel la vapeur d'eau se refroidit et forme des nuages s'appelle la ______.",
        "option_A": "transpiration",
        "option_B": "condensation",
        "option_C": "précipitation",
        "option_D": "évaporation",
        "correct_option": "B",
        "source_text": "Ensuite vient la condensation. En altitude, la vapeur d'eau se refroidit et se transforme en de minuscules gouttelettes d'eau ou des cristaux de glace, formant ainsi les nuages.",
        "created_at": datetime.datetime.utcnow()
    },
    {
        "question": "La photosynthèse convertit l'énergie lumineuse du soleil en énergie ______.",
        "option_A": "thermique",
        "option_B": "mécanique",
        "option_C": "nucléaire",
        "option_D": "chimique",
        "correct_option": "D",
        "source_text": "La photosynthèse est le processus biochimique fondamental qui permet aux plantes vertes, aux algues et à certaines bactéries de convertir l'énergie lumineuse du soleil en énergie chimique.",
        "created_at": datetime.datetime.utcnow()
    },
    {
        "question": "Le pigment vert contenu dans les chloroplastes et qui capte la lumière est la ______.",
        "option_A": "chlorophylle",
        "option_B": "carotène",
        "option_C": "mélanine",
        "option_D": "xanthophylle",
        "correct_option": "A",
        "source_text": "...les chloroplastes, qui contiennent un pigment vert, la chlorophylle.",
        "created_at": datetime.datetime.utcnow()
    }
]


# --- SCRIPT D'INSERTION ---

def populate_database():
    try:
        print("Connexion à la base de données locale MongoDB...")
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]

        # Vider les collections pour un départ propre (uniquement pour le développement)
        print("Nettoyage des collections existantes...")
        db.textes.delete_many({})
        db.qcm_questions.delete_many({})
        db.fitb_questions.delete_many({})

        # Insertion des textes
        if SAMPLE_TEXTS:
            print(f"Insertion de {len(SAMPLE_TEXTS)} textes...")
            db.textes.insert_many(SAMPLE_TEXTS)
            print("Textes insérés avec succès.")
        
        # Insertion des QCM
        if SAMPLE_QCM:
            print(f"Insertion de {len(SAMPLE_QCM)} questions QCM...")
            db.qcm_questions.insert_many(SAMPLE_QCM)
            print("QCM insérés avec succès.")
            
        # Insertion des FITB
        if SAMPLE_FITB:
            print(f"Insertion de {len(SAMPLE_FITB)} questions FITB...")
            db.fitb_questions.insert_many(SAMPLE_FITB)
            print("FITB insérés avec succès.")
            
        print("\n=== Base de données initialisée avec succès ! ===")

    except Exception as e:
        print(f"\nERREUR : Une erreur est survenue lors de l'initialisation de la base de données.")
        print(f"Détails : {e}")
        print("Veuillez vous assurer que le service MongoDB est bien en cours d'exécution (vérifiez services.msc sur Windows).")
    
    finally:
        if 'client' in locals():
            client.close()
            print("\nConnexion à la base de données fermée.")

if __name__ == "__main__":
    populate_database()