"""Calendrier de contrôle réglementaire : calculs d'échéances et taux de réalisation."""

import datetime

import pandas as pd

from tpr.config import CI_CODES, NB_JOURS_VISITE, ORDRE_CI, PERIODICITE


def construire_calendrier_controle(df_rapports: pd.DataFrame, annee_reference: int = None) -> pd.DataFrame:
    if annee_reference is None:
        annee_reference = datetime.date.today().year
    if df_rapports.empty:
        return pd.DataFrame()

    col_ins       = [c for c in df_rapports.columns if "ins" in c.lower()]
    col_date      = [c for c in df_rapports.columns if "date" in c.lower()
                      and "reelle" not in c.lower() and "réelle" not in c.lower()
                      and "prochaine" not in c.lower() and "planifi" not in c.lower()]
    col_site      = [c for c in df_rapports.columns if "site" in c.lower()]
    col_reelle    = [c for c in df_rapports.columns if "reelle" in c.lower() or "réelle" in c.lower()]
    col_prochaine = [c for c in df_rapports.columns if "prochaine" in c.lower()]

    if not (col_ins and col_date and col_site):
        return pd.DataFrame()

    df = df_rapports.copy()
    df["_date_brute"]  = pd.to_datetime(df[col_date[0]], dayfirst=True, errors="coerce")
    df["_date_reelle"] = pd.to_datetime(df[col_reelle[0]], dayfirst=True, errors="coerce") if col_reelle else pd.NaT
    df["_date_prochaine_manuelle"] = (pd.to_datetime(df[col_prochaine[0]], dayfirst=True, errors="coerce")
                                       if col_prochaine else pd.NaT)
    df["_date"] = df["_date_reelle"].combine_first(df["_date_brute"])
    df = df.dropna(subset=["_date"])
    df["_site"] = df[col_site[0]].astype(str).str.strip().str.upper()
    df["_installation"] = df[col_ins[0]].astype(str).str.strip()

    col_realisation = f"Réalisation {annee_reference}"
    lignes = []

    for site in ("MEG", "SGB"):
        df_site = df[df["_site"] == site]
        for installation in ORDRE_CI:
            attendu = round(12 / PERIODICITE.get(installation, 12)) 
            df_grp = df_site[df_site["_installation"] == installation].sort_values("_date")

            dates_realisees = sorted(df_grp["_date"].dropna().unique())[-attendu:] if not df_grp.empty else []

            nb_realisees_annee = df_grp[df_grp["_date"].dt.year == annee_reference]["_date"].nunique()
            pct = round(min(nb_realisees_annee, attendu) / attendu * 100) if attendu else 0
            realisation_txt = f"{pct}%" if nb_realisees_annee > 0 else "A planifier"

            periodicite_mois = PERIODICITE.get(installation, 12)
            if not df_grp.empty and df_grp["_date_prochaine_manuelle"].notna().any():
                dates_planifiees = sorted(df_grp["_date_prochaine_manuelle"].dropna().unique())[-attendu:]
            else:
                dates_planifiees = [pd.Timestamp(d) + pd.DateOffset(months=periodicite_mois) for d in dates_realisees]

            lignes.append({
                "Site": site,
                "CI": CI_CODES.get(installation, ""),
                "Installation": installation,
                "Nbr visite/An": attendu,
                "Nbr jour": NB_JOURS_VISITE.get(site, {}).get(installation, "-"),
                "Dates réalisées": (" | ".join(pd.Timestamp(d).strftime("%d/%m/%Y") for d in dates_realisees)
                                     if len(dates_realisees) else "-"),
                col_realisation: realisation_txt,
                "Dates planifiées": "-",
                "Nbr visites réalisées en 2026": min(nb_realisees_annee, attendu), 
                "_dates_planifiees": list(dates_planifiees),
            })

    # Repère, sur l'ensemble du calendrier (tous sites/installations confondus), la SEULE
    # date planifiée la plus proche de la date du jour (= prochaine échéance à réaliser en priorité)
    # pour y accoler un petit symbole. Toutes les autres dates restent affichées sans symbole.
    aujourd_hui = pd.Timestamp(datetime.date.today())
    idx_ligne_proche, idx_date_proche, ecart_min = None, None, None
    for idx_ligne, ligne in enumerate(lignes):
        for idx_date, d in enumerate(ligne["_dates_planifiees"]):
            ecart = abs((pd.Timestamp(d) - aujourd_hui).days)
            if ecart_min is None or ecart < ecart_min:
                ecart_min, idx_ligne_proche, idx_date_proche = ecart, idx_ligne, idx_date

    for idx_ligne, ligne in enumerate(lignes):
        dates_planifiees = ligne.pop("_dates_planifiees")
        if len(dates_planifiees):
            ligne["Dates planifiées"] = " | ".join(
                (f"★ {pd.Timestamp(d).strftime('%d/%m/%Y')}"
                 if (idx_ligne == idx_ligne_proche and idx_date == idx_date_proche)
                 else pd.Timestamp(d).strftime("%d/%m/%Y"))
                for idx_date, d in enumerate(dates_planifiees)
            )
        else:
            ligne["Dates planifiées"] = "-"

    return pd.DataFrame(lignes)

# ⚠️ Streamlit n'exécute du code que lorsqu'une page est ouverte/interagie : il n'y a pas
# de tâche planifiée en arrière-plan ici. Le bouton de relance (onglet Statistiques) doit
# donc être déclenché manuellement par un administrateur, ou automatisé de l'extérieur
# (ex. une tâche planifiée GitHub Actions / cron qui appelle un petit script Python
# réutilisant ces mêmes fonctions, indépendamment de l'app Streamlit).
def extraire_echeances_proches(df_calendrier: pd.DataFrame, jours_horizon: int = 30) -> list:
    """Parcourt la colonne 'Dates planifiées' du calendrier et retourne la liste des échéances
    en retard ou à venir dans les `jours_horizon` prochains jours : [{Site, Installation, Date, Jours}]."""
    if df_calendrier.empty or "Dates planifiées" not in df_calendrier.columns:
        return []
    aujourd_hui = pd.Timestamp(datetime.date.today())
    resultats = []
    for _, row in df_calendrier.iterrows():
        brut = str(row.get("Dates planifiées", "") or "")
        if brut in ("", "-"):
            continue
        for morceau in brut.split("|"):
            morceau = morceau.replace("★", "").strip()
            try:
                d = pd.to_datetime(morceau, format="%d/%m/%Y")
            except Exception:
                continue
            jours = (d - aujourd_hui).days
            if jours <= jours_horizon:
                resultats.append({"Site": row.get("Site", ""), "Installation": row.get("Installation", ""),
                                   "Date": d.strftime("%d/%m/%Y"), "Jours": int(jours)})
    resultats.sort(key=lambda r: r["Jours"])
    return resultats

def construire_message_relance(echeances: list) -> str:
    if not echeances:
        return "Aucune échéance de contrôle réglementaire en retard ou à venir dans les 30 prochains jours."
    lignes = ["Echéances de contrôle réglementaire à surveiller :", ""]
    for e in echeances:
        if e["Jours"] < 0:
            statut = f"⚠️ EN RETARD de {abs(e['Jours'])} jour(s)"
        elif e["Jours"] == 0:
            statut = "📅 Aujourd'hui"
        else:
            statut = f"A venir dans {e['Jours']} jour(s)"
        lignes.append(f"[{e['Site']}] {e['Installation']} — prévue le {e['Date']} ({statut})")
    lignes.append("")
    lignes.append("Merci de vérifier la planification correspondante dans le Tableau de Bord Réglementaire.")
    return "\n".join(lignes)

def calculer_taux_realisation(df_calendrier: pd.DataFrame) -> dict:
    if df_calendrier.empty or "Nbr visites réalisées en 2026" not in df_calendrier.columns:
        return {"MEG": 0.0, "SGB": 0.0, "Global": 0.0}

    resultat = {}
    for site in ("MEG", "SGB"):
        df_site = df_calendrier[df_calendrier["Site"] == site]
        attendu_total = df_site["Nbr visite/An"].sum()
        realise_total = df_site["Nbr visites réalisées en 2026"].sum()
        resultat[site] = round(realise_total / attendu_total * 100, 1) if attendu_total else 0.0

    attendu_global = df_calendrier["Nbr visite/An"].sum()
    realise_global = df_calendrier["Nbr visites réalisées en 2026"].sum()
    resultat["Global"] = round(realise_global / attendu_global * 100, 1) if attendu_global else 0.0
    return resultat
