"""Onglet « Exigences » (équipements et contrat)."""

import datetime
import re

import pandas as pd
import streamlit as st

from tpr.config import COULEURS_INS
from tpr.reports.equipements import generer_rapport_equipements_pdf
from tpr.services.repository import ajouter_equipement, ecrire_contrat, lire_exigences, supprimer_contrat, supprimer_equipement_ligne
from tpr.ui.pdf_viewer import afficher_apercu_pdf


def render(ctx):
    password_correct = ctx.password_correct
    role = ctx.role
    st.markdown("<br><p style='font-size:1.2rem;font-weight:700;color:#0F172A;margin-bottom:15px;'>📌 Exigences réglementaires</p>", unsafe_allow_html=True)

    df_exig = lire_exigences()


        # ===== SECTION 1 : CONTRAT D'ABONNEMENT =====
    st.markdown("### 📄 Contrat d'abonnement 2026")

    def lien_telechargement_direct(lien: str) -> str:
        """Convertit un lien Google Drive (vue/partage) en lien de téléchargement direct.
        Si ce n'est pas un lien Google Drive reconnu, renvoie le lien tel quel."""
        if not lien:
            return lien
        m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", lien)
        if not m:
            m = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", lien)
        if m:
            file_id = m.group(1)
            return f"https://drive.google.com/uc?export=download&id={file_id}"
        return lien

    def lien_apercu_drive(lien: str) -> str:
        """Convertit un lien Google Drive en lien d'aperçu (preview) qui s'ouvre
        directement dans Drive sans télécharger le fichier."""
        if not lien:
            return lien
        m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", lien)
        if not m:
            m = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", lien)
        if m:
            file_id = m.group(1)
            return f"https://drive.google.com/file/d/{file_id}/preview"
        return lien

    lien_contrat = ""
    if not df_exig.empty and "Type" in df_exig.columns:
        ligne_c = df_exig[df_exig["Type"] == "Contrat"]
        if not ligne_c.empty:
            lien_contrat = str(ligne_c.iloc[0].get("Lien_PDF", "")).strip()

    col_contrat, col_action = st.columns([5, 1])
    with col_contrat:
        if lien_contrat and lien_contrat.lower() != "nan":
            lien_dl = lien_telechargement_direct(lien_contrat)
            lien_apercu = lien_apercu_drive(lien_contrat)

            st.markdown(
                "<div style='background:white;padding:16px 20px;border-radius:10px;"
                "box-shadow:0 2px 8px rgba(0,0,0,0.05);border-left:4px solid #1E3A8A;"
                "display:flex;align-items:center;justify-content:space-between;'>"
                "<span style='font-size:14px;font-weight:600;color:#1E293B;'>📑 Contrat d'abonnement 2026</span>"
                "<span>"
                f"<a href='{lien_apercu}' target='_blank' rel='noopener' style='text-decoration:none;background:#1E3A8A;"
                "color:white;padding:8px 14px;border-radius:6px;font-size:13px;font-weight:600;margin-right:8px;'>"
                "👁️ Consulter</a>"
                f"<a href='{lien_dl}' download target='_blank' rel='noopener' style='text-decoration:none;background:#16A34A;"
                "color:white;padding:8px 14px;border-radius:6px;font-size:13px;font-weight:600;'>"
                "📥 Télécharger</a>"
                "</span>"
                "</div>", unsafe_allow_html=True)
        else:
            st.info("Aucun contrat n'a encore été ajouté.")

    if role == "Admin" and password_correct:
        with st.expander("✏️ Gérer le contrat"):
            nouveau_lien = st.text_input("Lien Google Drive du contrat PDF :",
                value=lien_contrat if lien_contrat.lower() != "nan" else "",
                placeholder="https://drive.google.com/file/d/...")
            bc1, bc2 = st.columns(2)
            with bc1:
                if st.button("💾", use_container_width=True):
                    if nouveau_lien.strip():
                        ok, err = ecrire_contrat(nouveau_lien.strip())
                        if ok:
                            st.success("✅ Contrat mis à jour !")
                            st.rerun()
                        else:
                            st.error(f"Erreur : {err}")
                    else:
                        st.warning("Veuillez coller un lien.")
            with bc2:
                if st.button("🗑️", use_container_width=True):
                    if supprimer_contrat():
                        st.success("✅ Contrat supprimé.")
                        st.rerun()
                    else:
                        st.error("Erreur lors de la suppression.")

    st.markdown("<br><hr style='border-color:#E2E8F0;'>", unsafe_allow_html=True)     


        # ===== SECTION 3 : LISTE DES ÉQUIPEMENTS (ARBORESCENCE) =====
    st.markdown("### 🏭 Liste des équipements soumis au contrôle")

    df_equip = pd.DataFrame()
    if not df_exig.empty and "Type" in df_exig.columns:
        df_equip = df_exig[df_exig["Type"] == "Equipement"].copy()
        if "Nombre" in df_equip.columns:
            df_equip["Nombre"] = pd.to_numeric(df_equip["Nombre"], errors="coerce").fillna(0).astype(int)

        # Initialisation propre du Session State
    if "site_exig_sel" not in st.session_state: 
        st.session_state.site_exig_sel = None
    if "ins_exig_sel" not in st.session_state: 
        st.session_state.ins_exig_sel = None

        # Niveau 1 : choix du site
    st.markdown("<p style='font-size:13px;color:#64748B;font-weight:600;margin-bottom:8px;'>Sélectionnez un site :</p>", unsafe_allow_html=True)
    s1, s2, s3 = st.columns([1, 1, 3])

    with s1:
        actif_sgb = (st.session_state.site_exig_sel == "SGB")
        if st.button("🏢 SGB", use_container_width=True, type="primary" if actif_sgb else "secondary"):
            st.session_state.site_exig_sel = "SGB"
            st.session_state.ins_exig_sel = None  # Reset l'installation si on change de site
            st.rerun()
    
    with s2:
        actif_meg = (st.session_state.site_exig_sel == "MEG")
        if st.button("🏢 MEG", use_container_width=True, type="primary" if actif_meg else "secondary"):
            st.session_state.site_exig_sel = "MEG"
            st.session_state.ins_exig_sel = None  # Reset l'installation si on change de site
            st.rerun()

        # --- CORRECTION DE LA LOGIQUE D'AFFICHAGE ---
        # On se base TOUJOURS sur le session_state actuel, pas sur le clic du bouton direct
    if st.session_state.site_exig_sel:
        site_sel = st.session_state.site_exig_sel
        st.markdown(f"<p style='font-size:13px;color:#64748B;font-weight:600;margin:16px 0 8px 0;'>Installations — Site {site_sel} :</p>", unsafe_allow_html=True)

        df_site = df_equip[df_equip["Site"] == site_sel] if not df_equip.empty else pd.DataFrame()

        NOMS_COURTS_INS = {
            "Installations électriques": "⚡ Électriques",
            "Equipements de levage":     "🏗️ Levage",
            "Sécurité incendie":         "🔥 Incendie",
            "Installations de gaz":      "🔵 Gaz",
            "Appareil pression de gaz":  "⚙️ Pression gaz",
        }

    # Création dynamique des boutons des installations
        ins_cols = st.columns(5)
        for i, (ins, couleur) in enumerate(COULEURS_INS.items()):
            with ins_cols[i % 5]:
                nb_total_ins = int(df_site[df_site["Installation"] == ins]["Nombre"].sum()) if not df_site.empty else 0
                actif_ins = (st.session_state.ins_exig_sel == ins)
                label_court = NOMS_COURTS_INS.get(ins, ins)
        
                if st.button(f"{label_court} ({nb_total_ins})", key=f"ins_btn_{ins}", use_container_width=True,
                             type="primary" if actif_ins else "secondary",
                             help=f"{nb_total_ins} équipement(s) au total"):
                    st.session_state.ins_exig_sel = ins
                    st.rerun()

    # Niveau 3 : sous-équipements de l'istallation choisie
        if st.session_state.ins_exig_sel:
            ins_sel = st.session_state.ins_exig_sel
            st.markdown(f"<p style='font-size:13px;color:#64748B;font-weight:600;margin:16px 0 8px 0;'>Sous-équipements — {ins_sel} ({site_sel}) :</p>", unsafe_allow_html=True)

            df_ins = df_site[df_site["Installation"] == ins_sel] if not df_site.empty else pd.DataFrame()
            couleur_ins = COULEURS_INS.get(ins_sel, "#94a3b8")

            if df_ins.empty:
                st.info(f"Aucun sous-équipement enregistré pour {ins_sel} sur le site {site_sel}.")
            else:
                eq_cols = st.columns(3)
                for idx, (_, row_eq) in enumerate(df_ins.iterrows()):
                    with eq_cols[idx % 3]:
                        st.markdown(
                            f"<div style='background:white;border-left:4px solid {couleur_ins};"
                            "padding:14px;border-radius:8px;box-shadow:0 2px 6px rgba(0,0,0,0.05);margin-bottom:10px;'>"
                            f"<p style='margin:0;font-size:13px;font-weight:600;color:#1E293B;'>{row_eq.get('Sous_equipement','')}</p>"
                            f"<p style='margin:6px 0 0 0;font-size:24px;font-weight:800;color:{couleur_ins};'>{int(row_eq.get('Nombre',0))}</p>"
                            "</div>", unsafe_allow_html=True)

        # Gestion (ajout/suppression) — admin uniquement
            if role == "Admin" and password_correct:
                with st.expander("✏️ Gérer les sous-équipements"):
                    st.markdown("**Ajouter un sous-équipement :**")
                    ac1, ac2, ac3 = st.columns([2, 1, 1])
                    with ac1:
                        nouv_seq = st.text_input("Nom du sous-équipement", key="nouv_seq_nom")
                    with ac2:
                        nouv_nb = st.number_input("Nombre", min_value=1, value=1, key="nouv_seq_nb")
                    with ac3:
                        st.write("")
                        st.write("")
                        if st.button("➕ Ajouter", use_container_width=True):
                            if nouv_seq.strip():
                                ok, err = ajouter_equipement(site_sel, ins_sel, nouv_seq.strip(), nouv_nb)
                                if ok:
                                    st.success("✅ Ajouté !")
                                    st.rerun()
                                else:
                                    st.error(f"Erreur : {err}")
                            else:
                                st.warning("Veuillez saisir un nom.")

                    if not df_ins.empty:
                        st.markdown("<br>**Supprimer un sous-équipement :**", unsafe_allow_html=True)
                        for orig_idx, row_eq in df_ins.iterrows():
                            dc1, dc2 = st.columns([5, 1])
                            with dc1:
                                st.write(f"{row_eq.get('Sous_equipement','')} — {int(row_eq.get('Nombre',0))} unité(s)")
                            with dc2:
                                if st.button("🗑️", key=f"del_eq_{orig_idx}"):
                                    num_ligne_sheet = orig_idx + 2
                                    if supprimer_equipement_ligne(num_ligne_sheet):
                                        st.success("Supprimé !")
                                        st.cache_data.clear()
                                        st.rerun()
                                    else:
                                        st.error("Erreur lors de la suppression.")
    else:
        st.info("👆 Sélectionnez un site (SGB ou MEG) pour voir les installations")

    st.divider()

    if not df_exig.empty:
        st.markdown("### 📄 Check-lists des équipements contractés")
        col_sgb, col_meg = st.columns(2)
        date_str = datetime.date.today().strftime('%d_%m_%Y')

        with col_sgb:
            st.markdown(
                "<div style='background:white;padding:16px 20px;border-radius:10px;"
                "box-shadow:0 2px 8px rgba(0,0,0,0.05);border-left:4px solid #1E3A8A;"
                "margin-bottom:10px;'>"
                "<span style='font-size:14px;font-weight:600;color:#1E293B;'>📑 Rapport d'inspection — SGB</span>"
                "</div>", unsafe_allow_html=True)
            if st.button("👁️ Consulter le rapport", use_container_width=True, key="consult_sgb", type="primary"):
                with st.spinner("Préparation du rapport SGB..."):
                    try:
                        st.session_state["pdf_sgb"] = generer_rapport_equipements_pdf(df_exig, "SGB")
                    except Exception as e:
                        st.session_state["pdf_sgb"] = None
                        st.error(f"Erreur PDF SGB : {e}")
            if st.session_state.get("pdf_sgb"):
                afficher_apercu_pdf(st.session_state["pdf_sgb"])
                st.download_button(
                    label="📥 Télécharger le rapport SGB",
                    data=st.session_state["pdf_sgb"],
                    file_name=f"Rapport_Inspection_SGB_{date_str}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="dl_sgb"
                )

        with col_meg:
            st.markdown(
                "<div style='background:white;padding:16px 20px;border-radius:10px;"
                "box-shadow:0 2px 8px rgba(0,0,0,0.05);border-left:4px solid #1E3A8A;"
                "margin-bottom:10px;'>"
                "<span style='font-size:14px;font-weight:600;color:#1E293B;'>📑 Rapport d'inspection — MEG</span>"
                "</div>", unsafe_allow_html=True)
            if st.button("👁️ Consulter le rapport", use_container_width=True, key="consult_meg", type="primary"):
                with st.spinner("Préparation du rapport MEG..."):
                    try:
                        st.session_state["pdf_meg"] = generer_rapport_equipements_pdf(df_exig, "MEG")
                    except Exception as e:
                        st.session_state["pdf_meg"] = None
                        st.error(f"Erreur PDF MEG : {e}")
            if st.session_state.get("pdf_meg"):
                afficher_apercu_pdf(st.session_state["pdf_meg"])
                st.download_button(
                    label="📥 Télécharger le rapport MEG",
                    data=st.session_state["pdf_meg"],
                    file_name=f"Rapport_Inspection_MEG_{date_str}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="dl_meg"
                )
            





        # ---- ONGLET 3 : PRÉSENCE & VISITES ----
