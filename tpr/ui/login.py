"""Connexion visiteur par code à usage unique (OTP) envoyé par e-mail."""

import hmac
import secrets as secrets_lib
import time

import streamlit as st

from tpr.core.security import enregistrer_echec, format_email_valide, reinitialiser_echecs, tentative_bloquee
from tpr.services.email import envoyer_email
from tpr.services.repository import ecrire_log, mettre_a_jour_presence, visiteur_deja_verifie


def render_login_visiteur():
    # ---- Vérification réelle de l'adresse e-mail par code à usage unique (OTP) ----
    # Étape 1 : l'utilisateur saisit son e-mail et reçoit un code à 6 chiffres (valable 10 min).
    # Étape 2 : il doit saisir ce code pour prouver qu'il possède bien cette boîte e-mail.
    if "otp_code" not in st.session_state: st.session_state.otp_code = None
    if "otp_email" not in st.session_state: st.session_state.otp_email = None
    if "otp_expire_a" not in st.session_state: st.session_state.otp_expire_a = 0
    if "otp_dernier_envoi" not in st.session_state: st.session_state.otp_dernier_envoi = 0

    otp_deja_envoye = st.session_state.otp_code is not None and time.time() < st.session_state.otp_expire_a

    if not otp_deja_envoye:
        st.markdown("""<div style="margin-bottom:14px;">
            <p style="color:#0F172A;font-size:15px;font-weight:700;margin:0 0 6px 0;">Adresse e-mail :</p>
            <p style="color:#64748B;font-size:13.5px;margin:0;line-height:1.5;">Lors de votre première connexion, un code de vérification à 6 chiffres vous sera envoyé par e-mail. Les fois suivantes, l'accès est direct.</p>
        </div>""",unsafe_allow_html=True)
        email_saisi=st.text_input("Adresse e-mail :",placeholder="exemple@domain.com",label_visibility="collapsed",key="otp_email_input")
        blocage_otp = tentative_bloquee("otp")
        if blocage_otp > 0:
            st.error(f"🔒 Trop de tentatives échouées. Réessaie dans {blocage_otp} s.")
        elif st.button("Continuer",type="primary"):
            if not format_email_valide(email_saisi):
                st.error("Veuillez saisir une adresse e-mail valide.")
            elif visiteur_deja_verifie(email_saisi):
                # ---- Visiteur déjà connu (déjà vérifié par le passé) : accès direct, sans nouveau code ----
                # On garde malgré tout la traçabilité (log + présence) pour l'historique.
                st.session_state.email_visiteur=email_saisi
                with st.spinner("Enregistrement de votre accès..."):
                    succes,erreur=ecrire_log(email_saisi)
                    mettre_a_jour_presence(email_saisi)
                if succes:
                    st.success("✅ Bon retour ! Accès accordé.")
                    st.rerun()
                else:
                    st.error(f"❌ Erreur d'enregistrement : {erreur}")
                    st.stop()
            elif time.time() - st.session_state.otp_dernier_envoi < 60:
                st.warning("Merci de patienter avant de redemander un code.")
            else:
                code = f"{secrets_lib.randbelow(1_000_000):06d}"
                succes_envoi, erreur_envoi = envoyer_email(
                    email_saisi,
                    "Votre code d'accès — Tableau de Bord Réglementaire",
                    f"Votre code de vérification est : {code}\n\nCe code est valable 10 minutes.\nSi vous n'êtes pas à l'origine de cette demande, ignorez cet e-mail."
                )
                if succes_envoi:
                    st.session_state.otp_code = code
                    st.session_state.otp_email = email_saisi
                    st.session_state.otp_expire_a = time.time() + 600
                    st.session_state.otp_dernier_envoi = time.time()
                    st.success("✅ Code envoyé. Vérifiez votre boîte e-mail (et vos spams).")
                    st.rerun()
                elif "Configuration SMTP absente" in (erreur_envoi or ""):
                    # Repli si l'administrateur n'a pas encore configuré le SMTP : on ne bloque
                    # pas l'accès, mais on ne peut pas garantir que l'adresse est vérifiée.
                    st.session_state.email_visiteur=email_saisi
                    with st.spinner("Enregistrement de votre accès..."):
                        succes,erreur=ecrire_log(email_saisi)
                        mettre_a_jour_presence(email_saisi)
                    st.warning("⚠️ Vérification par code indisponible (SMTP non configuré côté administrateur) — accès accordé sans confirmation de l'e-mail.")
                    st.rerun()
                else:
                    st.error(f"❌ Impossible d'envoyer le code : {erreur_envoi}")
    else:
        st.markdown(f"""<div style="margin-bottom:14px;">
            <p style="color:#0F172A;font-size:15px;font-weight:700;margin:0 0 6px 0;">Code de vérification :</p>
            <p style="color:#64748B;font-size:13.5px;margin:0;line-height:1.5;">Un code a été envoyé à {st.session_state.otp_email}. Saisissez-le ci-dessous.</p>
        </div>""",unsafe_allow_html=True)
        code_saisi = st.text_input("Code :",placeholder="123456",label_visibility="collapsed",max_chars=6,key="otp_code_input")
        c_valider, c_renvoyer = st.columns(2)
        with c_valider:
            if st.button("Valider le code",type="primary",use_container_width=True):
                if code_saisi and hmac.compare_digest(code_saisi.strip(), st.session_state.otp_code):
                    email_confirme = st.session_state.otp_email
                    st.session_state.email_visiteur=email_confirme
                    st.session_state.otp_code = None
                    st.session_state.otp_email = None
                    reinitialiser_echecs("otp")
                    with st.spinner("Enregistrement de votre accès..."):
                        succes,erreur=ecrire_log(email_confirme)
                        mettre_a_jour_presence(email_confirme)
                    if succes:
                        st.success("✅ Accès accordé. Bienvenue !")
                        st.rerun()
                    else:
                        st.error(f"❌ Erreur d'enregistrement : {erreur}")
                        st.stop()
                else:
                    enregistrer_echec("otp")
                    st.error("Code incorrect.")
        with c_renvoyer:
            if st.button("↻ Renvoyer / changer d'e-mail",use_container_width=True):
                st.session_state.otp_code = None
                st.session_state.otp_email = None
                st.rerun()
