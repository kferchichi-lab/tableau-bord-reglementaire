"""Initialisation de l'état de session Streamlit."""

from __future__ import annotations

import datetime

import streamlit as st


def init_session_state() -> None:
    aujourdhui = datetime.date.today()
    defauts = {
        "email_visiteur": None,
        "heartbeat_actif": False,
        "cal_mois": aujourdhui.month,
        "cal_annee": aujourdhui.year,
        "jour_selectionne": None,
        "responsable_connecte": False,
        "responsable_actif": None,
    }
    for cle, valeur in defauts.items():
        st.session_state.setdefault(cle, valeur)
