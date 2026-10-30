"""Authentification compte de service Google (OAuth2 JWT)."""

import time

import requests
import streamlit as st

# Cache du token d'accès Google (évite de ré-authentifier à CHAQUE écriture/lecture,
# ce qui provoquait des enregistrements très lents quand plusieurs lignes étaient modifiées).
_TOKEN_CACHE = {"token": None, "expire_a": 0}

def obtenir_access_token():
    # Réutilise le token tant qu'il reste valide plus de 60 secondes
    if _TOKEN_CACHE["token"] and time.time() < _TOKEN_CACHE["expire_a"] - 60:
        return _TOKEN_CACHE["token"]
    try:
        import jwt as pyjwt
        private_key  = st.secrets["connections"]["gsheets"]["private_key"]
        client_email = st.secrets["connections"]["gsheets"]["client_email"]
        now = int(time.time())
        payload = {"iss":client_email,"scope":"https://www.googleapis.com/auth/spreadsheets",
                   "aud":"https://oauth2.googleapis.com/token","exp":now+3600,"iat":now}
        token_jwt = pyjwt.encode(payload, private_key, algorithm="RS256")
        resp = requests.post("https://oauth2.googleapis.com/token",
            data={"grant_type":"urn:ietf:params:oauth:grant-type:jwt-bearer","assertion":token_jwt},timeout=15)
        if resp.status_code == 200:
            token = resp.json()["access_token"]
            _TOKEN_CACHE["token"] = token
            _TOKEN_CACHE["expire_a"] = now + 3600
            return token
        return None
    except Exception:
        return None

def _obtenir_token_scope(scope):
    """Comme obtenir_access_token(), mais permet de demander un scope OAuth différent
    (ex: Drive en lecture) avec le même compte de service."""
    try:
        import jwt as pyjwt
        private_key  = st.secrets["connections"]["gsheets"]["private_key"]
        client_email = st.secrets["connections"]["gsheets"]["client_email"]
        now = int(time.time())
        payload = {"iss":client_email,"scope":scope,
                   "aud":"https://oauth2.googleapis.com/token","exp":now+3600,"iat":now}
        token_jwt = pyjwt.encode(payload, private_key, algorithm="RS256")
        resp = requests.post("https://oauth2.googleapis.com/token",
            data={"grant_type":"urn:ietf:params:oauth:grant-type:jwt-bearer","assertion":token_jwt},timeout=15)
        return resp.json()["access_token"] if resp.status_code==200 else None
    except Exception:
        return None
