"""Onglet « Planification » (calendrier de contrôle)."""

import calendar
import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from tpr.config import COULEURS_INS, MOIS_FR, PERIODICITE, SOUS_EQUIPEMENTS
from tpr.core.security import format_email_valide
from tpr.domain.calendrier import (
    calculer_taux_realisation,
    construire_calendrier_controle,
    construire_message_relance,
    extraire_echeances_proches,
)
from tpr.reports.calendrier_excel import generer_calendrier_controle_excel
from tpr.reports.calendrier_pdf import generer_calendrier_controle_pdf
from tpr.services.audit import journaliser_action, utilisateur_courant
from tpr.services.email import envoyer_email
from tpr.services.sheets import sheets_ecrire_cellule_v2


def render(ctx):
    df_rapports = ctx.df_rapports
    password_correct = ctx.password_correct
    role = ctx.role
    st.markdown("<br><p style='font-size:1.2rem;font-weight:700;color:#0F172A;'>📅 Prochaines échéances</p>",unsafe_allow_html=True)

    # ---- FILTRES ÉCHÉANCES ----
    with st.container(border=True):
        st.markdown("<p style='font-weight:600;color:#1E293B;margin:0 0 10px 0;font-size:13px;'>🔍 Filtrer les échéances</p>",unsafe_allow_html=True)
        fc1,fc2,fc3=st.columns(3)
        with fc1: f_ech_site=st.selectbox("Site",["Tous","SGB","MEG"],key="f_ech_site")
        with fc2: f_ech_ins =st.selectbox("Installation",["Tous"]+list(PERIODICITE.keys()),key="f_ech_ins")
        with fc3:
            opts_seq=["Tous"]+SOUS_EQUIPEMENTS.get(f_ech_ins,[]) if f_ech_ins!="Tous" else ["Tous"]+[i for sub in SOUS_EQUIPEMENTS.values() for i in sub]
            f_ech_seq=st.selectbox("Sous-équipement",opts_seq,key="f_ech_seq")

    if not df_rapports.empty:
        col_ins_r  =[c for c in df_rapports.columns if "ins" in c.lower()]
        col_date_r =[c for c in df_rapports.columns if "date" in c.lower() and "reelle" not in c.lower() and "réelle" not in c.lower() and "prochaine" not in c.lower()]
        col_site_r =[c for c in df_rapports.columns if "site" in c.lower()]
        col_label_r=[c for c in df_rapports.columns if "equip" in c.lower() or "label" in c.lower() or "nom" in c.lower()]
        col_reelle =[c for c in df_rapports.columns if "reelle" in c.lower() or "réelle" in c.lower()]
        col_prochaine_r=[c for c in df_rapports.columns if "prochaine" in c.lower()]

        if col_ins_r and col_date_r:
            df_ech=df_rapports.copy()
            # Identifiant stable = numéro de ligne réel dans le Sheet (header=ligne1, donc +2)
            df_ech["_ligne_sheet"]=df_ech.index+2
            df_ech["_date_brute"]=pd.to_datetime(df_ech[col_date_r[0]],dayfirst=True,errors='coerce')

            if col_reelle:
                df_ech["_date_reelle"]=pd.to_datetime(df_ech[col_reelle[0]],dayfirst=True,errors='coerce')
            else:
                df_ech["_date_reelle"]=pd.NaT

            if col_prochaine_r:
                df_ech["_prochaine_manuelle"]=pd.to_datetime(df_ech[col_prochaine_r[0]],dayfirst=True,errors='coerce')
            else:
                df_ech["_prochaine_manuelle"]=pd.NaT

            # Date de dernière visite = date réelle si dispo, sinon date planifiée initiale
            df_ech["_date"]=df_ech["_date_reelle"].combine_first(df_ech["_date_brute"])
            df_ech=df_ech.dropna(subset=["_date"])

            # Déduplication
            cles=[]
            if col_site_r:  cles.append(col_site_r[0])
            cles.append(col_ins_r[0])
            if col_label_r: cles.append(col_label_r[0])
            df_ech=df_ech.sort_values("_date_brute",ascending=True)
            df_ech=df_ech.drop_duplicates(subset=cles,keep="last")

            today_dt=pd.Timestamp.today().normalize()

            def calc_prochaine(row):
                # Priorité à une échéance saisie manuellement par le responsable,
                # sinon calcul automatique selon la périodicité de l'installation
                if pd.notna(row["_prochaine_manuelle"]):
                    return row["_prochaine_manuelle"]
                mois=PERIODICITE.get(str(row[col_ins_r[0]]).strip(),12)
                return row["_date"]+pd.DateOffset(months=mois)

            df_ech["Prochaine échéance"]=df_ech.apply(calc_prochaine,axis=1)
            df_ech["Jours restants"]=(df_ech["Prochaine échéance"]-today_dt).dt.days
            df_ech["Statut"]=df_ech["Jours restants"].apply(
                lambda j:"⚠️ Dépassé" if j<0 else "🔴 Urgent" if j<30 else "🟡 Proche" if j<90 else "🟢 OK")

            cols_affich=[]
            if col_site_r:  cols_affich.append(col_site_r[0])
            if col_label_r: cols_affich.append(col_label_r[0])
            cols_affich+=[col_ins_r[0],"_date_reelle","Prochaine échéance","Jours restants","Statut","_ligne_sheet"]
            df_show=df_ech[cols_affich].sort_values("Prochaine échéance")

            # ---- APPLICATION DES FILTRES ----
            df_show_filtre=df_show.copy()
            if f_ech_site!="Tous" and col_site_r:
                df_show_filtre=df_show_filtre[df_show_filtre[col_site_r[0]].astype(str).str.strip()==f_ech_site]
            if f_ech_ins!="Tous" and col_ins_r:
                df_show_filtre=df_show_filtre[df_show_filtre[col_ins_r[0]].astype(str).str.strip()==f_ech_ins]
            if f_ech_seq!="Tous" and col_label_r:
                df_show_filtre=df_show_filtre[df_show_filtre[col_label_r[0]].astype(str).str.strip().str.contains(f_ech_seq,case=False,na=False)]

            # KPIs statut
            nb_depasse=len(df_show_filtre[df_show_filtre["Statut"]=="⚠️ Dépassé"])
            nb_urgent =len(df_show_filtre[df_show_filtre["Statut"]=="🔴 Urgent"])
            nb_proche =len(df_show_filtre[df_show_filtre["Statut"]=="🟡 Proche"])
            nb_ok     =len(df_show_filtre[df_show_filtre["Statut"]=="🟢 OK"])

            kf1,kf2,kf3,kf4=st.columns(4)
            with kf1:
                st.markdown(f"""<div style="background:#FEF2F2;padding:10px;border-radius:8px;border-left:3px solid #EF4444;margin-bottom:12px;">
                    <p style="margin:0;font-size:10px;color:#7F1D1D;font-weight:600;text-transform:uppercase;">⚠️ Dépassé</p>
                    <p style="margin:2px 0 0 0;font-size:22px;color:#991B1B;font-weight:700;">{nb_depasse}</p></div>""",unsafe_allow_html=True)
            with kf2:
                st.markdown(f"""<div style="background:#FFF1F0;padding:10px;border-radius:8px;border-left:3px solid #e34948;margin-bottom:12px;">
                    <p style="margin:0;font-size:10px;color:#7F1D1D;font-weight:600;text-transform:uppercase;">🔴 Urgent</p>
                    <p style="margin:2px 0 0 0;font-size:22px;color:#e34948;font-weight:700;">{nb_urgent}</p></div>""",unsafe_allow_html=True)
            with kf3:
                st.markdown(f"""<div style="background:#FFFBEB;padding:10px;border-radius:8px;border-left:3px solid #eda100;margin-bottom:12px;">
                    <p style="margin:0;font-size:10px;color:#78350F;font-weight:600;text-transform:uppercase;">🟡 Proche</p>
                    <p style="margin:2px 0 0 0;font-size:22px;color:#eda100;font-weight:700;">{nb_proche}</p></div>""",unsafe_allow_html=True)
            with kf4:
                st.markdown(f"""<div style="background:#F0FDF4;padding:10px;border-radius:8px;border-left:3px solid #10B981;margin-bottom:12px;">
                    <p style="margin:0;font-size:10px;color:#064E3B;font-weight:600;text-transform:uppercase;">🟢 OK</p>
                    <p style="margin:2px 0 0 0;font-size:22px;color:#10B981;font-weight:700;">{nb_ok}</p></div>""",unsafe_allow_html=True)

            left_col,right_col=st.columns([1.5,1])

            # ---- COLONNE GAUCHE : TABLEAU ----
            with left_col:
                if role!="Admin" or not password_correct:
                    # Visiteur : lecture seule
                    cols_visiteur=[]
                    if col_site_r:  cols_visiteur.append(col_site_r[0])
                    if col_label_r: cols_visiteur.append(col_label_r[0])
                    cols_visiteur+=[col_ins_r[0],"_date_reelle","Prochaine échéance","Jours restants","Statut"]
                    st.dataframe(df_show_filtre[cols_visiteur],column_config={
                        "_date_reelle":       st.column_config.DateColumn("📅 Date de dernière visite",format="DD/MM/YYYY"),
                        "Prochaine échéance": st.column_config.DateColumn("⏭️ Prochaine échéance",format="DD/MM/YYYY"),
                        "Jours restants":     st.column_config.NumberColumn("Jours restants",format="%d j"),
                    },hide_index=True,use_container_width=True)
                else:
                    # Admin : édition de la date de dernière visite ET de la prochaine échéance
                    st.markdown("""<div style='background:#EFF6FF;border-left:4px solid #2a78d6;padding:10px 14px;border-radius:6px;margin-bottom:10px;'>
                        <p style='margin:0;font-size:12px;color:#1e40af;font-weight:600;'>✏️ Mode administrateur</p>
                    </div>""",unsafe_allow_html=True)
                    cols_resp=[]
                    if col_site_r:  cols_resp.append(col_site_r[0])
                    if col_label_r: cols_resp.append(col_label_r[0])
                    cols_resp+=[col_ins_r[0],"_date_reelle","Prochaine échéance","Jours restants","Statut","_ligne_sheet"]
                    df_editable=df_show_filtre[cols_resp].copy()
                    df_editable["_date_reelle"]=pd.to_datetime(df_editable["_date_reelle"],errors='coerce')
                    df_editable["Prochaine échéance"]=pd.to_datetime(df_editable["Prochaine échéance"],errors='coerce')
                    edited_df=st.data_editor(df_editable,column_config={
                        "_date_reelle":       st.column_config.DateColumn("✅ Date de dernière visite",format="DD/MM/YYYY",help="Saisissez ici la date réelle du dernier contrôle effectué"),
                        "Prochaine échéance": st.column_config.DateColumn("⏭️ Prochaine échéance",format="DD/MM/YYYY",help="Calculée automatiquement, modifiable si besoin"),
                        "Jours restants":     st.column_config.NumberColumn("Jours restants",format="%d j"),
                        "_ligne_sheet":       None,
                    },disabled=[c for c in df_editable.columns if c not in ("_date_reelle","Prochaine échéance")],hide_index=True,use_container_width=True,key="editor_dates_reelles")

                    if not col_prochaine_r:
                        st.caption("ℹ️ Pour que la « Prochaine échéance » modifiée soit conservée après actualisation, ajoutez une colonne « Prochaine_echeance » dans l'onglet « Rapports » du Google Sheet.")

                    if st.button("💾 Sauvegarder les modifications",type="primary"):
                        with st.spinner("Mise à jour dans Google Sheets..."):
                            nb_maj=0
                            erreurs=[]
                            for idx,row_edit in edited_df.iterrows():
                                num_ligne_sheet=int(row_edit["_ligne_sheet"])

                                # -- Date de dernière visite --
                                nouvelle_date=row_edit["_date_reelle"]
                                ancienne_date=df_editable.loc[idx,"_date_reelle"]
                                dates_diff=False
                                if pd.isna(nouvelle_date) and pd.isna(ancienne_date): dates_diff=False
                                elif pd.isna(nouvelle_date)!=pd.isna(ancienne_date): dates_diff=True
                                elif not pd.isna(nouvelle_date) and nouvelle_date!=ancienne_date: dates_diff=True
                                if dates_diff and not pd.isna(nouvelle_date):
                                    if col_reelle:
                                        num_col=df_rapports.columns.tolist().index(col_reelle[0])+1
                                    else:
                                        num_col=len(df_rapports.columns)+1
                                    lettre_col=chr(64+num_col)
                                    date_str=nouvelle_date.strftime("%d/%m/%Y")
                                    ok, msg = sheets_ecrire_cellule_v2("Rapports",f"{lettre_col}{num_ligne_sheet}",date_str)
                                    if ok:
                                        nb_maj+=1
                                    else:
                                        erreurs.append(f"Ligne {num_ligne_sheet}: {msg}")

                                # -- Prochaine échéance --
                                if col_prochaine_r:
                                    nouvelle_prochaine=row_edit["Prochaine échéance"]
                                    ancienne_prochaine=df_editable.loc[idx,"Prochaine échéance"]
                                    prochaine_diff=False
                                    if pd.isna(nouvelle_prochaine) and pd.isna(ancienne_prochaine): prochaine_diff=False
                                    elif pd.isna(nouvelle_prochaine)!=pd.isna(ancienne_prochaine): prochaine_diff=True
                                    elif not pd.isna(nouvelle_prochaine) and nouvelle_prochaine!=ancienne_prochaine: prochaine_diff=True

                                    # Si l'utilisateur a modifié l'échéance lui-même, cette saisie manuelle
                                    # est prioritaire. Sinon, si la date de dernière visite vient de changer,
                                    # on recalcule automatiquement l'échéance (date + périodicité) au lieu
                                    # de laisser l'ancienne valeur (potentiellement obsolète) figée dans le Sheet.
                                    if prochaine_diff and not pd.isna(nouvelle_prochaine):
                                        prochaine_a_ecrire=nouvelle_prochaine
                                    elif dates_diff and not pd.isna(nouvelle_date):
                                        mois_recalc=PERIODICITE.get(str(row_edit[col_ins_r[0]]).strip(),12)
                                        prochaine_a_ecrire=nouvelle_date+pd.DateOffset(months=mois_recalc)
                                    else:
                                        prochaine_a_ecrire=None

                                    if prochaine_a_ecrire is not None:
                                        num_col_p=df_rapports.columns.tolist().index(col_prochaine_r[0])+1
                                        lettre_col_p=chr(64+num_col_p)
                                        prochaine_str=prochaine_a_ecrire.strftime("%d/%m/%Y")
                                        ok_p, msg_p = sheets_ecrire_cellule_v2("Rapports",f"{lettre_col_p}{num_ligne_sheet}",prochaine_str)
                                        if ok_p:
                                            nb_maj+=1
                                        else:
                                            erreurs.append(f"Ligne {num_ligne_sheet} (prochaine échéance): {msg_p}")
                        if nb_maj>0:
                            st.success(f"✅ {nb_maj} modification(s) enregistrée(s) !")
                        if erreurs:
                            st.error("❌ Erreurs : " + " | ".join(erreurs))
                        if nb_maj>0 or erreurs:
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.info("Aucune modification détectée.")

            # ---- COLONNE DROITE : CALENDRIER ----
            with right_col:
                m_view=st.session_state.cal_mois
                a_view=st.session_state.cal_annee

                nav1,nav2,nav3=st.columns([1,3,1])
                with nav1:
                    if st.button("◀",key="prev_month"):
                        if st.session_state.cal_mois==1: st.session_state.cal_mois=12; st.session_state.cal_annee-=1
                        else: st.session_state.cal_mois-=1
                        st.session_state.jour_selectionne=None; st.rerun()
                with nav2:
                    st.markdown(f"<p style='text-align:center;font-weight:600;font-size:14px;margin:0;padding-top:4px;'>{MOIS_FR[m_view]} {a_view}</p>",unsafe_allow_html=True)
                with nav3:
                    if st.button("▶",key="next_month"):
                        if st.session_state.cal_mois==12: st.session_state.cal_mois=1; st.session_state.cal_annee+=1
                        else: st.session_state.cal_mois+=1
                        st.session_state.jour_selectionne=None; st.rerun()

                m_view=st.session_state.cal_mois
                a_view=st.session_state.cal_annee

                # Événements du mois (sur df_ech complet, pas filtré)
                evenements={}; details_evt={}
                for _,row in df_ech.iterrows():
                    d=row["Prochaine échéance"]
                    if pd.notna(d) and d.month==m_view and d.year==a_view:
                        j=d.day; ins=str(row[col_ins_r[0]]).strip()
                        col_c=COULEURS_INS.get(ins,"#94a3b8")
                        evenements.setdefault(j,[]).append(col_c)
                        details_evt.setdefault(j,[]).append(row)

                # En-tête jours
                jours_abbr=["Lu","Ma","Me","Je","Ve","Sa","Di"]
                cols_hdr=st.columns(7)
                for i,j in enumerate(jours_abbr):
                    with cols_hdr[i]:
                        st.markdown(f"<p style='text-align:center;font-size:10px;color:#94a3b8;font-weight:500;margin:0;padding:2px 0;'>{j}</p>",unsafe_allow_html=True)

                # CSS boutons calendrier
                st.markdown("""<style>
                    section[data-testid="stSidebar"] ~ div button[kind="secondary"]{min-height:28px!important;height:28px!important;width:28px!important;border-radius:50%!important;font-size:11px!important;padding:0!important;line-height:1!important;}
                </style>""",unsafe_allow_html=True)

                today_dt2=datetime.date.today()
                for semaine in calendar.monthcalendar(a_view,m_view):
                    cols_sem=st.columns(7)
                    for i,jour in enumerate(semaine):
                        with cols_sem[i]:
                            if jour==0:
                                st.markdown("<div style='height:28px;'></div>",unsafe_allow_html=True)
                            else:
                                evts    =evenements.get(jour,[])
                                is_today=(jour==today_dt2.day and m_view==today_dt2.month and a_view==today_dt2.year)
                                is_sel  =(jour==st.session_state.jour_selectionne)
                                has_evt =len(evts)>0

                                if has_evt:
                                    bg=evts[0]
                                    outline="outline:2.5px solid #0F172A;outline-offset:1px;" if is_sel else ""
                                    st.markdown(f"<div style='width:28px;height:28px;border-radius:50%;background:{bg};color:white;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;margin:auto;margin-bottom:-30px;position:relative;z-index:1;pointer-events:none;{outline}'>{jour}</div>",unsafe_allow_html=True)
                                    if st.button("​",key=f"cal_{a_view}_{m_view}_{jour}",help=f"{len(evts)} contrôle(s)"):
                                        st.session_state.jour_selectionne=jour; st.rerun()
                                elif is_today:
                                    st.markdown(f"<div style='width:28px;height:28px;border-radius:50%;background:#1E3A8A;color:white;font-size:11px;font-weight:600;display:flex;align-items:center;justify-content:center;margin:auto;'>{jour}</div>",unsafe_allow_html=True)
                                else:
                                    st.markdown(f"<div style='width:28px;height:28px;display:flex;align-items:center;justify-content:center;margin:auto;font-size:11px;color:#334155;'>{jour}</div>",unsafe_allow_html=True)

                # Légende
                st.markdown("<div style='margin-top:12px;border-top:1px dashed #E2E8F0;padding-top:8px;'></div>",unsafe_allow_html=True)
                inss_du_mois={str(r[col_ins_r[0]]).strip() for evts_list in details_evt.values() for r in evts_list}
                for ins,couleur in COULEURS_INS.items():
                    opacity="1" if ins in inss_du_mois else "0.3"
                    st.markdown(f"""<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;opacity:{opacity};'>
                        <span style='width:10px;height:10px;border-radius:2px;background:{couleur};display:inline-block;flex-shrink:0;'></span>
                        <span style='font-size:11px;color:#475569;'>{ins}</span>
                    </div>""",unsafe_allow_html=True)

            # ---- DÉTAIL JOUR SÉLECTIONNÉ ----
            jour_sel=st.session_state.jour_selectionne
            if jour_sel and jour_sel in details_evt:
                nb_c=len(details_evt[jour_sel])
                st.markdown(f"""<div style='margin-top:20px;padding:12px 16px;background:#F0F9FF;border-left:4px solid #0EA5E9;border-radius:8px;margin-bottom:12px;'>
                    <p style='margin:0;font-size:14px;font-weight:600;color:#0C4A6E;'>📋 {nb_c} contrôle(s) planifié(s) le {jour_sel} {MOIS_FR[m_view]} {a_view}</p>
                </div>""",unsafe_allow_html=True)
                nb_cols=min(nb_c,4)
                card_cols=st.columns(nb_cols)
                for idx,row_ctrl in enumerate(details_evt[jour_sel]):
                    with card_cols[idx%nb_cols]:
                        c_ins  =str(row_ctrl[col_ins_r[0]]).strip()
                        c_site =str(row_ctrl[col_site_r[0]]).strip()  if col_site_r  else ""
                        c_label=str(row_ctrl[col_label_r[0]]).strip() if col_label_r else ""
                        c_date =row_ctrl["_date_brute"]
                        c_reel =row_ctrl["_date_reelle"]
                        c_next =row_ctrl["Prochaine échéance"]
                        c_jours=int(row_ctrl["Jours restants"])
                        c_stat =row_ctrl["Statut"]
                        c_col  =COULEURS_INS.get(c_ins,"#94a3b8")
                        date_fmt=c_date.strftime("%d/%m/%Y") if pd.notna(c_date) else "—"
                        reel_fmt=c_reel.strftime("%d/%m/%Y") if pd.notna(c_reel) else None
                        next_fmt=c_next.strftime("%d/%m/%Y") if pd.notna(c_next) else "—"
                        j_txt  =f"⚠️ {abs(c_jours)}j de retard" if c_jours<0 else f"Dans {c_jours} j"
                        if reel_fmt:
                            date_ctrl_html=(
                                "<p style='margin:0 0 2px 0;font-size:10px;color:#94a3b8;'>Date réelle visite</p>"
                                f"<p style='margin:0 0 6px 0;font-size:11px;color:#059669;font-weight:600;'>✅ {reel_fmt}</p>"
                                "<p style='margin:0 0 2px 0;font-size:10px;color:#94a3b8;'>Date planifiée initiale</p>"
                                f"<p style='margin:0 0 6px 0;font-size:11px;color:#94a3b8;text-decoration:line-through;'>{date_fmt}</p>"
                            )
                        else:
                            date_ctrl_html=(
                                "<p style='margin:0 0 2px 0;font-size:10px;color:#94a3b8;'>Date planifiée</p>"
                                f"<p style='margin:0 0 6px 0;font-size:11px;color:#334155;font-weight:500;'>{date_fmt}</p>"
                            )
                        label_html = ("<p style='margin:0 0 4px 0;font-size:11px;color:#64748B;'>⚙️ "+c_label+"</p>") if c_label else ""
                        carte_html=(
                            f"<div style='background:white;border-top:4px solid {c_col};padding:14px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-bottom:8px;'>"
                            f"<p style='margin:0 0 8px 0;font-size:12px;font-weight:700;color:#1E293B;'>{c_ins}</p>"
                            f"<p style='margin:0 0 4px 0;font-size:11px;color:#475569;'>🏢 <b>{c_site}</b></p>"
                            f"{label_html}"
                            "<hr style='border:none;border-top:1px solid #F1F5F9;margin:8px 0;'>"
                            f"{date_ctrl_html}"
                            "<p style='margin:0 0 2px 0;font-size:10px;color:#94a3b8;'>Prochaine échéance</p>"
                            f"<p style='margin:0 0 6px 0;font-size:11px;color:#334155;font-weight:500;'>{next_fmt}</p>"
                            f"<span style='display:inline-block;padding:3px 8px;border-radius:4px;font-size:10px;font-weight:600;background:{c_col}22;color:{c_col};'>{c_stat} — {j_txt}</span>"
                            "</div>"
                        )
                        st.markdown(carte_html, unsafe_allow_html=True)
            elif evenements and jour_sel is None:
                st.info("💡 Cliquez sur un jour coloré du calendrier pour voir les détails du contrôle.")


    # ------------------------------------------------------------------------------
    # BLOC 3 — UI Streamlit (à insérer dans `with tab_exigences:`)
    # ------------------------------------------------------------------------------
    st.divider()
    st.markdown("### 🗓️ Calendrier de contrôle réglementaire")


    annee_ref_calendrier = datetime.date.today().year

    if st.button("🗓️ Générer le calendrier", use_container_width=True, key="btn_gen_calendrier"):
        with st.spinner("Construction du calendrier..."):
            df_calendrier = construire_calendrier_controle(df_rapports, annee_ref_calendrier)
            if df_calendrier.empty:
                st.warning("Aucune donnée exploitable pour construire le calendrier.")
                st.session_state["df_calendrier"] = None
            else:
                st.session_state["df_calendrier"] = df_calendrier

    if st.session_state.get("df_calendrier") is not None:
        df_cal = st.session_state["df_calendrier"]
        st.dataframe(df_cal, hide_index=True, use_container_width=True)

        # ----- Taux de réalisation 2026 : barres horizontales par site + infographie globale -----
        taux = calculer_taux_realisation(df_cal)
        taux_meg = taux.get("MEG", 0.0)
        taux_sgb = taux.get("SGB", 0.0)
        taux_global = taux.get("Global", 0.0)

        st.markdown(f"#### 📊 Taux de réalisation des contrôles — {annee_ref_calendrier}")
        col_bars, col_gauge = st.columns([2, 1])

        with col_bars:
            df_bars = pd.DataFrame({"Site": ["MEG", "SGB"], "Taux (%)": [taux_meg, taux_sgb]})
            fig_bars = px.bar(
                df_bars, x="Taux (%)", y="Site", text="Taux (%)", color="Site",
                orientation="h",
                color_discrete_map={"MEG": "#2563EB", "SGB": "#059669"},
                range_x=[0, 100],
            )
            fig_bars.update_traces(texttemplate='%{text}%', textposition='outside', cliponaxis=False)
            fig_bars.update_layout(
                title=f"Taux de réalisation par site — {annee_ref_calendrier}", title_x=0.5,
                showlegend=False, xaxis_title="Taux (%)", yaxis_title="",
                margin=dict(t=40, b=10, l=10, r=30), height=280,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            )
            st.plotly_chart(fig_bars, use_container_width=True, config={'displayModeBar': False})

        with col_gauge:
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=taux_global,
                number={'suffix': "%", 'font': {'size': 70, 'color': "#0F172A"}},
                title={'text': f"Taux global {annee_ref_calendrier}", 'font': {'size': 14, 'color': "#334155"}},
                gauge={
                    'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#94A3B8",
                             'tickvals': [0, 25, 50, 75, 100], 'ticktext': ["0", "25", "50", "75", "100"]},
                    'bar': {'color': "#1E3A8A", 'thickness': 0.8},
                    'bgcolor': "white",
                    'borderwidth': 0,
                    'steps': [{'range': [0, 100], 'color': "#E2E8F0"}],
                },
            ))
            fig_gauge.update_layout(
                margin=dict(t=40, b=10, l=30, r=30), height=280,
                paper_bgcolor='rgba(0,0,0,0)',
                transition_duration=600, transition_easing="cubic-in-out",
            )
            st.plotly_chart(fig_gauge, use_container_width=True, config={'displayModeBar': False})

        dl1, dl2 = st.columns(2)
        with dl1:
            pdf_cal = generer_calendrier_controle_pdf(df_cal, annee_ref_calendrier)
            st.download_button(
                "📥 Télécharger en PDF", data=pdf_cal,
                file_name=f"Calendrier_Controle_{annee_ref_calendrier}_{datetime.date.today().strftime('%d_%m_%Y')}.pdf",
                mime="application/pdf", use_container_width=True, key="dl_calendrier_pdf",
            )
        with dl2:
            excel_cal = generer_calendrier_controle_excel(df_cal, annee_ref_calendrier)
            st.download_button(
                "📥 Télécharger en Excel", data=excel_cal,
                file_name=f"Calendrier_Controle_{annee_ref_calendrier}_{datetime.date.today().strftime('%d_%m_%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True, key="dl_calendrier_excel",
            )
    # ---- Relance des échéances proches (notification manuelle par e-mail) ----
    # Réservé au profil Admin uniquement.
        if role == "Admin" and password_correct:
            st.markdown("<br><hr style='border-color:#E2E8F0;'>",unsafe_allow_html=True)
            st.markdown("<br>",unsafe_allow_html=True)
            st.markdown("### 📧 Relance des échéances")
            st.caption("Envoie un e-mail récapitulatif des contrôles en retard ou à venir sous 30 jours. ")
            df_calendrier_relance = construire_calendrier_controle(df_rapports)
            echeances_proches = extraire_echeances_proches(df_calendrier_relance, jours_horizon=30)
            if echeances_proches:
                st.warning(f"⚠️ {len(echeances_proches)} échéance(s) en retard ou à venir sous 30 jours.")
            else:
                st.success("✅ Aucune échéance en retard ou à venir sous 30 jours.")
            destinataires_defaut = ""
            try:
                destinataires_defaut = ", ".join(st.secrets["notifications"]["destinataires"])
            except Exception:
                pass
            destinataires_saisis = st.text_input("Destinataires (séparés par des virgules) :",
                                                   value=destinataires_defaut, placeholder="a@domaine.com, b@domaine.com")
            if st.button("📧 Envoyer la relance maintenant", use_container_width=True, disabled=not echeances_proches):
                emails = [e.strip() for e in destinataires_saisis.split(",") if format_email_valide(e.strip())]
                if not emails:
                    st.error("Aucune adresse e-mail valide renseignée.")
                else:
                    corps = construire_message_relance(echeances_proches)
                    nb_ok, nb_ko = 0, 0
                    for dest in emails:
                        ok_env, err_env = envoyer_email(dest, "Relance — Echéances de contrôle réglementaire", corps)
                        nb_ok += 1 if ok_env else 0
                        nb_ko += 0 if ok_env else 1
                    if nb_ok:
                        st.success(f"✅ Relance envoyée à {nb_ok} destinataire(s).")
                        journaliser_action(utilisateur_courant(), "Relance échéances envoyée", f"{nb_ok} destinataire(s)")
                    if nb_ko:
                        st.error(f"❌ Échec d'envoi pour {nb_ko} destinataire(s) (vérifier la configuration SMTP).")


        # ---- ONGLET EXIGENCES ----
