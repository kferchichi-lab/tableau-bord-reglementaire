"""Onglet « Rapports CR »."""


import pandas as pd
import plotly.express as px
import streamlit as st

from tpr.config import SOUS_EQUIPEMENTS, URL_GOOGLE_SHEET
from tpr.ui.liens import convertir_lien


def render(ctx):
    df_rapports = ctx.df_rapports
    password_correct = ctx.password_correct
    role = ctx.role
    val_total = ctx.val_total
    st.markdown("""<style>
        .filter-title{text-align:center!important;font-weight:600;color:#1E293B;margin-top:0;margin-bottom:15px;width:100%;}
        div[data-testid="stSelectbox"] label p{text-align:center!important;width:100%;display:block;}
    </style>""",unsafe_allow_html=True)
    col_filtre_v, col_indic_v = st.columns([4,1])
    with col_filtre_v:
        with st.container(border=True):
            st.markdown("<p class='filter-title'>Filtres de recherche</p>",unsafe_allow_html=True)
            c1,c2,c3,c4=st.columns(4)
            with c1: f_site =st.selectbox("Site",["Tous","SGB","MEG"])
            with c2: f_annee=st.selectbox("Année",["Tous","2025","2026"])
            with c3: f_ins  =st.selectbox("Installation",["Tous"]+list(SOUS_EQUIPEMENTS.keys()))
            with c4:
                opts=["Tous"]+SOUS_EQUIPEMENTS[f_ins] if f_ins!="Tous" else ["Tous"]+[i for sub in SOUS_EQUIPEMENTS.values() for i in sub]
                f_sous_eq=st.selectbox("Sous-équipement",opts)
    with col_indic_v:
        st.markdown(f"""<div style="background:white;padding:18px 10px;border-radius:12px;box-shadow:0 4px 6px -1px rgba(0,0,0,0.05);border-left:5px solid #1E3A8A;min-height:140px;box-sizing:border-box;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;">
            <p style="margin:0;font-size:12px;color:#64748B;font-weight:600;text-transform:uppercase;letter-spacing:0.3px;line-height:1.3;">Total Rapports<br>Archivés</p>
            <p style="margin:10px 0 0 0;font-size:30px;color:#0F172A;font-weight:700;line-height:1;">{val_total}</p></div>""",unsafe_allow_html=True)

    st.markdown("<br><p style='font-size:1.2rem;font-weight:700;color:#0F172A;margin-bottom:10px;'>📂 Documents rattachés</p>",unsafe_allow_html=True)
    df_f=df_rapports.copy()
    col_site=[c for c in df_f.columns if "site" in c.lower()]
    col_ex  =[c for c in df_f.columns if "exerc" in c.lower() or "ann" in c.lower()]
    col_ins =[c for c in df_f.columns if "ins" in c.lower()]
    col_seq =[c for c in df_f.columns if "sous" in c.lower()]
    col_lien=[c for c in df_f.columns if "lien" in c.lower() or "pdf" in c.lower()]
    col_date=[c for c in df_f.columns if "date" in c.lower() or "contr" in c.lower()]
    if not df_f.empty:
        if f_site !="Tous" and col_site: df_f=df_f[df_f[col_site[0]].astype(str).str.strip()==f_site]
        if f_annee!="Tous" and col_ex:   df_f=df_f[pd.to_numeric(df_f[col_ex[0]],errors='coerce')==int(f_annee)]
        if f_ins  !="Tous" and col_ins:  df_f=df_f[df_f[col_ins[0]].astype(str).str.strip()==f_ins]
        if f_sous_eq!="Tous" and col_seq:df_f=df_f[df_f[col_seq[0]].astype(str).str.strip()==f_sous_eq]
        if col_lien: df_f[col_lien[0]]=df_f[col_lien[0]].apply(convertir_lien)
        if col_date: df_f[col_date[0]]=pd.to_datetime(df_f[col_date[0]],dayfirst=True,errors='coerce')
    if not df_f.empty:
        col_reelle_doc=[c for c in df_f.columns if "reelle" in c.lower() or "réelle" in c.lower()]
        if col_reelle_doc: df_f=df_f.drop(columns=col_reelle_doc)
        col_planifiee_doc=[c for c in df_f.columns if "planifi" in c.lower()]
        if col_planifiee_doc: df_f=df_f.drop(columns=col_planifiee_doc)
        col_prochaine_doc=[c for c in df_f.columns if "prochaine" in c.lower()]
        if col_prochaine_doc: df_f=df_f.drop(columns=col_prochaine_doc)
        st.dataframe(df_f,column_config={
            (col_lien[0] if col_lien else "Lien PDF"):st.column_config.LinkColumn("Action",display_text="Voir le rapport"),
            (col_ex[0]   if col_ex   else "Année"):st.column_config.NumberColumn("Année",format="%d"),
            (col_date[0] if col_date else "Date"):    st.column_config.DateColumn("Date de dernier contrôle",format="DD/MM/YYYY"),
        },hide_index=True,use_container_width=True)
    else:
        st.warning("Aucun rapport ne correspond aux critères sélectionnés.")

    st.markdown("<br><hr style='border-color:#E2E8F0;'><p style='font-size:1.2rem;font-weight:700;color:#0F172A;'>📊 Gestion des rapports</p>",unsafe_allow_html=True)
    if not df_rapports.empty:
        col_sc=[c for c in df_rapports.columns if "site" in c.lower()]
        col_cc=[c for c in df_rapports.columns if "ins" in c.lower()]
        if col_sc and col_cc:
            df_s=df_rapports[col_sc[0]].value_counts().reset_index(); df_s.columns=['Site','Nombre']
            df_c=df_rapports[col_cc[0]].value_counts().reset_index(); df_c.columns=['Domaine','Nombre']
            g1,g2=st.columns(2)
            with g1:
                fig=px.pie(df_s,values='Nombre',names='Site',hole=0.6,color_discrete_sequence=['#1E3A8A','#0EA5E9','#94A3B8'])
                fig.update_traces(textposition='inside',textinfo='percent+label')
                fig.update_layout(margin=dict(t=10,b=10,l=10,r=10),height=220,showlegend=False,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})
            with g2:
                fig2=px.bar(df_c.sort_values('Nombre'),x='Nombre',y='Domaine',orientation='h',text='Nombre',color_discrete_sequence=['#1E3A8A'])
                fig2.update_traces(textposition='outside',cliponaxis=False)
                fig2.update_layout(margin=dict(t=5,b=5,l=10,r=40),height=220,xaxis_title=None,yaxis_title=None,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',transition_duration=500,transition_easing="cubic-in-out")
                fig2.update_xaxes(showgrid=True,gridcolor='#E2E8F0')
                st.plotly_chart(fig2,use_container_width=True,config={'displayModeBar':False})
    if role=="Admin" and password_correct:
        with st.expander("🛠️ Panneau d'administration"):
            st.markdown(f"[Ouvrir le Google Sheets]({URL_GOOGLE_SHEET})")

        # ---- ONGLET 2 : PLANNING ----
