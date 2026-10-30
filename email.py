"""Envoi d'e-mails via SMTP (code OTP visiteur, relances)."""

import smtplib
from email.mime.text import MIMEText

import streamlit as st


def envoyer_email(destinataire: str, sujet: str, corps_texte: str) -> tuple:
    """Envoie un e-mail texte simple via SMTP. Retourne (succes: bool, erreur: str|None)."""
    try:
        cfg = st.secrets["smtp"]
    except Exception:
        return False, "Configuration SMTP absente (section [smtp] manquante dans secrets.toml)."
    try:
        msg = MIMEText(corps_texte, "plain", "utf-8")
        msg["Subject"] = sujet
        msg["From"] = cfg.get("expediteur", cfg.get("utilisateur"))
        msg["To"] = destinataire
        with smtplib.SMTP(cfg["host"], int(cfg.get("port", 587)), timeout=15) as serveur:
            serveur.starttls()
            serveur.login(cfg["utilisateur"], cfg["mot_de_passe"])
            serveur.sendmail(msg["From"], [destinataire], msg.as_string())
        return True, None
    except Exception as e:
        return False, str(e)
