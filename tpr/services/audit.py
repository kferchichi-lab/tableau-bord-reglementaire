"""Journal d'audit et identification de l'utilisateur courant."""

import datetime

import streamlit as st

from tpr.config import TZ
from tpr.services.sheets import sheets_append


def journaliser_action(utilisateur: str, action: str, details: str = ""):
    try:
        now_str = datetime.datetime.now(TZ).strftime("%d/%m/%Y %H:%M:%S")
        sheets_append("AuditLog", [now_str, utilisateur or "inconnu", action, details])
    except Exception:
        pass  # la journalisation ne doit jamais bloquer l'action métier principale

_CLE_UTILISATEUR = "_utilisateur_courant"


def definir_utilisateur(libelle: str | None) -> None:
    """Mémorise l'utilisateur authentifié de la session (utilisé par le journal d'audit)."""
    st.session_state[_CLE_UTILISATEUR] = libelle or "inconnu"


def utilisateur_courant() -> str:
    """Libellé de l'utilisateur actif : « Admin », « Responsable : ID » ou « Visiteur : e-mail »."""
    return st.session_state.get(_CLE_UTILISATEUR, "inconnu")
