"""Constantes métier et paramètres globaux de l'application."""


import pytz

TZ       = pytz.timezone('Africa/Tunis')

SHEET_ID = "1ZK6VWg_gcCO70nt6DTyYogDeNeQUgovFmwWQufMVO-M"

URL_GOOGLE_SHEET = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?gid=0#gid=0"

# Classeurs externes "Classification des actions CR 2026" : un classeur par site, un onglet par
# installation à l'intérieur, colonnes Désignation | Observation | Code (T/S/E/D/O/R).
# Utilisés pour le rapport PDF par pilote ainsi que pour le suivi des actions.
CODIF_SHEET_ID_PAR_SITE = {
    "MEG": "1AF65P1sQPKM6JN7_r2mck-UrrZqz7tn5QmpnJD1iICA",
    "SGB": "1bD6LUxs_nGgamVsC9DAmGffScUo5wgMhxjvPBuBxzx0",
}

# Conservé par compatibilité (ancien classeur unique) — non utilisé si les IDs par site ci-dessus sont renseignés.
CODIF_SHEET_ID = "119hyynlCiIUzf-17iiSkcPnaEr2oCiFC"

SEUIL_EN_LIGNE_SECONDES = 90

PERIODICITE = {
    "Installations électriques": 6,
    "Equipements de levage":     12,
    "Sécurité incendie":         12,
    "Installations de gaz":      12,
    "Appareil pression de gaz":  12,
}

COULEURS_INS = {
    "Installations électriques": "#2a78d6",
    "Equipements de levage":     "#1baf7a",
    "Sécurité incendie":         "#e34948",
    "Installations de gaz":      "#eda100",
    "Appareil pression de gaz":  "#4a3aa7",
}

# Couleur d'accent par site, pour une identification visuelle rapide dans les badges,
# titres et graphes comparatifs (MEG = bleu, SGB = vert).
COULEUR_SITE = {
    "MEG": {"principale": "#2563EB", "claire": "#DBEAFE", "fonce": "#1E3A8A"},
    "SGB": {"principale": "#059669", "claire": "#D1FAE5", "fonce": "#065F46"},
}

# Code interne (CI) de chaque type d'installation — adapte librement les libellés
CI_CODES = {
    "Installations de gaz":       "B1",
    "Installations électriques":  "B2",
    "Equipements de levage":      "B3",
    "Appareil pression de gaz":   "A1",
    "Sécurité incendie":          "A2",
}

# Ordre d'affichage dans le tableau (reprend celui de ta capture)
ORDRE_CI = [
    "Installations de gaz",
    "Installations électriques",
    "Equipements de levage",
    "Appareil pression de gaz",
    "Sécurité incendie",
]

# Durée de visite en jours, par site et par installation.
# ⚠️ Cette donnée n'existe dans aucune feuille actuelle de ton Google Sheet :
# soit tu la fixes ici "en dur", soit (mieux) tu ajoutes une colonne "Nbr_jour"
# dans l'onglet Exigences et tu remplaces ce dict par une lecture de cette colonne.
NB_JOURS_VISITE = {
    "SGB": {"Installations de gaz": 1, "Installations électriques": 3, "Equipements de levage": 6,
            "Appareil pression de gaz": 1, "Sécurité incendie": 2},
    "MEG": {"Installations de gaz": 1, "Installations électriques": 3, "Equipements de levage": 6,
            "Appareil pression de gaz": 1, "Sécurité incendie": 1},
}

MOIS_FR = ["","Janvier","Février","Mars","Avril","Mai","Juin",
           "Juillet","Août","Septembre","Octobre","Novembre","Décembre"]

SOUS_EQUIPEMENTS = {
    "Installations électriques": [],
    "Equipements de levage": ["Transpalette","Table élévatrice","Potence","Pont roulant",
                               "Plateforme de travail","Nacelle","Gerbeur","Chariot élévateur","Palan électrique","Ascenseur"],
    "Sécurité incendie": [],
    "Installations de gaz": ["Industrielle","Chaudière"],
    "Appareil pression de gaz": []
}

LUCID_CARTOGRAPHIE_URL = "https://lucid.app/lucidspark/088f02a4-bdb7-4c79-8e28-64e05fc773c3/edit?beaconFlowId=69403DCAA7251095&invitationId=inv_16e69b3a-177f-4fb1-922e-fd6c28f294d5&page=0_0"

# Noms EXACTS des colonnes (Désignation | Observation | Code) pour chaque type d'installation,
# tels que mis à jour dans les classeurs de codification MEG et SGB (structure identique sur les
# deux sites, seul le nom de l'onglet change : "... - MEG" / "... - SGB").
# Format : (mots-clés identifiant le type d'installation à partir du nom de l'onglet,
#           nom exact colonne désignation, nom exact colonne observation, nom exact colonne code)
COLONNES_CODIF_PAR_INSTALLATION = [
    (["electrique"],           "Désignation", "Observation",                    "C"),
    (["levage"],                "Rapport",     "Organes examines NC",            "C"),
    (["pression"],               "Rapport",     "Points examines non conforme",   "C"),
    (["gaz"],                   "Rapport",     "Points examines non conforme",   "C"),
    (["incendie"],               "Local",       "Observation",                    "C"),
]

NATURE_PILOTE = {
    "T": ("Technique",      "Maintenance"),
    "S": ("Sécurité",       "HSE"),
    "E": ("Energétique",    "BT + Maintenance"),
    "D": ("Documentation",  "BT + HSE"),
    "O": ("Organisation",   "DMTN + Chef service BT"),
    "R": ("Règlementation", "BT + HSE + RH + DG"),
}

# Nom du sous-pilote (personne responsable) associé à chaque entité de pilotage.
# Les entités non listées ici (ex: DMTN) affichent l'entité elle-même à défaut de nom connu.
SOUS_PILOTE_NOMS = {
    "Maintenance":     "Saber BEN CHAABEN",
    "HSE":             "Montassar MEHRABI",
    "BT":              "Aïcha BELLAKHAL",
    "Chef service BT": "Aïcha BELLAKHAL",
    "RH":              "Aïcha BELLAKHAL",
    "DG":              "Aïcha BELLAKHAL",
}


# Visuel affiché à droite de l'en-tête (fichier PNG déposé à la racine du projet)
MAINTENANCE_ICON_PATH = "unnamed.png"

# Logo institutionnel (en-tête, barre latérale et rapports PDF)
LOGO_URL = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR6q1BtDSDgVnJZFo0hOBfQJoDS6OYiub-qfQ&s"
