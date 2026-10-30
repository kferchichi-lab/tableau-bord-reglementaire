"""Onglet « KPI » — vue visiteur."""


import pandas as pd
import plotly.express as px
import streamlit as st

from tpr.config import NATURE_PILOTE
from tpr.services.repository import lire_points_reserve_nature


def render(ctx):
    st.markdown("<br><p style='font-size:1.2rem;font-weight:700;color:#1E3A8A;'>📊 Actions de contrôle par nature</p>",unsafe_allow_html=True)

    with st.spinner("Chargement des actions par nature..."):
        df_nature_v = lire_points_reserve_nature()

    if df_nature_v.empty:
        st.info("Aucune donnée disponible pour le moment.")
    else:
        if "Nombre" in df_nature_v.columns:
            df_nature_v["Nombre"] = pd.to_numeric(df_nature_v["Nombre"],errors="coerce").fillna(0).astype(int)

        if "site_kpi_visiteur" not in st.session_state:
            st.session_state.site_kpi_visiteur = "SGB"

        bcol1,bcol2,_ = st.columns([1,1,4])
        with bcol1:
            if st.button("🏭 SGB", key="btn_kpi_sgb", type=("primary" if st.session_state.site_kpi_visiteur=="SGB" else "secondary"), use_container_width=True):
                st.session_state.site_kpi_visiteur = "SGB"
                st.rerun()
        with bcol2:
            if st.button("🏭 MEG", key="btn_kpi_meg", type=("primary" if st.session_state.site_kpi_visiteur=="MEG" else "secondary"), use_container_width=True):
                st.session_state.site_kpi_visiteur = "MEG"
                st.rerun()

        site_choisi = st.session_state.site_kpi_visiteur
        st.markdown(f"<p style='font-weight:700;font-size:14px;color:#0F172A;text-align:center;margin:14px 0 10px 0;'>Répartition — Site {site_choisi}</p>",unsafe_allow_html=True)

        all_natures_v = [v[0] for v in NATURE_PILOTE.values()]
        palette_nat_v = px.colors.qualitative.Set2
        color_map_nat_v = {n: palette_nat_v[i % len(palette_nat_v)] for i,n in enumerate(all_natures_v)}

        entites_atomiques_v = sorted(set(
            e.strip() for v in NATURE_PILOTE.values() for e in v[1].split("+") if e.strip()
        ))
        palette_pil_v = px.colors.qualitative.Set1
        color_map_pil_v = {p: palette_pil_v[i % len(palette_pil_v)] for i,p in enumerate(entites_atomiques_v)}

        if {"Nature","Pilote","Site"}.issubset(df_nature_v.columns):
            vg1,vg2 = st.columns(2)
            with vg1:
                dv = df_nature_v[df_nature_v["Site"]==site_choisi].groupby("Nature")["Nombre"].sum().reset_index()
                if dv.empty:
                    st.info(f"Aucune donnée {site_choisi}.")
                else:
                    figv1 = px.pie(dv,values="Nombre",names="Nature",hole=0.6,color="Nature",color_discrete_map=color_map_nat_v)
                    figv1.update_traces(textposition='inside',textinfo='percent')
                    figv1.update_layout(title=f"{site_choisi} — % par nature",title_x=0.5,margin=dict(t=40,b=10,l=10,r=10),height=300,
                                         paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',legend=dict(font=dict(size=9)))
                    st.plotly_chart(figv1,use_container_width=True,config={'displayModeBar':False})
            with vg2:
                dsite = df_nature_v[df_nature_v["Site"]==site_choisi]
                total_v = dsite["Nombre"].sum()
                compte_v = {}
                for _,row in dsite.iterrows():
                    for e in str(row["Pilote"]).split("+"):
                        e = e.strip()
                        if not e: continue
                        compte_v[e] = compte_v.get(e,0) + row["Nombre"]
                if not compte_v or total_v==0:
                    st.info(f"Aucune donnée {site_choisi}.")
                else:
                    ddv = pd.DataFrame({"Pilote":list(compte_v.keys()),"Nombre":list(compte_v.values())})
                    ddv["Pourcentage"] = (ddv["Nombre"]/total_v*100).round(1)
                    ddv = ddv.sort_values("Pourcentage",ascending=True)
                    figv2 = px.bar(ddv,x="Pourcentage",y="Pilote",orientation="h",text="Pourcentage",
                                   color="Pilote",color_discrete_map=color_map_pil_v)
                    figv2.update_traces(texttemplate='%{text}%',textposition='outside',cliponaxis=False)
                    figv2.update_layout(title=f"{site_choisi} — % par pilote",title_x=0.5,showlegend=False,
                                         xaxis_title="% des actions",yaxis_title="",
                                         margin=dict(t=40,b=10,l=10,r=30),height=300,
                                         paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(figv2,use_container_width=True,config={'displayModeBar':False})
        else:
            st.info("Aucune donnée à afficher pour les graphes.")

        # ---- ONGLET 5 : SUIVI DES ACTIONS (cocher les actions terminées, historique persistant) ----
