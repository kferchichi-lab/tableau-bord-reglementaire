"""Accès aux données métier (onglets Google Sheets)."""

import datetime

import pandas as pd
import requests
import streamlit as st

from tpr.config import NATURE_PILOTE, SEUIL_EN_LIGNE_SECONDES, SHEET_ID, TZ, URL_GOOGLE_SHEET
from tpr.services.audit import journaliser_action, utilisateur_courant
from tpr.services.google_auth import obtenir_access_token
from tpr.services.sheets import _valeur_sheet, sheets_append, sheets_append_multiple, sheets_lire, sheets_trouver_ligne_email


@st.cache_data(ttl=30)
def charger_donnees_sheet(nom_onglet):
    try:
        base_url = URL_GOOGLE_SHEET.split("/edit")[0]
        df = pd.read_csv(f"{base_url}/gviz/tq?tqx=out:csv&sheet={nom_onglet}")
        return df.dropna(how='all')
    except Exception:
        return pd.DataFrame()

def _cle_action(row):
    """Clé unique identifiant une action précise, utilisée pour repérer les actions déjà réalisées."""
    return "||".join(str(row.get(c, "")).strip().upper() for c in
                      ["Site", "Installation", "Désignation", "Observation", "Code"])

def lire_actions_realisees():
    """Lit l'onglet ActionsRealisees : Site | Installation | Désignation | Observation | Code | Pilote | Responsable | DateRealisation."""
    return sheets_lire("ActionsRealisees", "A:H")

def marquer_actions_realisees(df_lignes, responsable_nom):
    """Enregistre toutes les actions cochées comme réalisées en UN SEUL appel réseau
    (au lieu d'un appel par action, ce qui rendait l'enregistrement très lent).
    Retourne (ok_total, liste_des_messages_erreur)."""
    if df_lignes.empty:
        return True, []
    date_str = datetime.datetime.now(TZ).strftime("%d/%m/%Y %H:%M")
    lignes_a_ecrire = [
        [
            _valeur_sheet(row.get("Site", "")), _valeur_sheet(row.get("Installation", "")),
            _valeur_sheet(row.get("Désignation", "")), _valeur_sheet(row.get("Observation", "")),
            _valeur_sheet(row.get("Code", "")), _valeur_sheet(row.get("Pilote", "")),
            responsable_nom, date_str
        ]
        for _, row in df_lignes.iterrows()
    ]
    ok, msg = sheets_append_multiple("ActionsRealisees", lignes_a_ecrire)
    erreurs = [] if ok else [msg]
    if ok:
        journaliser_action(utilisateur_courant(), "Action marquée réalisée",
                            f"{len(df_lignes)} action(s), pilote={responsable_nom}")
    return ok, erreurs

def lire_suivi_encours():
    """Lit l'onglet SuiviActions : Site | Installation | Désignation | Observation | Code | Pilote |
    Statut | Type | Commentaire | Responsable | DateMaJ.
    Ne garde que la dernière saisie connue pour chaque action (une action peut être mise à jour
    plusieurs fois : seule la ligne la plus récente fait foi)."""
    df = sheets_lire("SuiviActions", "A:K")
    if df.empty:
        return df
    df["Cle"] = df.apply(_cle_action, axis=1)
    df = df.drop_duplicates(subset="Cle", keep="last").reset_index(drop=True)
    return df

def enregistrer_statut_en_cours(row, type_suivi, commentaire, responsable_nom):
    """Enregistre (nouvelle ligne d'historique) le statut « En cours » d'une action, avec son type
    de suivi (Immédiat / Sous-traitance / Planifié) et un commentaire libre facultatif."""
    date_str = datetime.datetime.now(TZ).strftime("%d/%m/%Y %H:%M")
    ok, msg = sheets_append("SuiviActions", [
        _valeur_sheet(row.get("Site", "")), _valeur_sheet(row.get("Installation", "")),
        _valeur_sheet(row.get("Désignation", "")), _valeur_sheet(row.get("Observation", "")),
        _valeur_sheet(row.get("Code", "")), _valeur_sheet(row.get("Pilote", "")),
        "En cours", _valeur_sheet(type_suivi), _valeur_sheet(commentaire), responsable_nom, date_str
    ])
    if ok:
        journaliser_action(utilisateur_courant(), "Action mise à jour (En cours)",
                            f"{row.get('Code','')} — {type_suivi} — pilote={responsable_nom}")
    return ok, msg

def enregistrer_statuts_en_cours_lot(liste_rows_types_commentaires, responsable_nom):
    """Version groupée d'enregistrer_statut_en_cours : enregistre plusieurs mises à jour
    « En cours » en UN SEUL appel réseau au lieu d'un appel par ligne.
    liste_rows_types_commentaires : liste de tuples (row, type_suivi, commentaire).
    Retourne (ok_total, liste_des_messages_erreur)."""
    if not liste_rows_types_commentaires:
        return True, []
    date_str = datetime.datetime.now(TZ).strftime("%d/%m/%Y %H:%M")
    lignes_a_ecrire = [
        [
            _valeur_sheet(row.get("Site", "")), _valeur_sheet(row.get("Installation", "")),
            _valeur_sheet(row.get("Désignation", "")), _valeur_sheet(row.get("Observation", "")),
            _valeur_sheet(row.get("Code", "")), _valeur_sheet(row.get("Pilote", "")),
            "En cours", _valeur_sheet(type_suivi), _valeur_sheet(commentaire), responsable_nom, date_str
        ]
        for (row, type_suivi, commentaire) in liste_rows_types_commentaires
    ]
    ok, msg = sheets_append_multiple("SuiviActions", lignes_a_ecrire)
    if ok:
        for (row, type_suivi, _c) in liste_rows_types_commentaires:
            journaliser_action(utilisateur_courant(), "Action mise à jour (En cours)",
                                f"{row.get('Code','')} — {type_suivi} — pilote={responsable_nom}")
    return ok, ([] if ok else [msg])

def ecrire_log(email):
    maintenant = datetime.datetime.now(TZ).strftime("%d/%m/%Y %H:%M")
    return sheets_append("Logs",[maintenant,email])

def mettre_a_jour_presence(email):
    maintenant = datetime.datetime.now(TZ).strftime("%d/%m/%Y %H:%M:%S")
    ligne = sheets_trouver_ligne_email("Presence",email)
    if ligne:
        token = obtenir_access_token()
        if token:
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/Presence!B{ligne}:C{ligne}"
            requests.put(url,headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},
                params={"valueInputOption":"RAW"},json={"values":[[maintenant,"En ligne"]]},timeout=15)
    else:
        sheets_append("Presence",[email,maintenant,"En ligne"])

def visiteur_deja_verifie(email: str) -> bool:
    """Retourne True si cet e-mail figure déjà dans l'onglet 'Presence', c.-à-d. qu'il
    s'agit d'un visiteur déjà connu (première vérification OTP déjà effectuée par le passé).
    Dans ce cas, on ne renvoie plus de code : l'accès est direct, mais on continue à
    tracer sa présence/historique comme pour n'importe quelle connexion."""
    return sheets_trouver_ligne_email("Presence", email) is not None

def lire_presence():
    df = sheets_lire("Presence","A:C")
    if df.empty: return pd.DataFrame(columns=["Email","Derniere_activite","Statut","Activite"])
    maintenant = datetime.datetime.now(TZ)
    resultats = []
    for _,row in df.iterrows():
        email=row.get("Email",""); derniere=row.get("Derniere_activite","")
        try:
            dt=TZ.localize(datetime.datetime.strptime(derniere,"%d/%m/%Y %H:%M:%S"))
            delta=(maintenant-dt).total_seconds()
            if delta<SEUIL_EN_LIGNE_SECONDES: statut="🟢 En ligne"; activite="Actif maintenant"
            elif delta<300:
                m=int(delta//60); statut="🟡 Récemment actif"; activite=f"Actif il y a {m} min" if m>0 else "Actif il y a quelques secondes"
            else:
                m=int(delta//60); h=int(m//60); statut="🔴 Hors ligne"
                activite=f"Vu il y a {h}h{m%60:02d}" if h>0 else f"Vu il y a {m} min"
        except Exception:
            statut="⚪ Inconnu"; activite=derniere
        resultats.append({"Email":email,"Dernière activité":derniere,"Statut":statut,"Activité":activite})
    return pd.DataFrame(resultats)

def lire_logs():
    return sheets_lire("Logs","A:B")

def lire_audit_log():
    """Lit l'onglet AuditLog : Date | Utilisateur | Action | Détails.
    (Onglet à créer manuellement dans le Google Sheet s'il n'existe pas encore.)"""
    return sheets_lire("AuditLog", "A:D")

def lire_exigences():
    """Lit l'onglet Exigences."""
    return sheets_lire("Exigences", "A:F")

def ecrire_contrat(lien_pdf):
    """Met à jour ou crée la ligne du contrat dans l'onglet Exigences."""
    df = lire_exigences()
    token = obtenir_access_token()
    if not token:
        return False, "Token invalide"

    if not df.empty and "Type" in df.columns:
        ligne_contrat = df[df["Type"] == "Contrat"]
        if not ligne_contrat.empty:
            num_ligne = ligne_contrat.index[0] + 2
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/Exigences!F{num_ligne}"
            resp = requests.put(url,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                params={"valueInputOption": "RAW"},
                json={"values": [[lien_pdf]]}, timeout=15)
            ok = (resp.status_code == 200)
            if ok:
                journaliser_action(utilisateur_courant(), "Contrat mis à jour", lien_pdf)
            return ok, ""

    ok, msg = sheets_append("Exigences", ["Contrat", "", "", "", "", lien_pdf])
    if ok:
        journaliser_action(utilisateur_courant(), "Contrat créé", lien_pdf)
    return ok, msg

def supprimer_contrat():
    """Vide le lien du contrat."""
    df = lire_exigences()
    token = obtenir_access_token()
    if not token or df.empty or "Type" not in df.columns:
        return False
    ligne_contrat = df[df["Type"] == "Contrat"]
    if ligne_contrat.empty:
        return False
    num_ligne = ligne_contrat.index[0] + 2
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/Exigences!F{num_ligne}"
    resp = requests.put(url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        params={"valueInputOption": "RAW"},
        json={"values": [[""]]}, timeout=15)
    ok = resp.status_code == 200
    if ok:
        journaliser_action(utilisateur_courant(), "Contrat supprimé")
    return ok

def ajouter_equipement(site, installation, sous_eq, nombre):
    """Ajoute une ligne équipement dans Exigences."""
    ok, msg = sheets_append("Exigences", ["Equipement", site, installation, sous_eq, str(nombre), ""])
    if ok:
        journaliser_action(utilisateur_courant(), "Equipement ajouté", f"{site} / {installation} / {sous_eq} x{nombre}")
    return ok, msg

def supprimer_equipement_ligne(num_ligne_sheet):
    """Vide une ligne équipement (remplace par des cellules vides)."""
    token = obtenir_access_token()
    if not token: return False
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/Exigences!A{num_ligne_sheet}:F{num_ligne_sheet}"
    resp = requests.put(url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        params={"valueInputOption": "RAW"},
        json={"values": [["", "", "", "", "", ""]]}, timeout=15)
    ok = resp.status_code == 200
    if ok:
        journaliser_action(utilisateur_courant(), "Equipement supprimé", f"ligne {num_ligne_sheet}")
    return ok

def lire_points_reserve():
    """Lit l'onglet PointsReserve : Site | Installation | Sous_equipement | Nombre."""
    return sheets_lire("PointsReserve", "A:D")

def ajouter_point_reserve(site, installation, sous_eq, nombre):
    """Ajoute une ligne dans l'onglet PointsReserve."""
    ok, msg = sheets_append("PointsReserve", [site, installation, sous_eq, str(nombre)])
    if ok:
        journaliser_action(utilisateur_courant(), "Point de réserve ajouté", f"{site} / {installation} / {sous_eq} x{nombre}")
    return ok, msg

def lire_points_reserve_nature():
    """Lit l'onglet PointsReserveNature : Site | Installation | Nombre | Nature | Pilote."""
    return sheets_lire("PointsReserveNature", "A:E")

def ajouter_point_reserve_nature(site, installation, nombre, code_nature):
    """Ajoute une ligne dans l'onglet PointsReserveNature. Le pilote est calculé depuis le code de la nature."""
    nature_nom, pilote = NATURE_PILOTE[code_nature]
    ok, msg = sheets_append("PointsReserveNature", [site, installation, str(nombre), nature_nom, pilote])
    if ok:
        journaliser_action(utilisateur_courant(), "Point de réserve (nature) ajouté", f"{site} / {installation} — {nature_nom} x{nombre}")
    return ok, msg

def supprimer_ligne_generique(onglet, num_ligne_sheet, nb_colonnes):
    """Vide une ligne (remplace par des cellules vides) dans un onglet donné, sur nb_colonnes colonnes (A..)."""
    token = obtenir_access_token()
    if not token: return False
    derniere_col = chr(ord('A') + nb_colonnes - 1)
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{onglet}!A{num_ligne_sheet}:{derniere_col}{num_ligne_sheet}"
    resp = requests.put(url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        params={"valueInputOption": "RAW"},
        json={"values": [[""] * nb_colonnes]}, timeout=15)
    ok = resp.status_code == 200
    if ok:
        journaliser_action(utilisateur_courant(), "Ligne supprimée", f"onglet={onglet}, ligne={num_ligne_sheet}")
    return ok
