"""En-tête de l'application."""


from pathlib import Path

import streamlit as st

from tpr.config import MAINTENANCE_ICON_PATH


def render_header():
    col_titre, col_icone = st.columns([5,1])
    with col_titre:
        st.markdown("""<div class="app-header-block" style="width:100%;margin:10px auto 0 auto;">
        <div style="display:flex;justify-content:center;align-items:baseline;gap:8px;">
            <h1 style="font-size:2.6rem;font-weight:800;color:#0F172A;margin:0;letter-spacing:-1px;line-height:1.2;">Tableau de Bord Réglementaire</h1>
            <span style="font-size:0.75rem;color:#94A3B8;font-weight:400;white-space:nowrap;">v1.1.0</span>
        </div>
        <p style="text-align:center;font-size:0.85rem;color:#64748B;margin:6px auto 0 auto;font-weight:400;line-height:1.5;max-width:800px;">L'amélioration continue.. Notre trajectoire..</p>
        <p style="text-align:center;font-size:0.75rem;color:#64748B;margin:6px auto 0 auto;font-weight:400;line-height:1.5;max-width:800px;">© 2026 TPR</p>
        </div>""",unsafe_allow_html=True)
    with col_icone:
        if Path(MAINTENANCE_ICON_PATH).is_file():
            st.image(MAINTENANCE_ICON_PATH, use_container_width=True)
