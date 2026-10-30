"""Accès bas niveau à l'API Google Sheets."""

import math

import pandas as pd
import requests

from tpr.config import SHEET_ID
from tpr.services.google_auth import obtenir_access_token


def sheets_append(onglet, valeurs):
    token = obtenir_access_token()
    if not token: return False,"Token invalide"
    # Filet de sécurité : un NaN pandas glissé dans `valeurs` fait échouer json.dumps(allow_nan=False)
    # utilisé en interne par `requests`, ce qui faisait échouer l'écriture avec un message trompeur.
    valeurs = [("" if (v is None or (isinstance(v, float) and v != v)) else v) for v in valeurs]
    try:
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{onglet}!A:Z:append"
        resp = requests.post(url,headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},
            params={"valueInputOption":"RAW","insertDataOption":"INSERT_ROWS"},json={"values":[valeurs]},timeout=15)
        return (True,"") if resp.status_code==200 else (False,resp.text)
    except Exception as e:
        return False,str(e)

def sheets_append_multiple(onglet, liste_de_lignes):
    """Enregistre PLUSIEURS lignes en un seul appel réseau (au lieu d'un appel par ligne).
    liste_de_lignes : liste de listes de valeurs. Retourne (ok, message_erreur)."""
    if not liste_de_lignes:
        return True, ""
    token = obtenir_access_token()
    if not token:
        return False, "Token invalide"
    valeurs_nettoyees = [
        [("" if (v is None or (isinstance(v, float) and v != v)) else v) for v in ligne]
        for ligne in liste_de_lignes
    ]
    try:
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{onglet}!A:Z:append"
        resp = requests.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
            json={"values": valeurs_nettoyees}, timeout=30)
        return (True, "") if resp.status_code == 200 else (False, resp.text)
    except Exception as e:
        return False, str(e)

def sheets_lire(onglet, plage="A:Z"):
    token = obtenir_access_token()
    if not token: return pd.DataFrame()
    try:
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{onglet}!{plage}"
        resp = requests.get(url,headers={"Authorization":f"Bearer {token}"},timeout=15)
        if resp.status_code!=200: return pd.DataFrame()
        valeurs = resp.json().get("values",[])
        if len(valeurs)<=1: return pd.DataFrame()
        entetes = [str(c).strip() for c in valeurs[0]]
        nb_col = len(entetes)
        # Complète les lignes trop courtes avec des cellules vides (Google Sheets omet les cellules vides en fin de ligne)
        lignes = [ (r + [""]*(nb_col-len(r)))[:nb_col] for r in valeurs[1:] ]
        df = pd.DataFrame(lignes,columns=entetes)
        # Nettoie les espaces superflus dans toutes les valeurs texte pour éviter les non-correspondances silencieuses
        for c in df.columns:
            if df[c].dtype == object:
                df[c] = df[c].astype(str).str.strip()
        return df
    except Exception:
        return pd.DataFrame()

def sheets_ecrire_cellule_v2(onglet, cellule, valeur):
    """Écrit une valeur dans une cellule précise. Retourne (ok, message_erreur)."""
    token = obtenir_access_token()
    if not token: return False, "Token invalide"
    try:
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{onglet}!{cellule}"
        resp = requests.put(url,headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},
            params={"valueInputOption":"RAW"},json={"values":[[valeur]]},timeout=15)
        if resp.status_code == 200:
            return True, ""
        return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return False, str(e)

def sheets_trouver_ligne_email(onglet, email):
    token = obtenir_access_token()
    if not token: return None
    try:
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{onglet}!A:A"
        resp = requests.get(url,headers={"Authorization":f"Bearer {token}"},timeout=15)
        if resp.status_code!=200: return None
        for i,row in enumerate(resp.json().get("values",[])):
            if row and row[0]==email: return i+1
        return None
    except Exception:
        return None

def _valeur_sheet(v):
    """Convertit une valeur de ligne pandas en valeur sûre pour l'API Sheets/JSON.
    Une cellule vide dans un DataFrame pandas peut être un float NaN (pas une chaîne vide) ;
    or json.dumps(..., allow_nan=False) — utilisé par `requests` — lève une exception sur NaN,
    ce qui faisait échouer silencieusement CHAQUE écriture concernée ('Out of range float
    values are not JSON compliant: nan'). On neutralise donc tout NaN/None en chaîne vide."""
    if v is None:
        return ""
    try:
        if isinstance(v, float) and math.isnan(v):
            return ""
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    return v
