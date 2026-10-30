"""Sécurité : hachage des mots de passe, anti-bruteforce, validation."""

import hashlib
import hmac
import re
import secrets as secrets_lib
import time

import streamlit as st

_PBKDF2_ITERATIONS = 200_000

def hacher_mot_de_passe(mot_de_passe: str, sel: bytes = None) -> str:
    """Retourne 'sel_hex$hash_hex' à stocker dans st.secrets."""
    if sel is None:
        sel = secrets_lib.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode("utf-8"), sel, _PBKDF2_ITERATIONS)
    return f"{sel.hex()}${h.hex()}"

def verifier_mot_de_passe(mot_de_passe_saisi: str, hash_stocke: str) -> bool:
    """Compare en temps constant le mot de passe saisi au hash stocké (format 'sel_hex$hash_hex')."""
    try:
        sel_hex, hash_hex = hash_stocke.split("$", 1)
        sel = bytes.fromhex(sel_hex)
        h_saisi = hashlib.pbkdf2_hmac("sha256", mot_de_passe_saisi.encode("utf-8"), sel, _PBKDF2_ITERATIONS)
        return hmac.compare_digest(h_saisi.hex(), hash_hex)
    except Exception:
        return False

_MAX_TENTATIVES = 5

_DUREE_BLOCAGE_SECONDES = 60  # 5 minutes

def tentative_bloquee(cle: str) -> int:
    """Retourne le nb de secondes restant avant déblocage (0 si non bloqué)."""
    blocage_jusqu_a = st.session_state.get(f"blocage_{cle}", 0)
    reste = blocage_jusqu_a - time.time()
    return max(0, int(reste))

def enregistrer_echec(cle: str):
    nb = st.session_state.get(f"echecs_{cle}", 0) + 1
    st.session_state[f"echecs_{cle}"] = nb
    if nb >= _MAX_TENTATIVES:
        st.session_state[f"blocage_{cle}"] = time.time() + _DUREE_BLOCAGE_SECONDES
        st.session_state[f"echecs_{cle}"] = 0

def reinitialiser_echecs(cle: str):
    st.session_state[f"echecs_{cle}"] = 0
    st.session_state[f"blocage_{cle}"] = 0

def format_email_valide(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+",email) is not None
