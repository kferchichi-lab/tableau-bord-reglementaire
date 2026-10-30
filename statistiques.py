"""Onglet « Statistiques » (administrateur)."""


import streamlit as st

from tpr.services.repository import lire_audit_log, lire_logs, lire_presence


def render(ctx):
    st.markdown("<p style='font-size:1.2rem;font-weight:700;color:#1E3A8A;'>👥 Suivi des visiteurs</p>",unsafe_allow_html=True)
    col_r,_=st.columns([1,5])
    with col_r:
        if st.button("🔄"): st.rerun()
    st.markdown("### 🟢 Présence en temps réel")
    with st.spinner("Chargement..."):
        df_presence=lire_presence()
    if df_presence.empty:
        st.info("Aucun visiteur enregistré.")
    else:
        nb_en_ligne=len(df_presence[df_presence["Statut"].str.contains("🟢")])
        nb_recent  =len(df_presence[df_presence["Statut"].str.contains("🟡")])
        nb_offline =len(df_presence[df_presence["Statut"].str.contains("🔴")])
        p1,p2,p3=st.columns(3)
        with p1:
            st.markdown(f"""<div style="background:#F0FDF4;padding:16px;border-radius:10px;border-left:4px solid #10B981;margin-bottom:16px;">
                <p style="margin:0;font-size:11px;color:#064E3B;font-weight:700;text-transform:uppercase;">🟢 En ligne</p>
                <p style="margin:4px 0 0 0;font-size:32px;color:#065F46;font-weight:800;">{nb_en_ligne}</p></div>""",unsafe_allow_html=True)
        with p2:
            st.markdown(f"""<div style="background:#FFFBEB;padding:16px;border-radius:10px;border-left:4px solid #F59E0B;margin-bottom:16px;">
                <p style="margin:0;font-size:11px;color:#78350F;font-weight:700;text-transform:uppercase;">🟡 Récemment actif</p>
                <p style="margin:4px 0 0 0;font-size:32px;color:#92400E;font-weight:800;">{nb_recent}</p></div>""",unsafe_allow_html=True)
        with p3:
            st.markdown(f"""<div style="background:#FEF2F2;padding:16px;border-radius:10px;border-left:4px solid #EF4444;margin-bottom:16px;">
                <p style="margin:0;font-size:11px;color:#7F1D1D;font-weight:700;text-transform:uppercase;">🔴 Hors ligne</p>
                <p style="margin:4px 0 0 0;font-size:32px;color:#991B1B;font-weight:800;">{nb_offline}</p></div>""",unsafe_allow_html=True)
        st.dataframe(df_presence,column_config={
            "Email":st.column_config.TextColumn("📧 Visiteur"),
            "Dernière activité":st.column_config.TextColumn("🕐 Dernière activité"),
            "Statut":st.column_config.TextColumn("Statut"),
            "Activité":st.column_config.TextColumn("⏱️ Détail")},
            hide_index=True,use_container_width=True)

    st.markdown("<br>",unsafe_allow_html=True)
    st.markdown("### 📋 Historique complet des accès")
    with st.spinner("Chargement des logs..."):
        df_logs=lire_logs()
    if df_logs.empty:
        st.info("Aucun log enregistré.")
    else:
        nb_total=len(df_logs)
        col_em=[c for c in df_logs.columns if "email" in c.lower() or "mail" in c.lower()]
        nb_uniq=df_logs[col_em[0]].nunique() if col_em else 0
        l1,l2=st.columns(2)
        with l1:
            st.markdown(f"""<div style="background:white;padding:16px;border-radius:10px;box-shadow:0 2px 6px rgba(0,0,0,0.05);border-left:4px solid #1E3A8A;margin-bottom:16px;">
                <p style="margin:0;font-size:11px;color:#64748B;font-weight:600;text-transform:uppercase;">Total visites</p>
                <p style="margin:4px 0 0 0;font-size:28px;color:#0F172A;font-weight:700;">{nb_total}</p></div>""",unsafe_allow_html=True)
        with l2:
            st.markdown(f"""<div style="background:white;padding:16px;border-radius:10px;box-shadow:0 2px 6px rgba(0,0,0,0.05);border-left:4px solid #0EA5E9;margin-bottom:16px;">
                <p style="margin:0;font-size:11px;color:#64748B;font-weight:600;text-transform:uppercase;">Visiteurs uniques</p>
                <p style="margin:4px 0 0 0;font-size:28px;color:#0F172A;font-weight:700;">{nb_uniq}</p></div>""",unsafe_allow_html=True)
        st.dataframe(df_logs,column_config={
            "Date":st.column_config.TextColumn("📅 Date & Heure"),
            "Email":st.column_config.TextColumn("📧 E-mail")},
            hide_index=True,use_container_width=True)

    # ---- Journal d'audit (traçabilité des actions de modification) ----
    st.markdown("<br><hr style='border-color:#E2E8F0;'>",unsafe_allow_html=True)
    st.markdown("<br>",unsafe_allow_html=True)
    st.markdown("### 🧾 Journal d'audit")
    st.caption("Historique des créations, modifications, suppressions effectuées dans l'application.")
    with st.spinner("Chargement du journal d'audit..."):
        df_audit = lire_audit_log()
    if df_audit.empty:
        st.info("Aucune action journalisée.")
    else:
        st.dataframe(df_audit.sort_index(ascending=False), hide_index=True, use_container_width=True)




        # ---- ONGLET 4 : KPI (Admin uniquement — vue complète) ----
