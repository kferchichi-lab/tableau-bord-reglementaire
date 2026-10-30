"""Barre latérale : identité de l'organisation et authentification."""

import datetime

import streamlit as st

from tpr.config import LOGO_URL, TZ
from tpr.core.accounts import charger_comptes
from tpr.core.security import enregistrer_echec, reinitialiser_echecs, tentative_bloquee, verifier_mot_de_passe
from tpr.services.sheets import sheets_append


def render_sidebar():
    with st.sidebar:
        st.markdown("<br>",unsafe_allow_html=True)
        _,c2,_=st.columns([1,4,1])
        with c2:
            st.image(LOGO_URL,use_container_width=True)
        st.markdown("""<div style="text-align:center;margin-top:15px;margin-bottom:25px;">
            <h3 style="font-size:1.15rem;font-weight:700;margin-bottom:4px;color:#0F172A;">Tunisie Profilés d'Aluminium</h3>
            <p style="font-size:0.85rem;color:#64748B;margin:0;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;">Direction Maintenance & TN</p>
        </div>""",unsafe_allow_html=True)
        st.divider()
        st.markdown("<p style='font-weight:600;color:#334155;margin-bottom:0;'>🔐 Espace sécurisé</p>",unsafe_allow_html=True)
        role=st.selectbox("Profil :",["Visiteur","Responsable","Admin"],label_visibility="collapsed")
        password_correct=False

        ADMIN_HASH, RESPONSABLES = charger_comptes()

        if "responsable_connecte" not in st.session_state: st.session_state.responsable_connecte=False
        if "responsable_actif" not in st.session_state: st.session_state.responsable_actif=None

        if role=="Admin":
            secondes_restantes = tentative_bloquee("admin")
            if secondes_restantes > 0:
                st.error(f"🔒 Trop de tentatives échouées. Réessaie dans {secondes_restantes} s.")
            else:
                password=st.text_input("Code d'accès :",type="password",placeholder="•••")
                if password and verifier_mot_de_passe(password, ADMIN_HASH):
                    password_correct=True
                    reinitialiser_echecs("admin")
                    st.success("Accès administrateur validé")
                    if "responsable_log_enregistre" not in st.session_state:
                        st.session_state.responsable_log_enregistre=True
                        now_str=datetime.datetime.now(TZ).strftime("%d/%m/%Y %H:%M")
                        sheets_append("Logs",[now_str,"responsable@admin"])
                elif password:
                    enregistrer_echec("admin")
                    st.error("Code d'accès incorrect")
        elif role=="Responsable":
            secondes_restantes = tentative_bloquee("responsable")
            if secondes_restantes > 0:
                st.error(f"🔒 Trop de tentatives échouées. Réessaie dans {secondes_restantes} s.")
            else:
                identifiant=st.text_input("Identifiant :",placeholder="Identifiant").strip().upper()
                mdp_resp=st.text_input("Mot de passe :",type="password",placeholder="•••")
                if identifiant and mdp_resp:
                    compte=RESPONSABLES.get(identifiant)
                    if compte and verifier_mot_de_passe(mdp_resp, compte["hash"]):
                        st.session_state.responsable_connecte=True
                        st.session_state.responsable_actif=identifiant
                        reinitialiser_echecs("responsable")
                        st.success(f"Accès responsable validé : {compte['nom']}")
                        if st.session_state.get("responsable_dernier_log")!=identifiant:
                            st.session_state.responsable_dernier_log=identifiant
                            now_str=datetime.datetime.now(TZ).strftime("%d/%m/%Y %H:%M")
                            sheets_append("Logs",[now_str,f"{identifiant.lower()}@responsable"])
                    else:
                        st.session_state.responsable_connecte=False
                        st.session_state.responsable_actif=None
                        enregistrer_echec("responsable")
                        st.error("Identifiant ou mot de passe incorrect")
                else:
                    st.session_state.responsable_connecte=False
                    st.session_state.responsable_actif=None
    return role, password_correct, RESPONSABLES
