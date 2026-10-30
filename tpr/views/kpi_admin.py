"""Onglet « KPI » — vue administrateur."""

import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

from tpr.config import LOGO_URL, LUCID_CARTOGRAPHIE_URL, NATURE_PILOTE, PERIODICITE
from tpr.domain.pilotes import _codes_pour_pilote
from tpr.reports.export_global import generer_export_global_excel
from tpr.reports.kpi_pdf import generer_rapport_kpi_pdf
from tpr.reports.pilote_pdf import generer_rapport_pilote_pdf
from tpr.services.audit import journaliser_action, utilisateur_courant
from tpr.services.codif import codif_charger_toutes_actions
from tpr.services.repository import (
    _cle_action,
    ajouter_point_reserve,
    ajouter_point_reserve_nature,
    lire_actions_realisees,
    lire_points_reserve,
    lire_points_reserve_nature,
    supprimer_ligne_generique,
)
from tpr.ui.components import _charger_cartographie_b64
from tpr.ui.pdf_viewer import afficher_apercu_pdf_grille


def render(ctx):
    df_rapports = ctx.df_rapports
    df_planning = ctx.df_planning
    st.markdown("<p style='font-size:1.2rem;font-weight:700;color:#1E3A8A;'>📊 Indicateurs de performance</p>",unsafe_allow_html=True)
    col_r_kpi,_=st.columns([1,5])
    with col_r_kpi:
        if st.button("🔄",key="refresh_kpi"): st.cache_data.clear(); st.rerun()

    # ---- Préparation des données de contrôle (même logique que l'onglet Planification) ----
    col_ins_k   = [c for c in df_rapports.columns if "ins" in c.lower()]
    col_date_k  = [c for c in df_rapports.columns if "date" in c.lower() and "reelle" not in c.lower() and "réelle" not in c.lower() and "prochaine" not in c.lower() and "planifi" not in c.lower()]
    col_site_k  = [c for c in df_rapports.columns if "site" in c.lower()]
    col_label_k = [c for c in df_rapports.columns if "equip" in c.lower() or "label" in c.lower() or "nom" in c.lower()]
    col_reelle_k= [c for c in df_rapports.columns if "reelle" in c.lower() or "réelle" in c.lower()]
    col_planifiee_k = [c for c in df_rapports.columns if "planifi" in c.lower()]

    if df_rapports.empty or not col_ins_k or not col_date_k:
        st.info("Données insuffisantes dans l'onglet « Rapports » pour calculer les KPI.")
        kpi_data = None
    else:
        df_k = df_rapports.copy()
        df_k["_date_brute"]  = pd.to_datetime(df_k[col_date_k[0]], dayfirst=True, errors='coerce')
        df_k["_date_reelle"] = pd.to_datetime(df_k[col_reelle_k[0]], dayfirst=True, errors='coerce') if col_reelle_k else pd.NaT
        # Date planifiée de référence pour le respect de délai : si la colonne dédiée existe
        # dans le Sheet on l'utilise, sinon (tant qu'elle n'a pas été ajoutée) on considère
        # provisoirement que la date planifiée = la date de dernière visite (donc toujours respecté).
        if col_planifiee_k:
            df_k["_date_planifiee"] = pd.to_datetime(df_k[col_planifiee_k[0]], dayfirst=True, errors='coerce')
        else:
            df_k["_date_planifiee"] = df_k["_date_reelle"]
        df_k = df_k.dropna(subset=["_date_brute"])

        cles_k=[]
        if col_site_k:  cles_k.append(col_site_k[0])
        cles_k.append(col_ins_k[0])
        if col_label_k: cles_k.append(col_label_k[0])
        df_k = df_k.sort_values("_date_brute", ascending=True)
        df_k = df_k.drop_duplicates(subset=cles_k, keep="last")

        # ---- KPI 1 : Taux de réalisation 2026, calculé PAR INSTALLATION (et non par équipement) ----
        # Contrôles attendus en 2026 selon la périodicité de chaque installation :
        #   - Installations électriques : périodicité 6 mois -> 2 contrôles/an
        #   - Les 4 autres types        : périodicité 12 mois -> 1 contrôle/an
        # => 2 sites (SGB, MEG) x (1 élec x2 + 4 autres x1) = 12 contrôles attendus au total sur l'année

        SITES_SUIVIS = ["SGB", "MEG"]
        INSTALLATIONS_SUIVIES = list(PERIODICITE.keys())

        def nb_campagnes_attendues(installation):
            return round(12 / PERIODICITE.get(installation, 12))

        nb_total_2026 = sum(nb_campagnes_attendues(ins) for ins in INSTALLATIONS_SUIVIES) * len(SITES_SUIVIS)

        # Un contrôle est compté comme réalisé en 2026 dès lors que sa DATE RÉELLE de visite
        # tombe en 2026, quelle que soit l'année de l'échéance théorique associée.
        df_realises_2026 = df_k[df_k["_date_reelle"].notna() & (df_k["_date_reelle"].dt.year == 2026)].copy()
        if col_site_k:
            df_realises_2026 = df_realises_2026[df_realises_2026[col_site_k[0]].astype(str).str.strip().isin(SITES_SUIVIS)]

        nb_realises_2026 = 0
        for site in SITES_SUIVIS:
            for ins in INSTALLATIONS_SUIVIES:
                attendu = nb_campagnes_attendues(ins)
                df_grp = df_realises_2026[df_realises_2026[col_ins_k[0]].astype(str).str.strip() == ins]
                if col_site_k:
                    df_grp = df_grp[df_grp[col_site_k[0]].astype(str).str.strip() == site]
                # Une "campagne" réalisée = une date réelle distincte (mois/échéance) pour cette
                # installation sur ce site, plafonnée au nombre de contrôles attendus par an.
                nb_campagnes_realisees = df_grp["_date_brute"].nunique() if not df_grp.empty else 0
                nb_realises_2026 += min(nb_campagnes_realisees, attendu)

        nb_restants_2026 = nb_total_2026 - nb_realises_2026
        taux1 = round(nb_realises_2026/nb_total_2026*100,1) if nb_total_2026>0 else 0
    


        # ---- KPI 2 : Taux de respect de délai de visite (écart ≤ 1 mois entre date planifiée et date de dernière visite) ----
        # On ne considère que les contrôles dont la visite a réellement eu lieu en 2026
        # (certains contrôles réalisés figurent avec une date réelle en 2025 et ne doivent pas être comptés ici).
        df_realises_k = df_k[df_k["_date_reelle"].notna() & (df_k["_date_reelle"].dt.year == 2026)].copy()
        nb_visites_realisees = len(df_realises_k)
        if nb_visites_realisees > 0:
            df_realises_k["_ecart"] = (df_realises_k["_date_reelle"] - df_realises_k["_date_planifiee"]).dt.days.abs()
            nb_respectes = int((df_realises_k["_ecart"] <= 31).sum())
        else:
            nb_respectes = 0
        nb_non_respectes = nb_visites_realisees - nb_respectes
        taux2 = round(nb_respectes/nb_visites_realisees*100,1) if nb_visites_realisees>0 else 0

        # ---- Sous-totaux PAR SITE, pour le dashboard comparatif SGB vs MEG ----
        comparatif_sites = {}
        for site_c in SITES_SUIVIS:
            total_site_c = sum(nb_campagnes_attendues(ins) for ins in INSTALLATIONS_SUIVIES)
            realises_site_c = 0
            for ins in INSTALLATIONS_SUIVIES:
                attendu_c = nb_campagnes_attendues(ins)
                df_grp_c = df_realises_2026[df_realises_2026[col_ins_k[0]].astype(str).str.strip() == ins]
                if col_site_k:
                    df_grp_c = df_grp_c[df_grp_c[col_site_k[0]].astype(str).str.strip() == site_c]
                realises_site_c += min(df_grp_c["_date_brute"].nunique() if not df_grp_c.empty else 0, attendu_c)
            df_realises_site_c = df_realises_k[df_realises_k[col_site_k[0]].astype(str).str.strip() == site_c] if col_site_k else df_realises_k.iloc[0:0]
            nb_visites_site_c = len(df_realises_site_c)
            nb_respectes_site_c = int((df_realises_site_c["_ecart"] <= 31).sum()) if nb_visites_site_c > 0 and "_ecart" in df_realises_site_c.columns else 0
            comparatif_sites[site_c] = {
                "taux_realisation": round(realises_site_c/total_site_c*100,1) if total_site_c else 0,
                "realises": realises_site_c, "total": total_site_c,
                "taux_delai": round(nb_respectes_site_c/nb_visites_site_c*100,1) if nb_visites_site_c else 0,
                "visites": nb_visites_site_c,
            }



        kpi_data = {
            "kpi1": {"taux":taux1, "realises":nb_realises_2026, "restants":nb_restants_2026, "total":nb_total_2026},
            "kpi2": {"taux":taux2, "respectes":nb_respectes, "non_respectes":nb_non_respectes, "total":nb_visites_realisees}
        }




        k1c,k2c = st.columns(2)

        with k1c:
            st.markdown("<p style='text-align:center;font-weight:600;color:#1E293B;font-size:14px;'>Taux de réalisation 2026</p></p>",unsafe_allow_html=True)
            if nb_total_2026>0:
                dfp1=pd.DataFrame({"Statut":["Réalisés","Restants"],"Nombre":[nb_realises_2026,nb_restants_2026]})
                fig1=px.pie(dfp1,values="Nombre",names="Statut",hole=0.6,color="Statut",
                            color_discrete_map={"Réalisés":"#10B981","Restants":"#EF4444"})
                fig1.update_traces(textposition='inside',textinfo='percent')
                fig1.update_layout(margin=dict(t=10,b=10,l=10,r=10),height=260,showlegend=False,
                                    paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
                                    transition_duration=500,transition_easing="cubic-in-out")
                st.plotly_chart(fig1,use_container_width=True,config={'displayModeBar':False})
                st.markdown(f"<p style='text-align:center;font-size:13px;color:#64748B;'>{taux1}% réalisés ({nb_realises_2026}/{nb_total_2026} contrôles d'installation)</p>",unsafe_allow_html=True)
            else:
                st.info("Aucune échéance d'installation en 2026.")

        with k2c:
            st.markdown("<p style='text-align:center;font-weight:600;color:#1E293B;font-size:14px;'>Respect délai de visite (≤ 1 mois)</p>",unsafe_allow_html=True)
            if nb_visites_realisees>0:
                dfp2=pd.DataFrame({"Statut":["Respecté","Non respecté"],"Nombre":[nb_respectes,nb_non_respectes]})
                fig2=px.pie(dfp2,values="Nombre",names="Statut",hole=0.6,color="Statut",
                            color_discrete_map={"Respecté":"#0EA5E9","Non respecté":"#EF4444"})
                fig2.update_traces(textposition='inside',textinfo='percent')
                fig2.update_layout(margin=dict(t=10,b=10,l=10,r=10),height=260,showlegend=False,
                                    paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
                                    transition_duration=500,transition_easing="cubic-in-out")
                st.plotly_chart(fig2,use_container_width=True,config={'displayModeBar':False})
                st.markdown(f"<p style='text-align:center;font-size:13px;color:#64748B;'>{taux2}% respectés ({nb_respectes}/{nb_visites_realisees})</p>",unsafe_allow_html=True)
            else:
                st.info("Aucune visite réalisée à ce jour.")

    st.markdown("<br><hr style='border-color:#E2E8F0;'>",unsafe_allow_html=True)

    # ================= TAUX DE NON-CONFORMITÉ DE SITE (CARTOGRAPHIE) =================
    st.markdown("<p style='font-size:1.2rem;font-weight:700;color:#0F172A;'>🗺️ Taux de non-conformité de site</p>",unsafe_allow_html=True)

    carto_b64 = _charger_cartographie_b64()
    if carto_b64:
        vc1,vc2 = st.columns([5,1])
        with vc2:
            st.markdown(f"<a href='{LUCID_CARTOGRAPHIE_URL}' target='_blank' style='display:inline-block;background:#1E3A8A;color:white;padding:8px 14px;border-radius:8px;text-decoration:none;font-weight:600;font-size:13px;text-align:center;'>🔗 Ouvrir dans Lucid</a>",unsafe_allow_html=True)
        components.html(f"""
        <div id="carto-viewer" style="position:relative;width:100%;height:620px;overflow:hidden;
             background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;">
          <img id="carto-img" src="data:image/png;base64,{carto_b64}"
               style="position:absolute;top:0;left:0;transform-origin:0 0;cursor:grab;user-select:none;max-width:none;visibility:hidden;"
               draggable="false"/>
          <div style="position:absolute;bottom:14px;right:14px;display:flex;gap:8px;z-index:10;">
            <button id="carto-zoom-in" style="width:36px;height:36px;border-radius:8px;border:1px solid #CBD5E1;background:white;font-size:16px;font-weight:700;cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,0.08);">➕</button>
            <button id="carto-zoom-out" style="width:36px;height:36px;border-radius:8px;border:1px solid #CBD5E1;background:white;font-size:16px;font-weight:700;cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,0.08);">➖</button>
            <button id="carto-reset" style="width:36px;height:36px;border-radius:8px;border:1px solid #CBD5E1;background:white;font-size:15px;cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,0.08);">⟳</button>
          </div>
          <div style="position:absolute;top:10px;left:14px;font-size:11px;color:#64748B;background:rgba(255,255,255,0.85);
               padding:4px 10px;border-radius:6px;">🖱️ Molette pour zoomer • Glisser pour déplacer</div>
        </div>
        <script>
        (function(){{
            let baseScale=1, scale=1, posX=0, posY=0, isDragging=false, startX=0, startY=0;
            const viewer=document.getElementById('carto-viewer');
            const img=document.getElementById('carto-img');

            function apply(){{ img.style.transform = 'translate('+posX+'px,'+posY+'px) scale('+scale+')'; }}

            function fitToView(){{
                const cw = viewer.clientWidth, ch = viewer.clientHeight;
                const nw = img.naturalWidth, nh = img.naturalHeight;
                if(!nw || !nh) return;
                baseScale = Math.min(cw/nw, ch/nh);
                scale = baseScale;
                posX = (cw - nw*scale)/2;
                posY = (ch - nh*scale)/2;
                img.style.visibility = 'visible';
                apply();
            }}

            function zoom(factor){{
                scale*=factor;
                scale=Math.max(baseScale*0.9, Math.min(scale, baseScale*8));
                apply();
            }}

            function tryFit(attempts){{
                if(img.naturalWidth){{ fitToView(); }}
                else if(attempts>0){{ setTimeout(function(){{ tryFit(attempts-1); }}, 30); }}
            }}
            tryFit(100);
            img.addEventListener('load', fitToView);

            document.getElementById('carto-zoom-in').addEventListener('click', function(){{ zoom(1.25); }});
            document.getElementById('carto-zoom-out').addEventListener('click', function(){{ zoom(0.8); }});
            document.getElementById('carto-reset').addEventListener('click', fitToView);
            img.addEventListener('wheel', function(e){{
                e.preventDefault();
                zoom(e.deltaY<0 ? 1.1 : 0.9);
            }}, {{passive:false}});
            img.addEventListener('mousedown', function(e){{ isDragging=true; startX=e.clientX-posX; startY=e.clientY-posY; img.style.cursor='grabbing'; }});
            window.addEventListener('mouseup', function(){{ isDragging=false; img.style.cursor='grab'; }});
            window.addEventListener('mousemove', function(e){{ if(!isDragging) return; posX=e.clientX-startX; posY=e.clientY-startY; apply(); }});
        }})();
        </script>
        """, height=630, scrolling=False)
    else:
        st.warning("⚠️ Fichier « Cartographie.png » introuvable. Placez-le dans le même dossier que l'application (à côté de app.py) pour l'afficher ici.")
        st.markdown(f"[🔗 Consulter la cartographie sur Lucid]({LUCID_CARTOGRAPHIE_URL})")

    st.markdown("<br><hr style='border-color:#E2E8F0;'>",unsafe_allow_html=True)

    # ================= Actions de contrôle =================
    st.markdown("<p style='font-size:1.2rem;font-weight:700;color:#0F172A;'>📌 Actions de contrôle</p>",unsafe_allow_html=True)

    with st.spinner("Chargement des actions..."):
        df_reserve = lire_points_reserve()

    with st.expander("➕ Ajouter une action"):
        r1,r2,r3,r4 = st.columns([1,1.5,1.5,1])
        with r1:
            res_site = st.selectbox("Site",["SGB","MEG"],key="res_site_new")
        with r2:
            res_ins = st.selectbox("Installation",list(PERIODICITE.keys()),key="res_ins_new")
        with r3:
            res_seq = st.text_input("Sous-équipement",key="res_seq_new")
        with r4:
            res_nb = st.number_input("Nb points",min_value=1,value=1,key="res_nb_new")
        if st.button("💾 Enregistrer",key="btn_add_reserve"):
            if res_seq.strip():
                ok,err = ajouter_point_reserve(res_site,res_ins,res_seq.strip(),res_nb)
                if ok:
                    st.success("✅ Point de réserve ajouté !")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Erreur : {err}")
            else:
                st.warning("Veuillez saisir un sous-équipement.")

    if df_reserve.empty:
        st.info("Aucun point de réserve enregistré. Utilisez le formulaire ci-dessus pour en ajouter.")
    else:
        if "Nombre" in df_reserve.columns:
            df_reserve["Nombre"] = pd.to_numeric(df_reserve["Nombre"],errors="coerce").fillna(0).astype(int)

        with st.container(border=True):
            st.markdown("<p style='font-weight:600;color:#1E293B;margin:0 0 10px 0;font-size:13px;'>🔍 Filtrer les Actions de contrôle</p>",unsafe_allow_html=True)
            fr1,fr2,fr3 = st.columns(3)
            sites_dispo = ["Tous"]+sorted(df_reserve["Site"].dropna().unique().tolist()) if "Site" in df_reserve.columns else ["Tous"]
            inss_dispo  = ["Tous"]+sorted(df_reserve["Installation"].dropna().unique().tolist()) if "Installation" in df_reserve.columns else ["Tous"]
            with fr1: f_res_site = st.selectbox("Site",sites_dispo,key="f_res_site")
            with fr2: f_res_ins  = st.selectbox("Installation",inss_dispo,key="f_res_ins")
            with fr3: f_res_seq  = st.text_input("Recherche sous-équipement",key="f_res_seq")

        df_reserve_f = df_reserve.copy()
        if f_res_site!="Tous" and "Site" in df_reserve_f.columns:
            df_reserve_f = df_reserve_f[df_reserve_f["Site"]==f_res_site]
        if f_res_ins!="Tous" and "Installation" in df_reserve_f.columns:
            df_reserve_f = df_reserve_f[df_reserve_f["Installation"]==f_res_ins]
        if f_res_seq.strip() and "Sous_equipement" in df_reserve_f.columns:
            df_reserve_f = df_reserve_f[df_reserve_f["Sous_equipement"].astype(str).str.contains(f_res_seq.strip(),case=False,na=False)]

        st.dataframe(df_reserve_f.rename(columns={
            "Site":"Site","Installation":"Installation","Sous_equipement":"Sous équipement","Nombre":"Nombre des actions de contrôle"
        }),hide_index=True,use_container_width=True)

        st.markdown("<br>",unsafe_allow_html=True)

        # --- Répartition par site : graphique centré ---
        csite1,csite2,csite3 = st.columns([1,2,1])
        with csite2:
            if "Site" in df_reserve_f.columns and not df_reserve_f.empty:
                df_by_site = df_reserve_f.groupby("Site")["Nombre"].sum().reset_index()
                figS = px.pie(df_by_site,values="Nombre",names="Site",hole=0.6,
                              color_discrete_sequence=['#1E3A8A','#0EA5E9','#94A3B8'])
                figS.update_traces(textposition='inside',textinfo='percent+label')
                figS.update_layout(title="Répartition par site",title_x=0.5,margin=dict(t=40,b=10,l=10,r=10),height=280,
                                    paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(figS,use_container_width=True,config={'displayModeBar':False})
            else:
                st.info("Aucune donnée à afficher pour le graphe par site.")

        st.markdown("<br>",unsafe_allow_html=True)
        st.markdown("<p style='font-weight:700;font-size:14px;color:#0F172A;text-align:center;margin-bottom:10px;'>Répartition par installation</p>",unsafe_allow_html=True)

        # --- Répartition par installation : MEG (gauche) | légende (milieu) | SGB (droite) ---
        if "Installation" in df_reserve_f.columns and "Site" in df_reserve_f.columns and not df_reserve_f.empty:
            all_inss = sorted(df_reserve_f["Installation"].dropna().unique().tolist())
            palette = px.colors.qualitative.Set1
            color_map = {ins: palette[i % len(palette)] for i,ins in enumerate(all_inss)}

            gins1,gins2,gins3 = st.columns([2,1,2])

            with gins1:
                df_meg_ins = df_reserve_f[df_reserve_f["Site"]=="MEG"].groupby("Installation")["Nombre"].sum().reset_index()
                if not df_meg_ins.empty:
                    figMEG = px.pie(df_meg_ins,values="Nombre",names="Installation",hole=0.6,
                                     color="Installation",color_discrete_map=color_map)
                    figMEG.update_traces(textposition='inside',textinfo='percent',showlegend=False)
                    figMEG.update_layout(title="MEG",title_x=0.5,showlegend=False,
                                          margin=dict(t=40,b=10,l=10,r=10),height=260,
                                          paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(figMEG,use_container_width=True,config={'displayModeBar':False})
                else:
                    st.info("Aucune donnée MEG.")

            with gins2:
                legende_items = "".join(
                    f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:12px;'>"
                    f"<span style='width:12px;height:12px;min-width:12px;border-radius:3px;background:{color_map[ins]};display:inline-block;'></span>"
                    f"<span style='font-size:11.5px;color:#334155;'>{ins}</span>"
                    f"</div>"
                    for ins in all_inss
                )
                legende_html = f"<div style='padding-top:35px;'>{legende_items}</div>"
                st.markdown(legende_html,unsafe_allow_html=True)

            with gins3:
                df_sgb_ins = df_reserve_f[df_reserve_f["Site"]=="SGB"].groupby("Installation")["Nombre"].sum().reset_index()
                if not df_sgb_ins.empty:
                    figSGB = px.pie(df_sgb_ins,values="Nombre",names="Installation",hole=0.6,
                                     color="Installation",color_discrete_map=color_map)
                    figSGB.update_traces(textposition='inside',textinfo='percent',showlegend=False)
                    figSGB.update_layout(title="SGB",title_x=0.5,showlegend=False,
                                          margin=dict(t=40,b=10,l=10,r=10),height=260,
                                          paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(figSGB,use_container_width=True,config={'displayModeBar':False})
                else:
                    st.info("Aucune donnée SGB.")
        else:
            st.info("Aucune donnée à afficher pour le graphe par installation.")

        with st.expander("🗑️ Supprimer une action"):
            for orig_idx,row_r in df_reserve.iterrows():
                dcx1,dcx2 = st.columns([5,1])
                with dcx1:
                    st.write(f"{row_r.get('Site','')} — {row_r.get('Installation','')} — {row_r.get('Sous_equipement','')} — {row_r.get('Nombre',0)} pt(s)")
                with dcx2:
                    if st.button("🗑️",key=f"del_res_{orig_idx}"):
                        num_ligne_sheet = orig_idx+2
                        if supprimer_ligne_generique("PointsReserve",num_ligne_sheet,4):
                            st.success("Supprimé !")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("Erreur lors de la suppression.")

    # ================= Actions de contrôle PAR NATURE =================
    st.markdown("<br><hr style='border-color:#E2E8F0;'>",unsafe_allow_html=True)
    st.markdown("<p style='font-size:1.2rem;font-weight:700;color:#0F172A;'>🧭 Actions de contrôle par nature</p>",unsafe_allow_html=True)

    with st.spinner("Chargement des actions par nature..."):
        df_nature = lire_points_reserve_nature()

    with st.expander("➕ Ajouter une ligne"):
        nt1,nt2,nt3,nt4 = st.columns([1,1.5,1,1.5])
        with nt1:
            nat_site = st.selectbox("Site",["SGB","MEG"],key="nat_site_new")
        with nt2:
            nat_ins = st.selectbox("Installation",list(PERIODICITE.keys()),key="nat_ins_new")
        with nt3:
            nat_nb = st.number_input("Nb points",min_value=1,value=1,key="nat_nb_new")
        with nt4:
            nat_code = st.selectbox("Nature",list(NATURE_PILOTE.keys()),
                                     format_func=lambda c: f"{c} — {NATURE_PILOTE[c][0]}",key="nat_code_new")
        nat_pilote_auto = NATURE_PILOTE[nat_code][1]
        st.markdown(
            f"<p style='font-size:12.5px;color:#64748B;margin-top:-4px;'>Pilote assigné automatiquement : "
            f"<b style='color:#1E3A8A;'>{nat_pilote_auto}</b></p>",unsafe_allow_html=True)
        if st.button("💾 Enregistrer",key="btn_add_nature"):
            ok,err = ajouter_point_reserve_nature(nat_site,nat_ins,nat_nb,nat_code)
            if ok:
                st.success("✅ Ligne ajoutée !")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(f"Erreur : {err}")

    if df_nature.empty:
        st.info("Aucune donnée enregistrée. Utilisez le formulaire ci-dessus pour en ajouter.")
    else:
        if "Nombre" in df_nature.columns:
            df_nature["Nombre"] = pd.to_numeric(df_nature["Nombre"],errors="coerce").fillna(0).astype(int)

        with st.container(border=True):
            st.markdown("<p style='font-weight:600;color:#1E293B;margin:0 0 10px 0;font-size:13px;'>🔍 Filtrer</p>",unsafe_allow_html=True)
            fn1,fn2 = st.columns(2)
            sites_dispo_n = ["Tous"]+sorted(df_nature["Site"].dropna().unique().tolist()) if "Site" in df_nature.columns else ["Tous"]
            inss_dispo_n  = ["Tous"]+sorted(df_nature["Installation"].dropna().unique().tolist()) if "Installation" in df_nature.columns else ["Tous"]
            with fn1: f_nat_site = st.selectbox("Site",sites_dispo_n,key="f_nat_site")
            with fn2: f_nat_ins  = st.selectbox("Installation",inss_dispo_n,key="f_nat_ins")

        df_nature_f = df_nature.copy()
        if f_nat_site!="Tous" and "Site" in df_nature_f.columns:
            df_nature_f = df_nature_f[df_nature_f["Site"]==f_nat_site]
        if f_nat_ins!="Tous" and "Installation" in df_nature_f.columns:
            df_nature_f = df_nature_f[df_nature_f["Installation"]==f_nat_ins]

        st.dataframe(df_nature_f.rename(columns={
            "Site":"Site","Installation":"Installation","Nombre":"Nombre des actions","Nature":"Nature","Pilote":"Pilote"
        }),hide_index=True,use_container_width=True)

        st.markdown("<br>",unsafe_allow_html=True)
        st.markdown("<p style='font-weight:700;font-size:14px;color:#0F172A;text-align:center;margin-bottom:10px;'>Répartition par site : Nature et Pilote</p>",unsafe_allow_html=True)

        # --- Grille 2x2 : ligne 1 = SGB (Nature | Pilote), ligne 2 = MEG (Nature | Pilote) ---
        all_natures = [v[0] for v in NATURE_PILOTE.values()]
        palette_nat = px.colors.qualitative.Set2
        color_map_nat = {n: palette_nat[i % len(palette_nat)] for i,n in enumerate(all_natures)}

        # Les pilotes sont parfois combinés (ex: "BT + Maintenance", "BT + HSE + RH + DG").
        # On isole chaque entité (Maintenance, BT, HSE, RH, DG, DMTN, Chef service BT, ...)
        # pour calculer un % propre à chacune, même quand elle est partagée entre plusieurs natures.
        entites_atomiques = sorted(set(
            e.strip() for v in NATURE_PILOTE.values() for e in v[1].split("+") if e.strip()
        ))
        palette_pil = px.colors.qualitative.Set1
        color_map_pil = {p: palette_pil[i % len(palette_pil)] for i,p in enumerate(entites_atomiques)}

        def _pie_nature_site(df_src, site, color_map, titre):
            if "Nombre" not in df_src.columns or "Nature" not in df_src.columns or "Site" not in df_src.columns:
                st.info(f"Aucune donnée {site}.")
                return
            d = df_src[df_src["Site"]==site].groupby("Nature")["Nombre"].sum().reset_index()
            if d.empty:
                st.info(f"Aucune donnée {site}.")
                return
            fig = px.pie(d,values="Nombre",names="Nature",hole=0.6,color="Nature",color_discrete_map=color_map)
            fig.update_traces(textposition='inside',textinfo='percent')
            fig.update_layout(title=titre,title_x=0.5,margin=dict(t=40,b=10,l=10,r=10),height=280,
                               paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
                               legend=dict(font=dict(size=9)))
            st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})

        def _bar_pilote_site(df_src, site, color_map, titre):
            if "Nombre" not in df_src.columns or "Pilote" not in df_src.columns or "Site" not in df_src.columns:
                st.info(f"Aucune donnée {site}.")
                return
            d = df_src[df_src["Site"]==site]
            if d.empty:
                st.info(f"Aucune donnée {site}.")
                return
            total = d["Nombre"].sum()
            compte = {}
            for _,row in d.iterrows():
                for e in str(row["Pilote"]).split("+"):
                    e = e.strip()
                    if not e: continue
                    compte[e] = compte.get(e,0) + row["Nombre"]
            if not compte or total==0:
                st.info(f"Aucune donnée {site}.")
                return
            dd = pd.DataFrame({"Pilote":list(compte.keys()),"Nombre":list(compte.values())})
            dd["Pourcentage"] = (dd["Nombre"]/total*100).round(1)
            dd = dd.sort_values("Pourcentage",ascending=True)
            fig = px.bar(dd,x="Pourcentage",y="Pilote",orientation="h",text="Pourcentage",
                         color="Pilote",color_discrete_map=color_map)
            fig.update_traces(texttemplate='%{text}%',textposition='outside',cliponaxis=False)
            fig.update_layout(title=titre,title_x=0.5,showlegend=False,
                               xaxis_title="% des actions",yaxis_title="",
                               margin=dict(t=40,b=10,l=10,r=30),height=280,
                               paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})

        if {"Nature","Pilote","Site","Nombre"}.issubset(df_nature_f.columns):
            g1, g2 = st.columns(2)
            with g1: _pie_nature_site(df_nature_f,"SGB",color_map_nat,"SGB — % par nature")
            with g2: _bar_pilote_site(df_nature_f,"SGB",color_map_pil,"SGB — % par pilote")
            g3,g4 = st.columns(2)
            with g3: _pie_nature_site(df_nature_f,"MEG",color_map_nat,"MEG — % par nature")
            with g4: _bar_pilote_site(df_nature_f,"MEG",color_map_pil,"MEG — % par pilote")
        else:
            st.info("Aucune donnée à afficher pour les graphes.")

        with st.expander("🗑️ Supprimer une ligne"):
            for orig_idx,row_n in df_nature.iterrows():
                dnx1,dnx2 = st.columns([5,1])
                with dnx1:
                    st.write(f"{row_n.get('Site','')} — {row_n.get('Installation','')} — {row_n.get('Nombre',0)} pt(s) — {row_n.get('Nature','')} — {row_n.get('Pilote','')}")
                with dnx2:
                    if st.button("🗑️",key=f"del_nat_{orig_idx}"):
                        num_ligne_sheet = orig_idx+2
                        if supprimer_ligne_generique("PointsReserveNature",num_ligne_sheet,5):
                            st.success("Supprimé !")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("Erreur lors de la suppression.")

    # ================= RAPPORT PDF PAR PILOTE (CODIFICATION EXTERNE) =================
    st.markdown("<br><hr style='border-color:#E2E8F0;'>",unsafe_allow_html=True)
    st.markdown("<p style='font-size:1.2rem;font-weight:700;color:#0F172A;'>📄 Rapport des actions par Pilote</p>",unsafe_allow_html=True)

    entites_pilote_codif = sorted(set(
        e.strip() for v in NATURE_PILOTE.values() for e in v[1].split("+") if e.strip()
    ))
    cpil1,cpil2 = st.columns([3,1])
    with cpil1:
        pilote_codif_choisi = st.selectbox("Pilote",entites_pilote_codif,key="pilote_codif_select")
    with cpil2:
        st.write("")
        st.write("")
        charger_classeur_pilote = st.button("🔍 Charger les installations",use_container_width=True,key="btn_charger_classeur_pilote")

    if charger_classeur_pilote:
        with st.spinner("Lecture des classeurs de codification (MEG et SGB)..."):
            df_codif_brut, err = codif_charger_toutes_actions()
            if err and df_codif_brut.empty:
                st.session_state["classeur_codif_pilote"] = None
                st.error(err)
            else:
                if err:
                    st.warning(err)
                st.session_state["classeur_codif_pilote"] = df_codif_brut
                st.session_state["pdf_pilote"] = None

    classeur_pilote = st.session_state.get("classeur_codif_pilote")

    if classeur_pilote is None or (hasattr(classeur_pilote,"empty") and classeur_pilote.empty):
        st.info("👆 Cliquez sur « Charger les installations » pour sélectionner précisément "
                 "le site et l'installation à inclure dans le rapport.")
    else:
        df_codif = classeur_pilote.copy()
        # Exclut les actions déjà cochées comme réalisées par un responsable
        df_realisees_pilote = lire_actions_realisees()
        if not df_realisees_pilote.empty:
            cles_faites = set(df_realisees_pilote.apply(_cle_action, axis=1))
            df_codif = df_codif[~df_codif.apply(_cle_action, axis=1).isin(cles_faites)]

        df_codif["Nature"] = df_codif["Code"].map(lambda c: NATURE_PILOTE.get(c,("",""))[0])
        codes_ok = _codes_pour_pilote(pilote_codif_choisi)
        df_pilote_codif = df_codif[df_codif["Code"].isin(codes_ok)]

        if df_pilote_codif.empty:
            st.info(f"Aucune action restante pour le pilote « {pilote_codif_choisi} » "
                    f"(codes recherchés : {', '.join(codes_ok) if codes_ok else '—'}).")
        else:
                installations_dispo = sorted(df_pilote_codif["Installation"].unique().tolist())
                sites_dispo = sorted(df_pilote_codif["Site"].dropna().unique().tolist())

                cfil1,cfil2 = st.columns(2)
                with cfil1:
                    if sites_dispo:
                        site_filtre_pilote = st.selectbox(
                            "Site", ["Tous"]+sites_dispo, key="site_filtre_pilote_codif"
                        )
                    else:
                        site_filtre_pilote = "Tous"
                installations_apres_site = [
                    i for i in installations_dispo
                    if site_filtre_pilote == "Tous" or i in
                       df_pilote_codif[df_pilote_codif["Site"]==site_filtre_pilote]["Installation"].unique()
                ]
                with cfil2:
                    installation_filtre_pilote = st.selectbox(
                        "Installation", ["Toutes"]+installations_apres_site,
                        key="installation_filtre_pilote_codif"
                    )

                if installation_filtre_pilote == "Toutes":
                    df_filtre_codif = df_pilote_codif[df_pilote_codif["Installation"].isin(installations_apres_site)]
                else:
                    df_filtre_codif = df_pilote_codif[df_pilote_codif["Installation"] == installation_filtre_pilote]


                lancer_rapport_pilote = st.button(
                    "👁️ Générer",use_container_width=True,key="btn_gen_rapport_pilote",type="primary"
                )

                if lancer_rapport_pilote:
                    if df_filtre_codif.empty:
                        st.session_state["pdf_pilote"] = None
                        st.info(f"Aucune action trouvée pour le pilote « {pilote_codif_choisi} » "
                                f"avec les filtres sélectionnés.")
                    else:
                        try:
                            st.session_state["pdf_pilote"] = generer_rapport_pilote_pdf(
                                pilote_codif_choisi, df_filtre_codif,
                                LOGO_URL
                            )
                            st.session_state["nb_actions_pilote"] = len(df_filtre_codif)
                            st.session_state["pilote_pdf_nom"] = pilote_codif_choisi
                        except Exception as e:
                            st.session_state["pdf_pilote"] = None
                            st.error(f"Erreur lors de la génération du PDF : {e}")

    if st.session_state.get("pdf_pilote"):
        st.success(f"{st.session_state.get('nb_actions_pilote',0)} action(s) trouvée(s) pour "
                   f"« {st.session_state.get('pilote_pdf_nom','')} ».")
        afficher_apercu_pdf_grille(st.session_state["pdf_pilote"], colonnes=2)
        st.download_button(
            label="📥 Télécharger le rapport PDF",
            data=st.session_state["pdf_pilote"],
            file_name=f"Rapport_{st.session_state.get('pilote_pdf_nom','pilote')}_{datetime.date.today().strftime('%d_%m_%Y')}.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="dl_pilote"
        )

    # ================= RAPPORT PDF PREMIUM =================
    st.markdown("<br><hr style='border-color:#E2E8F0;'>",unsafe_allow_html=True)
    st.markdown("<p style='font-size:1.2rem;font-weight:700;color:#0F172A;'>📄 Rapport PDF </p>",unsafe_allow_html=True)

    if kpi_data is None:
        st.info("Le rapport PDF nécessite des données KPI disponibles (onglet « Rapports » non vide).")
    else:
        st.markdown(
            "<div style='background:white;padding:16px 20px;border-radius:10px;"
            "box-shadow:0 2px 8px rgba(0,0,0,0.05);border-left:4px solid #1E3A8A;"
            "margin-bottom:10px;'>"
            "<span style='font-size:14px;font-weight:600;color:#1E293B;'>📑 Rapport PDF — Synthèse KPI</span>"
            "</div>", unsafe_allow_html=True)
        if st.button("👁️ Consulter le rapport", use_container_width=True, key="consult_kpi", type="primary"):
            with st.spinner("Préparation du rapport PDF..."):
                try:
                    st.session_state["pdf_kpi"] = generer_rapport_kpi_pdf(
                        kpi_data,
                        df_reserve,
                        df_nature,
                        carto_b64,
                        LOGO_URL
                    )
                except Exception as e:
                    st.session_state["pdf_kpi"] = None
                    st.error(f"Erreur lors de la génération du PDF : {e}")
        if st.session_state.get("pdf_kpi"):
            afficher_apercu_pdf_grille(st.session_state["pdf_kpi"], colonnes=2)
            st.download_button(
                label="📥 Télécharger le rapport PDF",
                data=st.session_state["pdf_kpi"],
                file_name=f"Rapport_KPI_{datetime.date.today().strftime('%d_%m_%Y')}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="dl_kpi"
            )
    # ---- Export global (toutes les données, tous sites/années, en un seul fichier) ----
    st.markdown("<br><hr style='border-color:#E2E8F0;'>",unsafe_allow_html=True)
    st.markdown("<br>",unsafe_allow_html=True)
    st.markdown("### 📦 Export global")
    st.caption("Génère un classeur Excel regroupant tous les rapports.")
    if st.button("📥 Générer le classeur", use_container_width=True):
        with st.spinner("Génération de l'export global..."):
            excel_global = generer_export_global_excel(df_rapports, df_planning)
        st.download_button("⬇️ Télécharger le classeur", data=excel_global,
            file_name=f"Export_Global_{datetime.date.today().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)
        journaliser_action(utilisateur_courant(), "Export global généré")




        # ---- ONGLET 4 : KPI (Responsable — vue filtrée sur ses propres actions/rapport) ----
