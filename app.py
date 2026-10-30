"""Tableau de Bord Réglementaire — Tunisie Profilés d'Aluminium (point d'entrée Streamlit).

Lancer :  streamlit run app.py
"""

from __future__ import annotations

import time

import streamlit as st

st.set_page_config(page_title="Contrôle Réglementaire", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

from tpr.context import AppContext  # noqa: E402
from tpr.core.state import init_session_state  # noqa: E402
from tpr.services.audit import definir_utilisateur  # noqa: E402
from tpr.services.repository import charger_donnees_sheet, mettre_a_jour_presence  # noqa: E402
from tpr.ui.header import render_header  # noqa: E402
from tpr.ui.indicateurs import render_indicateurs  # noqa: E402
from tpr.ui.login import render_login_visiteur  # noqa: E402
from tpr.ui.sidebar import render_sidebar  # noqa: E402
from tpr.ui.styles import appliquer_styles  # noqa: E402
from tpr.views import (  # noqa: E402
    exigences,
    kpi_admin,
    kpi_responsable,
    kpi_visiteur,
    planification,
    rapports,
    statistiques,
    suivi_actions,
)

HEARTBEAT_SECONDES = 30


def _heartbeat(ctx: AppContext) -> None:
    """Met à jour la présence de l'utilisateur et programme un rafraîchissement périodique."""
    maintenant = time.time()
    if maintenant - st.session_state.get("last_heartbeat", 0) > HEARTBEAT_SECONDES:
        mettre_a_jour_presence(ctx.email_actif)
        st.session_state.last_heartbeat = maintenant
    st.markdown(
        f"""<script>setTimeout(function(){{window.parent.document.querySelector('[data-testid="stApp"]').click();}},{HEARTBEAT_SECONDES * 1000});</script>""",
        unsafe_allow_html=True,
    )


def _onglets(ctx: AppContext) -> list[tuple[str, callable]]:
    """Onglets visibles selon le profil, dans l'ordre d'affichage."""
    onglets = [
        ("📋 Rapports CR", rapports.render),
        ("📅 Planification", planification.render),
        ("📌 Exigences", exigences.render),
    ]
    if ctx.est_admin:
        onglets.append(("👥 Statistiques", statistiques.render))
    kpi = kpi_admin if ctx.est_admin else kpi_responsable if ctx.est_responsable else kpi_visiteur
    onglets.append(("📊 KPI", kpi.render))
    if ctx.peut_suivre_actions:
        onglets.append(("✅ Suivi des actions", suivi_actions.render))
    return onglets


def main() -> None:
    init_session_state()
    appliquer_styles()

    df_rapports = charger_donnees_sheet("Rapports")
    df_planning = charger_donnees_sheet("Planning")

    role, password_correct, responsables = render_sidebar()
    ctx = AppContext(
        role=role,
        password_correct=password_correct,
        responsable_connecte=st.session_state.responsable_connecte,
        responsable_actif=st.session_state.responsable_actif,
        email_visiteur=st.session_state.email_visiteur,
        responsables=responsables,
        df_rapports=df_rapports,
        df_planning=df_planning,
    )

    render_header()
    if not ctx.acces_autorise:
        if role == "Visiteur":
            render_login_visiteur()
        return

    definir_utilisateur(ctx.libelle_utilisateur)
    if ctx.email_actif:
        _heartbeat(ctx)

    render_indicateurs(ctx)
    st.markdown("<br>", unsafe_allow_html=True)

    onglets = _onglets(ctx)
    for conteneur, (_, rendu) in zip(st.tabs([titre for titre, _ in onglets]), onglets):
        with conteneur:
            rendu(ctx)


main()
