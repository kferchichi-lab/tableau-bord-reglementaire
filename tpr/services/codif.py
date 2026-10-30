"""Lecture et normalisation des classeurs de codification (actions CR)."""

import io
import re
import unicodedata

import pandas as pd
import requests
import streamlit as st

from tpr.config import CODIF_SHEET_ID_PAR_SITE, COLONNES_CODIF_PAR_INSTALLATION, NATURE_PILOTE
from tpr.services.google_auth import _obtenir_token_scope


def codif_charger_classeur(sheet_id):
    """Télécharge le classeur de codification via l'API Google Drive.
    Essaie d'abord l'export Excel (/export?mimeType=...) qui fonctionne pour un Google Sheets
    natif (cas des classeurs MEG/SGB), puis se rabat sur le téléchargement direct (alt=media),
    utile pour un fichier .xlsx binaire jamais converti en Sheets natif.
    Retourne (dict {nom_onglet: DataFrame_brut_sans_entete}, message_erreur détaillé)."""
    token = _obtenir_token_scope("https://www.googleapis.com/auth/drive.readonly")
    if not token:
        return None, "Impossible d'obtenir un jeton d'accès Google (scope Drive)."
    headers = {"Authorization": f"Bearer {token}"}
    try:
        email = st.secrets["connections"]["gsheets"]["client_email"]
    except Exception:
        email = "(voir le champ client_email de vos secrets)"

    # 0) Vérification préalable : le compte de service voit-il seulement les métadonnées du fichier ?
    #    Permet de distinguer "fichier introuvable / ID erroné" de "fichier vu mais export refusé".
    meta_msg = ""
    try:
        resp_meta = requests.get(
            f"https://www.googleapis.com/drive/v3/files/{sheet_id}",
            headers=headers,
            params={"fields": "id,name,mimeType,driveId", "supportsAllDrives": "true"},
            timeout=15,
        )
        if resp_meta.status_code == 200:
            meta_msg = f" (fichier vu : {resp_meta.json().get('name','?')})"
        else:
            meta_msg = f" [métadonnées: HTTP {resp_meta.status_code} — {resp_meta.text[:200]}]"
    except Exception as e:
        meta_msg = f" [métadonnées: erreur réseau — {e}]"

    dernier_status = None
    dernier_texte = ""

    # 1) Tentative : export natif (Google Sheets -> xlsx). C'est la bonne méthode pour un
    #    classeur Google Sheets classique (ex: liens docs.google.com/spreadsheets/.../edit).
    try:
        url_export = f"https://www.googleapis.com/drive/v3/files/{sheet_id}/export"
        resp = requests.get(
            url_export, headers=headers,
            params={
                "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "supportsAllDrives": "true",
            },
            timeout=30,
        )
        if resp.status_code == 200:
            classeur = pd.read_excel(io.BytesIO(resp.content), sheet_name=None, header=None, engine="openpyxl")
            return classeur, None
        dernier_status, dernier_texte = resp.status_code, resp.text
    except Exception as e:
        dernier_status, dernier_texte = None, str(e)

    # 2) Repli : téléchargement direct (fichier .xlsx binaire jamais converti en Sheets natif).
    try:
        url = f"https://www.googleapis.com/drive/v3/files/{sheet_id}"
        resp = requests.get(url, headers=headers, params={"alt": "media", "supportsAllDrives": "true"}, timeout=30)
        if resp.status_code == 200:
            classeur = pd.read_excel(io.BytesIO(resp.content), sheet_name=None, header=None, engine="openpyxl")
            return classeur, None
        dernier_status, dernier_texte = resp.status_code, resp.text
    except Exception as e:
        return None, f"Erreur inattendue lors de la lecture du fichier Excel : {e}{meta_msg}"

    if dernier_status in (403, 404):
        return None, (f"Accès refusé au fichier de codification (ID {sheet_id}){meta_msg}. "
                       f"Vérifiez qu'il est bien partagé (en lecture) avec le compte de service : {email}. "
                       f"Détail Google : HTTP {dernier_status} — {str(dernier_texte)[:300]}")
    return None, f"Erreur API Google Drive ({dernier_status}){meta_msg} : {str(dernier_texte)[:300]}"

def _sans_accents(texte):
    """Retire les accents d'une chaîne pour faciliter les comparaisons insensibles aux accents."""
    return "".join(c for c in unicodedata.normalize("NFD", str(texte)) if unicodedata.category(c) != "Mn")

def _normaliser(texte):
    return _sans_accents(texte).strip().lower()

def _colonnes_attendues_pour_onglet(onglet):
    """Détermine, à partir du nom de l'onglet (ex: 'Installation électrique - MEG' ou
    'Sécurité incendie - SGB'), les noms exacts des colonnes Désignation/Observation/Code à
    utiliser pour cet onglet. Retourne None si le type d'installation n'est pas reconnu
    (repli sur la détection générique par mots-clés)."""
    if not onglet:
        return None
    # On retire un éventuel suffixe de site ("- MEG" / "- SGB") pour ne garder que le type
    # d'installation, puis on teste les mots-clés dans un ordre où les plus spécifiques
    # ("pression") sont vérifiés avant les plus génériques ("gaz").
    base = re.sub(r"\s*-\s*(meg|sgb)\s*$", "", onglet, flags=re.IGNORECASE).strip()
    base_norm = _normaliser(base)
    for mots_cles, nom_desig, nom_obs, nom_code in COLONNES_CODIF_PAR_INSTALLATION:
        if all(mc in base_norm for mc in mots_cles):
            return (nom_desig, nom_obs, nom_code)
    return None

def _trouver_colonne_exacte(colonnes, nom_attendu):
    """Recherche une colonne correspondant exactement (insensible aux accents/casse) au nom
    attendu ; à défaut, se rabat sur une correspondance partielle."""
    cible = _normaliser(nom_attendu)
    for c in colonnes:
        if _normaliser(c) == cible:
            return c
    for c in colonnes:
        if cible in _normaliser(c):
            return c
    return None

def _detecter_entete_et_nettoyer_codif(valeurs, onglet=None):
    """Prend les lignes brutes (liste de listes) d'un onglet du classeur de codification et
    retourne un DataFrame propre avec les colonnes Désignation | Observation | Code.
    Cherche automatiquement la ligne d'en-tête, en tolérant les différents intitulés utilisés
    selon les onglets (ex: 'Désignation'/'Rapport' pour l'équipement,
    'Observation'/'Organes examinés NC'/'Problème' pour l'action), et complète (forward-fill)
    les cellules d'équipement fusionnées verticalement dans la feuille source."""
    if not valeurs:
        return pd.DataFrame()

    MOTS_CLES_EQUIP = ["désignation", "désignation", "équipement", "equipement", "rapport"]
    MOTS_CLES_OBS   = ["observation", "organe", "examin", "problème", "probleme", "action"]

    # Colonnes exactes attendues pour ce type d'installation (déduites du nom de l'onglet),
    # sinon repli sur la détection générique par mots-clés (ancien comportement).
    colonnes_attendues = _colonnes_attendues_pour_onglet(onglet)

    idx_entete = None
    for i, ligne in enumerate(valeurs):
        cellules = [str(c).strip().lower() for c in ligne]
        if colonnes_attendues:
            nom_desig, nom_obs, _nom_code = colonnes_attendues
            cible_desig = _normaliser(nom_desig)
            cible_obs = _normaliser(nom_obs)
            a_equip = any(_normaliser(c) == cible_desig for c in cellules)
            a_obs   = any(_normaliser(c) == cible_obs for c in cellules)
        else:
            a_equip = any(any(mc in c for mc in MOTS_CLES_EQUIP) for c in cellules)
            a_obs   = any(any(mc in c for mc in MOTS_CLES_OBS) for c in cellules)
        if a_equip and a_obs:
            idx_entete = i
            break
    if idx_entete is None:
        return pd.DataFrame()

    entetes = [str(c).strip() for c in valeurs[idx_entete]]
    nb_col = len(entetes)
    lignes = valeurs[idx_entete + 1:]
    lignes = [(list(r) + [""] * (nb_col - len(r)))[:nb_col] for r in lignes]
    df = pd.DataFrame(lignes, columns=entetes)

    def _trouver_colonne(colonnes, groupes_mots_cles):
        """Cherche la colonne correspondant au groupe de mots-clés le plus spécifique possible
        (on essaie groupe par groupe, du plus spécifique au plus générique, et on ne retombe sur
        un groupe générique — ex: 'rapport', 'action' — que si aucune colonne plus spécifique
        n'a matché, pour éviter de capturer par erreur une autre colonne du même onglet)."""
        for groupe in groupes_mots_cles:
            for c in colonnes:
                if any(mc in c.lower() for mc in groupe):
                    return c
        return None

    if colonnes_attendues:
        nom_desig, nom_obs, nom_code = colonnes_attendues
        col_desig = _trouver_colonne_exacte(df.columns, nom_desig)
        col_obs   = _trouver_colonne_exacte(df.columns, nom_obs)
        col_code  = _trouver_colonne_exacte(df.columns, nom_code)
    else:
        col_desig = _trouver_colonne(df.columns, [
            ["désignation", "désignation", "équipement", "equipement"],
            ["rapport"],
        ])
        col_obs = _trouver_colonne(df.columns, [
            ["observation"],
            ["organe", "examin"],
            ["problème", "probleme"],
            ["action"],
        ])
        col_code  = next((c for c in df.columns if c.strip().lower() in ("c", "code")), None)
    if not (col_desig and col_obs and col_code):
        return pd.DataFrame()

    df = df[[col_desig, col_obs, col_code]].copy()
    df.columns = ["Désignation", "Observation", "Code"]
    for c in df.columns:
        df[c] = df[c].astype(str).str.strip()
        df[c] = df[c].replace("nan", "")
    df["Désignation"] = df["Désignation"].replace("", pd.NA).ffill().fillna("")
    df["Code"] = df["Code"].str.upper()
    df = df[(df["Observation"] != "") & (df["Code"] != "")]
    df = df[df["Code"].isin(NATURE_PILOTE.keys())]
    return df.reset_index(drop=True)

@st.cache_data(ttl=300, show_spinner=False)
def codif_charger_toutes_actions():
    """Charge et combine les classeurs de codification des deux sites (MEG et SGB).
    Retourne (DataFrame combiné [Site, Installation, Désignation, Observation, Code], message_erreur_ou_None)."""
    frames, erreurs = [], []
    for site, sheet_id in CODIF_SHEET_ID_PAR_SITE.items():
        classeur, err = codif_charger_classeur(sheet_id)
        if err:
            erreurs.append(f"{site} : {err}")
            continue
        if not classeur:
            continue
        for onglet, df_brut in classeur.items():
            valeurs = df_brut.fillna("").astype(str).values.tolist()
            d = _detecter_entete_et_nettoyer_codif(valeurs, onglet)
            if not d.empty:
                d["Installation"] = onglet
                d["Site"] = site
                frames.append(d)
    if not frames:
        return pd.DataFrame(), (" / ".join(erreurs) if erreurs else "Aucune donnée trouvée dans les classeurs de codification.")
    return pd.concat(frames, ignore_index=True), (" / ".join(erreurs) if erreurs else None)
