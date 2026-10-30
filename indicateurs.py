"""Bandeau d'indicateurs en tête de page (contrôles réalisés, conformité)."""


import pandas as pd
import streamlit as st

from tpr.config import COULEUR_SITE, PERIODICITE
from tpr.ui.components import badge_site


def render_indicateurs(ctx):
    df_rapports = ctx.df_rapports

    # ---- Contrôles réalisés en 2026 / total des contrôles suivis (même dédup que les KPI) ----
    col_reelle_hdr = [c for c in df_rapports.columns if "reelle" in c.lower() or "réelle" in c.lower()]
    col_ins_hdr    = [c for c in df_rapports.columns if "ins" in c.lower()]
    col_site_hdr   = [c for c in df_rapports.columns if "site" in c.lower()]
    col_date_hdr   = [c for c in df_rapports.columns if "date" in c.lower() and "reelle" not in c.lower() and "réelle" not in c.lower() and "prochaine" not in c.lower() and "planifi" not in c.lower()]

    # ---- Contrôles 2026 réalisés PAR SITE (SGB / MEG), PAR CATÉGORIE d'installation (et non par équipement) ----
    # Périodicité : Installations électriques = 2 campagnes/an, les 4 autres catégories = 1 campagne/an
    # => 2 + 1 + 1 + 1 + 1 = 6 campagnes attendues par site sur l'année 2026
    def _nb_campagnes_attendues_hdr(installation):
        return round(12 / PERIODICITE.get(installation, 12))

    TOTAL_CATEGORIES_PAR_SITE = sum(_nb_campagnes_attendues_hdr(ins) for ins in PERIODICITE.keys())  # = 6

    nb_ctrl_site = {"SGB": 0, "MEG": 0}
    if not df_rapports.empty and col_ins_hdr and col_date_hdr:
        df_hdr = df_rapports.copy()
        df_hdr["_date_brute"]  = pd.to_datetime(df_hdr[col_date_hdr[0]], dayfirst=True, errors='coerce')
        df_hdr["_date_reelle"] = pd.to_datetime(df_hdr[col_reelle_hdr[0]], dayfirst=True, errors='coerce') if col_reelle_hdr else pd.NaT
        df_hdr = df_hdr.dropna(subset=["_date_brute"])
        df_realises_hdr = df_hdr[df_hdr["_date_reelle"].notna() & (df_hdr["_date_reelle"].dt.year == 2026)]
        if col_site_hdr and col_ins_hdr:
            for site_h in ("SGB", "MEG"):
                df_site_h = df_realises_hdr[df_realises_hdr[col_site_hdr[0]].astype(str).str.strip().str.upper() == site_h]
                total_site = 0
                for ins_h in PERIODICITE.keys():
                    attendu_h = _nb_campagnes_attendues_hdr(ins_h)
                    df_grp_h  = df_site_h[df_site_h[col_ins_hdr[0]].astype(str).str.strip() == ins_h]
                    nb_camp_h = df_grp_h["_date_brute"].nunique() if not df_grp_h.empty else 0
                    total_site += min(nb_camp_h, attendu_h)
                nb_ctrl_site[site_h] = total_site

    def _pct_et_couleur(nb, total):
        pct = round(nb/total*100) if total>0 else 0
        couleur = "#10B981" if pct>=80 else "#F97316" if pct>=50 else "#EF4444"
        return pct, couleur

    # Nombre de contrôles réalisés affichés dans l'indicateur (valeurs saisies manuellement :
    # SGB = 1/6 et MEG = 5/6). Pour revenir au calcul automatique depuis le Sheet, remplacer
    # par nb_ctrl_site["SGB"] et nb_ctrl_site["MEG"].
    nb_sgb_aff = 1
    nb_meg_aff = 5
    pct_sgb, couleur_sgb = _pct_et_couleur(nb_sgb_aff, TOTAL_CATEGORIES_PAR_SITE)
    pct_meg, couleur_meg = _pct_et_couleur(nb_meg_aff, TOTAL_CATEGORIES_PAR_SITE)

    k1,k2=st.columns(2)
    with k1:
        # ---- Taux de conformité global + par site (MEG / SGB), affiché pour tous les rôles ----
        taux_non_conformite_global = 40.23
        taux_non_conformite_meg    = 35.14
        taux_non_conformite_sgb    = 46.27
        taux_conformite_global = round(100 - taux_non_conformite_global, 2)
        taux_conformite_meg    = round(100 - taux_non_conformite_meg, 2)
        taux_conformite_sgb    = round(100 - taux_non_conformite_sgb, 2)
        def _couleur_taux(t):
            return "#10B981" if t>=80 else "#F97316" if t>=50 else "#EF4444"
        c_global = _couleur_taux(taux_conformite_global)
        c_meg    = _couleur_taux(taux_conformite_meg)
        c_sgb    = _couleur_taux(taux_conformite_sgb)
        st.markdown(f"""<div style="background:white;padding:22px;border-radius:12px;box-shadow:0 4px 6px -1px rgba(0,0,0,0.05);border-left:5px solid #1E3A8A;height:118px;box-sizing:border-box;display:flex;flex-direction:row;align-items:center;justify-content:space-between;gap:20px;">
            <div style="display:flex;flex-direction:column;justify-content:center;flex-shrink:0;">
                <p style="margin:0;font-size:12px;color:#64748B;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;white-space:nowrap;">Taux de Conformité Global</p>
                <p style="margin:8px 0 0 0;font-size:34px;color:{c_global};font-weight:700;line-height:1;">{taux_conformite_global}%</p>
            </div>
            <div style="display:flex;gap:14px;flex:1;">
                <div style="text-align:center;background:{COULEUR_SITE['MEG']['claire']};border-radius:10px;padding:10px 14px;flex:1;">
                    <div style="margin-bottom:4px;">{badge_site("MEG")}</div>
                    <p style="margin:4px 0 0 0;font-size:24px;font-weight:700;color:{c_meg};line-height:1;">{taux_conformite_meg}%</p>
                </div>
                <div style="text-align:center;background:{COULEUR_SITE['SGB']['claire']};border-radius:10px;padding:10px 14px;flex:1;">
                    <div style="margin-bottom:4px;">{badge_site("SGB")}</div>
                    <p style="margin:4px 0 0 0;font-size:24px;font-weight:700;color:{c_sgb};line-height:1;">{taux_conformite_sgb}%</p>
                </div>
            </div></div>""",unsafe_allow_html=True)
    with k2:
        st.markdown(f"""<div style="background:white;padding:22px;border-radius:12px;box-shadow:0 4px 6px -1px rgba(0,0,0,0.05);border-left:5px solid #0EA5E9;height:118px;box-sizing:border-box;display:flex;flex-direction:column;justify-content:center;gap:8px;">
            <p style="margin:0;font-size:12px;color:#64748B;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Contrôles Réalisés 2026</p>
            <div style="display:flex;align-items:center;gap:8px;">
                <span>{badge_site("SGB")}</span>
                <div style="flex:1;height:8px;background:#E2E8F0;border-radius:4px;overflow:hidden;">
                    <div style="width:{pct_sgb}%;height:100%;background:{COULEUR_SITE['SGB']['principale']};border-radius:4px;transition:width 0.6s ease-in-out;"></div>
                </div>
                <span style="font-size:11px;color:{couleur_sgb};font-weight:700;white-space:nowrap;width:90px;text-align:right;">{nb_sgb_aff}/{TOTAL_CATEGORIES_PAR_SITE} ({pct_sgb}%)</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
                <span>{badge_site("MEG")}</span>
                <div style="flex:1;height:8px;background:#E2E8F0;border-radius:4px;overflow:hidden;">
                    <div style="width:{pct_meg}%;height:100%;background:{COULEUR_SITE['MEG']['principale']};border-radius:4px;transition:width 0.6s ease-in-out;"></div>
                </div>
                <span style="font-size:11px;color:{couleur_meg};font-weight:700;white-space:nowrap;width:90px;text-align:right;">{nb_meg_aff}/{TOTAL_CATEGORIES_PAR_SITE} ({pct_meg}%)</span>
            </div></div>""",unsafe_allow_html=True)

    st.markdown("<br>",unsafe_allow_html=True)
