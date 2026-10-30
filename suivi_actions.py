"""Onglet « Suivi des actions »."""


import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from tpr.config import NATURE_PILOTE
from tpr.domain.pilotes import _codes_pour_pilote, nom_pour_pilote_site
from tpr.services.codif import codif_charger_toutes_actions
from tpr.services.repository import (
    _cle_action,
    enregistrer_statuts_en_cours_lot,
    lire_actions_realisees,
    lire_suivi_encours,
    marquer_actions_realisees,
)


def render(ctx):
    RESPONSABLES = ctx.responsables
    password_correct = ctx.password_correct
    role = ctx.role
    st.markdown("<p style='font-size:1.2rem;font-weight:700;color:#1E3A8A;'>✅ Suivi des actions</p>",unsafe_allow_html=True)

    est_admin_suivi = (role == "Admin" and password_correct)

    if not est_admin_suivi:
        st.markdown(
            "<div style='background:#EFF6FF;border-left:4px solid #2a78d6;padding:10px 14px;border-radius:6px;margin-bottom:14px;'>"
            "<p style='margin:0;font-size:12px;color:#1e40af;'>Cochez les actions terminées.</p>"
            "</div>", unsafe_allow_html=True)

    if est_admin_suivi:
        entites_disponibles_suivi = sorted(set(
            e.strip() for v in NATURE_PILOTE.values() for e in v[1].split("+") if e.strip()
        ))
        pilote_suivi_choisi = st.selectbox("Responsable à suivre", entites_disponibles_suivi, key="pilote_suivi_admin")
        nom_responsable_suivi = nom_pour_pilote_site(pilote_suivi_choisi, None)
        site_resp_suivi = None
    else:
        compte_resp_suivi = RESPONSABLES.get(st.session_state.responsable_actif, {})
        entites_resp_suivi = compte_resp_suivi.get("entites", [])
        nom_responsable_suivi = compte_resp_suivi.get("nom", st.session_state.responsable_actif)
        site_resp_suivi = compte_resp_suivi.get("site")
        if len(entites_resp_suivi) > 1:
            pilote_suivi_choisi = st.selectbox("Périmètre", entites_resp_suivi, key="pilote_suivi_resp")
        else:
            pilote_suivi_choisi = entites_resp_suivi[0] if entites_resp_suivi else None

    if not pilote_suivi_choisi:
        st.info("Aucun périmètre associé à ce profil.")
    else:
        with st.spinner("Chargement des actions (MEG et SGB)..."):
            df_codif_suivi, err_suivi = codif_charger_toutes_actions()
            df_realisees_suivi = lire_actions_realisees()
            df_encours_suivi = lire_suivi_encours()

        if err_suivi and df_codif_suivi.empty:
            st.error(err_suivi)
        else:
            if err_suivi:
                st.warning(err_suivi)

            codes_ok_suivi = _codes_pour_pilote(pilote_suivi_choisi)
            df_pilote_suivi = df_codif_suivi[df_codif_suivi["Code"].isin(codes_ok_suivi)].copy()
            if site_resp_suivi and "Site" in df_pilote_suivi.columns:
                df_pilote_suivi = df_pilote_suivi[df_pilote_suivi["Site"].astype(str).str.strip().str.upper() == site_resp_suivi.upper()]
            df_pilote_suivi["Cle"] = df_pilote_suivi.apply(_cle_action, axis=1)

            cles_faites_suivi = set()
            df_hist_pilote = pd.DataFrame()
            if not df_realisees_suivi.empty and "Pilote" in df_realisees_suivi.columns:
                df_hist_pilote = df_realisees_suivi[df_realisees_suivi["Pilote"] == pilote_suivi_choisi]
                cles_faites_suivi = set(df_hist_pilote.apply(_cle_action, axis=1))

            df_restantes = df_pilote_suivi[~df_pilote_suivi["Cle"].isin(cles_faites_suivi)]

            total_pilote = len(df_pilote_suivi)
            nb_realisees = len(cles_faites_suivi & set(df_pilote_suivi["Cle"]))
            taux = round((nb_realisees/total_pilote*100), 1) if total_pilote else 0.0

            # Dernier statut « En cours » connu (Type + commentaire), par clé d'action
            info_encours_par_cle = {}
            if not df_encours_suivi.empty:
                for _, r_enc in df_encours_suivi.iterrows():
                    info_encours_par_cle[r_enc["Cle"]] = {
                        "Type": r_enc.get("Type", "") or "",
                        "Commentaire": r_enc.get("Commentaire", "") or "",
                    }

            col_liste, col_graphe = st.columns([3, 1])

            with col_liste:
                if df_restantes.empty:
                    st.markdown(f"<p style='font-weight:700;font-size:14px;color:#0F172A;'>Actions restantes — {nom_responsable_suivi}</p>",unsafe_allow_html=True)
                    st.success("🎉 Toutes les actions de ce périmètre sont réalisées !")
                else:
                    site_f_suivi = "Tous"
                    if site_resp_suivi:
                        # Compte restreint à un seul site : pas de sélecteur de site
                        st.markdown(f"<p style='font-weight:700;font-size:14px;color:#0F172A;'>Actions restantes — {nom_responsable_suivi}</p>",unsafe_allow_html=True)
                        df_apres_site_suivi = df_restantes
                        installations_dispo_suivi = sorted(df_apres_site_suivi["Installation"].dropna().unique().tolist())
                        install_f_suivi = st.selectbox("Installation", ["Toutes"]+installations_dispo_suivi, key="installation_filtre_suivi")
                    else:
                        sites_dispo_suivi = sorted(df_restantes["Site"].dropna().unique().tolist())
                        fcol1, fcol2 = st.columns(2)
                        with fcol1:
                            site_f_suivi = st.selectbox("Site", ["Tous"]+sites_dispo_suivi, key="site_filtre_suivi")
                        if est_admin_suivi:
                            nom_responsable_suivi = nom_pour_pilote_site(pilote_suivi_choisi, None if site_f_suivi == "Tous" else site_f_suivi)
                        st.markdown(f"<p style='font-weight:700;font-size:14px;color:#0F172A;'>Actions restantes — {nom_responsable_suivi}</p>",unsafe_allow_html=True)
                        df_apres_site_suivi = df_restantes if site_f_suivi == "Tous" else df_restantes[df_restantes["Site"] == site_f_suivi]
                        with fcol2:
                            installations_dispo_suivi = sorted(df_apres_site_suivi["Installation"].dropna().unique().tolist())
                            install_f_suivi = st.selectbox("Installation", ["Toutes"]+installations_dispo_suivi, key="installation_filtre_suivi")
                    df_affiche_suivi = df_apres_site_suivi if install_f_suivi == "Toutes" else df_apres_site_suivi[df_apres_site_suivi["Installation"] == install_f_suivi]

                    # ---- Recalcul des statistiques (jauge + graphes) selon le site sélectionné ----
                    site_effectif_stats = site_resp_suivi if site_resp_suivi else (None if site_f_suivi == "Tous" else site_f_suivi)
                    if site_effectif_stats and "Site" in df_pilote_suivi.columns:
                        df_pilote_suivi_stats = df_pilote_suivi[df_pilote_suivi["Site"].astype(str).str.strip().str.upper() == site_effectif_stats.upper()]
                        df_restantes = df_restantes[df_restantes["Site"].astype(str).str.strip().str.upper() == site_effectif_stats.upper()]
                    else:
                        df_pilote_suivi_stats = df_pilote_suivi
                    total_pilote = len(df_pilote_suivi_stats)
                    nb_realisees = len(cles_faites_suivi & set(df_pilote_suivi_stats["Cle"]))
                    taux = round((nb_realisees/total_pilote*100), 1) if total_pilote else 0.0

                    if not est_admin_suivi:
                        # ---- Vue responsable : un tableau, avec colonnes Statut / Type de suivi / Commentaire ----
                        TYPES_SUIVI = ["Immédiat", "Sous-traitance", "Planifié"]

                        # Index réinitialisé (0..n-1) pour que les positions renvoyées par
                        # le data_editor (edited_rows) correspondent exactement aux lignes de
                        # df_affiche_suivi_reset — c'est ce qui garantit qu'on n'écrit QUE les
                        # lignes réellement modifiées par l'utilisateur, ni plus ni moins.
                        df_affiche_suivi_reset = df_affiche_suivi.reset_index(drop=True)

                        df_edit = df_affiche_suivi_reset[["Site", "Installation", "Désignation", "Observation", "Code"]].copy()
                        df_edit.insert(0, "Statut", "En cours")
                        df_edit["Type de suivi"] = df_affiche_suivi_reset["Cle"].map(
                            lambda c: info_encours_par_cle.get(c, {}).get("Type") or None
                        )
                        df_edit["Commentaire"] = df_affiche_suivi_reset["Cle"].map(
                            lambda c: info_encours_par_cle.get(c, {}).get("Commentaire", "")
                        )

                        df_edit_out = st.data_editor(
                            df_edit,
                            hide_index=True,
                            use_container_width=True,
                            disabled=["Site", "Installation", "Désignation", "Observation", "Code"],
                            column_config={
                                "Statut": st.column_config.SelectboxColumn("Statut", options=["En cours", "Terminé"], required=True),
                                "Type de suivi": st.column_config.SelectboxColumn("Type de suivi (si en cours)", options=TYPES_SUIVI, required=False),
                                "Commentaire": st.column_config.TextColumn("Commentaire (optionnel)"),
                            },
                            key="editeur_suivi_actions"
                        )

                        if st.button("💾 Enregistrer les modifications", type="primary",
                                     use_container_width=True, key="btn_valider_suivi"):
                            # ---- On ne traite QUE les lignes que Streamlit a lui-même identifiées
                            #      comme modifiées (st.session_state[...]["edited_rows"]), plutôt que
                            #      de comparer des valeurs par défaut : c'est fiable à 100% et garantit
                            #      qu'on n'écrit jamais des lignes non touchées par l'utilisateur. ----
                            etat_editeur = st.session_state.get("editeur_suivi_actions", {})
                            positions_modifiees = sorted(int(p) for p in etat_editeur.get("edited_rows", {}).keys())

                            lignes_terminees = []
                            lignes_en_cours = []
                            for pos in positions_modifiees:
                                row_edit = df_edit_out.iloc[pos]
                                row_orig = df_affiche_suivi_reset.iloc[pos].copy()
                                row_orig["Pilote"] = pilote_suivi_choisi
                                statut_c = row_edit["Statut"]
                                type_c = row_edit.get("Type de suivi")
                                commentaire_c = row_edit.get("Commentaire", "")
                                if statut_c == "Terminé":
                                    lignes_terminees.append(row_orig)
                                else:
                                    lignes_en_cours.append((row_orig, type_c or TYPES_SUIVI[0], commentaire_c or ""))

                            erreur_maj = False
                            messages_erreur = []
                            nb_termine_ok, nb_encours_ok = 0, 0

                            with st.spinner(f"Enregistrement de {len(lignes_terminees) + len(lignes_en_cours)} modification(s)..."):
                                if lignes_terminees:
                                    ok, msgs = marquer_actions_realisees(pd.DataFrame(lignes_terminees), nom_responsable_suivi)
                                    erreur_maj = erreur_maj or not ok
                                    nb_termine_ok = len(lignes_terminees) if ok else 0
                                    if not ok:
                                        messages_erreur.extend(msgs)

                                if lignes_en_cours:
                                    ok, msgs = enregistrer_statuts_en_cours_lot(lignes_en_cours, nom_responsable_suivi)
                                    erreur_maj = erreur_maj or not ok
                                    nb_encours_ok = len(lignes_en_cours) if ok else 0
                                    if not ok:
                                        messages_erreur.extend(msgs)

                            if not positions_modifiees:
                                st.info("Aucune modification détectée — rien à enregistrer.")
                            elif erreur_maj:
                                st.error("Une erreur est survenue lors de l'enregistrement (vérifiez les onglets « ActionsRealisees » / « SuiviActions »).")
                                if messages_erreur:
                                    with st.expander("Détail technique de l'erreur (à transmettre à l'administrateur)"):
                                        for m in messages_erreur:
                                            st.code(str(m))
                            else:
                                st.success(f"{nb_termine_ok} action(s) marquée(s) terminée(s), {nb_encours_ok} mise(s) à jour « en cours ».")
                                st.cache_data.clear()
                                st.rerun()
                    else:
                        # ---- Vue admin : tableau récapitulatif en lecture seule ----
                        df_recap = df_affiche_suivi[["Site", "Installation", "Désignation", "Observation", "Code"]].copy()
                        df_recap["Type de suivi"] = df_affiche_suivi["Cle"].map(
                            lambda c: info_encours_par_cle.get(c, {}).get("Type") or "Non défini"
                        )
                        df_recap["Commentaire"] = df_affiche_suivi["Cle"].map(
                            lambda c: info_encours_par_cle.get(c, {}).get("Commentaire", "")
                        )
                        st.dataframe(df_recap, hide_index=True, use_container_width=True)
                        st.caption("ℹ️ Vue administrateur en lecture seule.")

                with st.expander("🗂️ Historique des actions réalisées"):
                    if df_hist_pilote.empty:
                        st.info("Aucune action réalisée pour le moment.")
                    else:
                        cols_hist = [c for c in ["DateRealisation", "Site", "Installation", "Désignation", "Observation", "Code", "Responsable"] if c in df_hist_pilote.columns]
                        df_aff_hist = df_hist_pilote[cols_hist]
                        if "DateRealisation" in df_aff_hist.columns:
                            df_aff_hist = df_aff_hist.sort_values("DateRealisation", ascending=False)
                        st.dataframe(df_aff_hist, hide_index=True, use_container_width=True)

            with col_graphe:
                st.markdown("<p style='font-weight:700;font-size:13px;color:#0F172A;text-align:center;'>Taux de réalisation</p>",unsafe_allow_html=True)
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=taux,
                    number={"suffix": "%"},
                    gauge={
                        "axis": {"range": [0, 100],
                                 "tickvals": [0, 50, 100], "ticktext": ["0", "50", "100"]},
                        "bar": {"color": "#1baf7a"},
                        "steps": [
                            {"range": [0, 50], "color": "#FEE2E2"},
                            {"range": [50, 80], "color": "#FEF3C7"},
                            {"range": [80, 100], "color": "#DCFCE7"},
                        ],
                    }
                ))
                fig_gauge.update_layout(height=220, margin=dict(t=20, b=10, l=30, r=30), paper_bgcolor='rgba(0,0,0,0)',
                                         transition_duration=600, transition_easing="cubic-in-out")
                st.plotly_chart(fig_gauge, use_container_width=True, config={'displayModeBar': False})
                st.markdown(f"<p style='text-align:center;font-size:12px;color:#64748B;'>{nb_realisees} / {total_pilote} action(s) réalisée(s)</p>",unsafe_allow_html=True)

            # ---- Graphes complémentaires (Admin uniquement), affichés sous le tableau ----
            if est_admin_suivi:
                st.markdown("<br><hr style='border-color:#E2E8F0;'>",unsafe_allow_html=True)
                st.markdown(f"<p style='font-size:1.05rem;font-weight:700;color:#1E3A8A;'>📈 Analyse du suivi — {nom_responsable_suivi}</p>",unsafe_allow_html=True)

                gA, gB = st.columns(2)

                # --- Graphe 1 : % Terminé vs En cours (pour le pilote sélectionné) ---
                with gA:
                    en_cours_total = max(total_pilote - nb_realisees, 0)
                    if total_pilote:
                        df_g1 = pd.DataFrame({"Statut": ["Terminé", "En cours"], "Nombre": [nb_realisees, en_cours_total]})
                        fig1 = px.pie(df_g1, values="Nombre", names="Statut", hole=0.6, color="Statut",
                                      color_discrete_map={"Terminé": "#16A34A", "En cours": "#F97316"})
                        fig1.update_traces(textposition='inside', textinfo='percent+value')
                        fig1.update_layout(title="Terminé vs En cours", title_x=0.5,
                                            margin=dict(t=40,b=10,l=10,r=10), height=300,
                                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                            legend=dict(font=dict(size=9)),
                                            transition_duration=500, transition_easing="cubic-in-out")
                        st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})
                    else:
                        st.info("Aucune donnée.")

                # --- Graphe 2 : % Immédiat / Sous-traitance / Planifié parmi les actions en cours ---
                with gB:
                    cles_en_cours_g = set(df_restantes["Cle"]) if "Cle" in df_restantes.columns else set()
                    compte_type_g = {"Immédiat": 0, "Sous-traitance": 0, "Planifié": 0, "Non défini": 0}
                    for cle_g in cles_en_cours_g:
                        t_g = info_encours_par_cle.get(cle_g, {}).get("Type") or "Non défini"
                        if t_g not in compte_type_g:
                            t_g = "Non défini"
                        compte_type_g[t_g] += 1
                    df_g2 = pd.DataFrame({"Type": list(compte_type_g.keys()), "Nombre": list(compte_type_g.values())})
                    df_g2 = df_g2[df_g2["Nombre"] > 0]
                    if not df_g2.empty:
                        fig2 = px.pie(df_g2, values="Nombre", names="Type", hole=0.6, color="Type",
                                      color_discrete_map={"Immédiat": "#2563EB", "Sous-traitance": "#F59E0B",
                                                           "Planifié": "#8B5CF6", "Non défini": "#94A3B8"})
                        fig2.update_traces(textposition='inside', textinfo='percent+value')
                        fig2.update_layout(title="Répartition des actions en cours", title_x=0.5,
                                            margin=dict(t=40,b=10,l=10,r=10), height=300,
                                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                            legend=dict(font=dict(size=9)),
                                            transition_duration=500, transition_easing="cubic-in-out")
                        st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})
                    else:
                        st.info("Aucune action en cours.")
