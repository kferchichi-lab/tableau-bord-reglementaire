"""Chargement des feuilles de style globales (dossier ``css/``)."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_DOSSIER_CSS = Path(__file__).parent / "css"


@st.cache_resource(show_spinner=False)
def _lire_css(nom: str) -> str:
    return (_DOSSIER_CSS / nom).read_text(encoding="utf-8")


def appliquer_styles() -> None:
    """Injecte le thème (onglets, sélecteurs, cartes) puis les composants (boutons, champs)."""
    st.html(f"<style>{_lire_css('base.css')}</style>")
    st.markdown(f"<style>{_lire_css('components.css')}</style>", unsafe_allow_html=True)
