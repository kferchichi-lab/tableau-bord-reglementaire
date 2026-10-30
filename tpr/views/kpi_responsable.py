"""Onglet « KPI » — vue responsable."""

import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from tpr.config import LOGO_URL, NATURE_PILOTE
from tpr.domain.pilotes import _codes_pour_pilote
from tpr.reports.pilote_pdf import generer_rapport_pilote_pdf
from tpr.services.codif import codif_charger_toutes_actions
from tpr.services.repository import _cle_action, lire_actions_realisees, lire_points_reserve_nature
from tpr.ui.pdf_viewer import afficher_apercu_pdf_grille


def render(ctx):
    RESPONSABLES = ctx.responsables
    compte_resp = RESPONSABLES.get(st.session_state.responsable_actif, {})
    nom_resp = compte_resp.get("nom", st.session_state.responsable_actif)
    entites_resp = compte_resp.get("entites", [])
    site_resp = compte_resp.get("site")

    st.markdown(f"<p style='font-size:1.2rem;font-weight:700;color:#1E3A8A;'>📊 Indicateurs — {nom_resp}</p>",unsafe_allow_html=True)
    st.markdown(
        "<div style='background:#EFF6FF;border-left:4px solid #2a78d6;padding:10px 14px;border-radius:6px;margin-bottom:14px;'>"
        "<p style='margin:0;font-size:12px;color:#1e40af;font-weight:600;'>Consultation seule : Veuillez sélectionner votre site</p>"
        "</div>", unsafe_allow_html=True)

    with st.spinner("Chargement des actions par nature..."):
        df_nature_r = lire_points_reserve_nature()

    if df_nature_r.empty:
        st.info("Aucune donnée disponible pour le moment.")
    else:
        if "Nombre" in df_nature_r.columns:
            df_nature_r["Nombre"] = pd.to_numeric(df_nature_r["Nombre"],errors="coerce").fillna(0).astype(int)

        # Ne garder que les lignes concernant les entités du responsable connecté
        def _concerne_responsable(pilote_str):
            entites = [e.strip() for e in str(pilote_str).split("+") if e.strip()]
            return any(e in entites_resp for e in entites)

        if "Pilote" in df_nature_r.columns:
            df_nature_r = df_nature_r[df_nature_r["Pilote"].apply(_concerne_responsable)]

        if df_nature_r.empty:
            st.info("Aucune action trouvée pour votre périmètre.")
        else:
            if site_resp:
                # Compte restreint à un seul site (ex : Saber -> MEG, Chafik -> SGB)
                st.session_state.site_kpi_responsable = site_resp
                st.markdown(f"<p style='font-size:12px;color:#64748B;margin-bottom:6px;'>🏭 Site : <strong>{site_resp}</strong></p>",unsafe_allow_html=True)
            else:
                if "site_kpi_responsable" not in st.session_state:
                    st.session_state.site_kpi_responsable = "SGB"

                rcol1,rcol2,_ = st.columns([1,1,4])
                with rcol1:
                    if st.button("🏭 SGB", key="btn_kpi_sgb_resp", type=("primary" if st.session_state.site_kpi_responsable=="SGB" else "secondary"), use_container_width=True):
                        st.session_state.site_kpi_responsable = "SGB"
                        st.rerun()
                with rcol2:
                    if st.button("🏭 MEG", key="btn_kpi_meg_resp", type=("primary" if st.session_state.site_kpi_responsable=="MEG" else "secondary"), use_container_width=True):
                        st.session_state.site_kpi_responsable = "MEG"
                        st.rerun()

            site_choisi_r = st.session_state.site_kpi_responsable
            st.markdown(f"<p style='font-weight:700;font-size:14px;color:#0F172A;text-align:center;margin:14px 0 10px 0;'>Répartition des actions — Site {site_choisi_r}</p>",unsafe_allow_html=True)

            all_natures_r = [v[0] for v in NATURE_PILOTE.values()]
            palette_nat_r = px.colors.qualitative.Set2
            color_map_nat_r = {n: palette_nat_r[i % len(palette_nat_r)] for i,n in enumerate(all_natures_r)}

            if {"Nature","Site","Nombre"}.issubset(df_nature_r.columns):
                d_site_r = df_nature_r[df_nature_r["Site"]==site_choisi_r]
                if d_site_r.empty:
                    st.info(f"Aucune donnée {site_choisi_r} pour votre périmètre.")
                else:
                    total_r = int(d_site_r["Nombre"].sum())
                    st.markdown(f"""<div style="background:white;padding:14px;border-radius:10px;box-shadow:0 2px 6px rgba(0,0,0,0.05);border-left:4px solid #1E3A8A;margin-bottom:14px;">
                        <p style="margin:0;font-size:11px;color:#64748B;font-weight:600;text-transform:uppercase;">Total actions — {site_choisi_r}</p>
                        <p style="margin:4px 0 0 0;font-size:28px;color:#0F172A;font-weight:700;">{total_r}</p></div>""",unsafe_allow_html=True)

                    dv_r = d_site_r.groupby("Nature")["Nombre"].sum().reset_index()

                    gcol1,gcol2 = st.columns(2)
                    with gcol1:
                        fig_r = px.pie(dv_r,values="Nombre",names="Nature",hole=0.6,color="Nature",color_discrete_map=color_map_nat_r)
                        fig_r.update_traces(textposition='inside',textinfo='percent+value')
                        fig_r.update_layout(title=f"{site_choisi_r} — répartition par nature",title_x=0.5,margin=dict(t=40,b=10,l=10,r=10),height=320,
                                             paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',legend=dict(font=dict(size=9)))
                        st.plotly_chart(fig_r,use_container_width=True,config={'displayModeBar':False})

                    with gcol2:
                        if "Installation" in d_site_r.columns:
                            di_r = d_site_r.groupby("Installation")["Nombre"].sum().reset_index().sort_values("Nombre",ascending=True)
                            palette_ins_r = px.colors.qualitative.Set3
                            color_map_ins_r = {i: palette_ins_r[k % len(palette_ins_r)] for k,i in enumerate(di_r["Installation"])}
                            fig_ins_r = px.bar(di_r,x="Nombre",y="Installation",orientation="h",text="Nombre",
                                                color="Installation",color_discrete_map=color_map_ins_r)
                            fig_ins_r.update_traces(textposition='outside',cliponaxis=False)
                            fig_ins_r.update_layout(title=f"{site_choisi_r} — répartition par installation",title_x=0.5,showlegend=False,
                                                     xaxis_title="Nombre d'actions",yaxis_title="",
                                                     margin=dict(t=40,b=10,l=10,r=30),height=320,
                                                     paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
                            st.plotly_chart(fig_ins_r,use_container_width=True,config={'displayModeBar':False})
                        else:
                            st.info("Aucune donnée d'installation à afficher.")

                    st.dataframe(d_site_r.rename(columns={
                        "Site":"Site","Installation":"Installation","Nombre":"Nombre des actions","Nature":"Nature","Pilote":"Pilote"
                    }),hide_index=True,use_container_width=True)
            else:
                st.info("Aucune donnée à afficher pour les graphes.")

    # ================= RAPPORT PDF ASSOCIÉ AU RESPONSABLE =================
    st.markdown("<br><hr style='border-color:#E2E8F0;'>",unsafe_allow_html=True)
    st.markdown("<p style='font-size:1.2rem;font-weight:700;color:#0F172A;'>📄 Mon rapport des actions</p>",unsafe_allow_html=True)

    if len(entites_resp) > 1:
        entite_pdf_choisie = st.selectbox("Périmètre", entites_resp, key="entite_pdf_responsable")
    else:
        entite_pdf_choisie = entites_resp[0] if entites_resp else None

    # ---- Filtre de site (MEG / SGB / Tous), réservé aux responsables multi-sites (HSE, Aïcha) ----
    site_filtre_rapport_r = site_resp  # par défaut : site fixe du compte (Saber -> MEG, Chafik -> SGB)
    if not site_resp:
        col_btn_r, col_filtre_site_r = st.columns([3,2])
        with col_filtre_site_r:
            choix_site_rapport_r = st.selectbox(
                "Site", ["Tous","MEG","SGB"], key="site_filtre_rapport_responsable"
            )
        site_filtre_rapport_r = None if choix_site_rapport_r == "Tous" else choix_site_rapport_r
        bouton_generer_r = col_btn_r.button("Générer mon rapport", use_container_width=True, key="btn_gen_rapport_responsable", type="primary")
    else:
        bouton_generer_r = st.button("Générer mon rapport", use_container_width=True, key="btn_gen_rapport_responsable", type="primary")

    if bouton_generer_r and entite_pdf_choisie:
        with st.spinner("Lecture des classeurs de codification (MEG et SGB)..."):
            df_codif_r, err = codif_charger_toutes_actions()
            if err and df_codif_r.empty:
                st.session_state["pdf_responsable"] = None
                st.error(err)
            else:
                if err:
                    st.warning(err)
                # Exclut les actions déjà cochées comme réalisées (onglet « Suivi des actions »)
                df_realisees_r = lire_actions_realisees()
                if not df_realisees_r.empty:
                    cles_faites_r = set(df_realisees_r.apply(_cle_action, axis=1))
                    df_codif_r = df_codif_r[~df_codif_r.apply(_cle_action, axis=1).isin(cles_faites_r)]

                df_codif_r["Nature"] = df_codif_r["Code"].map(lambda c: NATURE_PILOTE.get(c,("",""))[0])
                codes_ok_r = _codes_pour_pilote(entite_pdf_choisie)
                df_filtre_codif_r = df_codif_r[df_codif_r["Code"].isin(codes_ok_r)]
                if site_filtre_rapport_r and "Site" in df_filtre_codif_r.columns:
                    df_filtre_codif_r = df_filtre_codif_r[df_filtre_codif_r["Site"].astype(str).str.strip().str.upper() == site_filtre_rapport_r.upper()]
                if df_filtre_codif_r.empty:
                    st.session_state["pdf_responsable"] = None
                    st.info(f"Aucune action restante pour « {entite_pdf_choisie} »" + (f" — site {site_filtre_rapport_r}." if site_filtre_rapport_r else "."))
                else:
                    try:
                        st.session_state["pdf_responsable"] = generer_rapport_pilote_pdf(
                            entite_pdf_choisie, df_filtre_codif_r,
                            LOGO_URL
                        )
                        st.session_state["nb_actions_responsable"] = len(df_filtre_codif_r)
                    except Exception as e:
                        st.session_state["pdf_responsable"] = None
                        st.error(f"Erreur lors de la génération du PDF : {e}")

    if st.session_state.get("pdf_responsable"):
        st.success(f"{st.session_state.get('nb_actions_responsable',0)} action(s) trouvée(s) pour « {entite_pdf_choisie} ».")
        afficher_apercu_pdf_grille(st.session_state["pdf_responsable"], colonnes=2)
        st.download_button(
            label="📥 Télécharger mon rapport PDF",
            data=st.session_state["pdf_responsable"],
            file_name=f"Rapport_{entite_pdf_choisie}_{datetime.date.today().strftime('%d_%m_%Y')}.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="dl_responsable"
        )

        # ---- ONGLET 4 : KPI (Visiteur — vue simplifiée en lecture seule) ----
