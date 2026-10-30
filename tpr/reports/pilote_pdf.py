"""Rapport PDF par pilote."""

import datetime

from weasyprint import HTML

from tpr.domain.pilotes import nom_pour_pilote_site


def _lignes_avec_rowspan(d_ins):
    """Regroupe les lignes consécutives ayant le même Equipement (Désignation) pour permettre
    une fusion de cellules (rowspan) dans le tableau PDF.
    Retourne une liste de tuples (equipement_ou_None, rowspan_ou_None, observation)."""
    valeurs = d_ins["Désignation"].tolist()
    obs = d_ins["Observation"].tolist()
    lignes = []
    i, n = 0, len(valeurs)
    while i < n:
        j = i
        while j < n and valeurs[j] == valeurs[i]:
            j += 1
        span = j - i
        lignes.append((valeurs[i], span, obs[i]))
        for k in range(i + 1, j):
            lignes.append((None, None, obs[k]))
        i = j
    return lignes

def generer_rapport_pilote_pdf(pilote_choisi, df_filtre, logo_url):
    """
    Génère un rapport PDF (format paysage) listant, pour un pilote donné, toutes les actions de
    la codification (classeur externe) qui le concernent — une page par installation
    (= un onglet du classeur source), sous forme de fiche de suivi terrain :
    Equipement | Actions | Responsable | Etat (Immédiat/Sous-traitant*/Planifié*) | Réalisation (O/N) | Observation.
    df_filtre doit contenir les colonnes : Installation, Désignation, Observation, Code, Nature.
    """
    date_str = datetime.date.today().strftime('%d/%m/%Y')
    installations = list(dict.fromkeys(df_filtre["Installation"].tolist()))  # ordre stable, sans doublons
    total_general = len(df_filtre)

    # Détermine le(s) site(s) présent(s) dans le périmètre filtré, afin d'afficher le bon
    # sous-pilote (ex : Maintenance -> Chafik ABID pour SGB, Saber BEN CHAABEN pour MEG).
    sites_presents = []
    if "Site" in df_filtre.columns:
        sites_presents = sorted({
            str(s).strip().upper() for s in df_filtre["Site"].dropna().unique().tolist() if str(s).strip()
        })

    def _nom_pour_site(site_val):
        return nom_pour_pilote_site(pilote_choisi, site_val)

    if len(sites_presents) == 1:
        nom_responsable = _nom_pour_site(sites_presents[0])
    else:
        # Plusieurs sites (ou site inconnu) dans le même rapport : on garde le libellé générique.
        nom_responsable = _nom_pour_site(None)

    # Nom du sous-pilote par installation (une installation appartient toujours à un seul site).
    nom_par_installation = {}
    for ins in installations:
        site_ins = None
        if "Site" in df_filtre.columns:
            valeurs_site = df_filtre.loc[df_filtre["Installation"] == ins, "Site"].dropna().unique().tolist()
            if len(valeurs_site) == 1:
                site_ins = valeurs_site[0]
        nom_par_installation[ins] = _nom_pour_site(site_ins)

    html_content = """
    <html>
    <head>
    <style>
        @page {
            size: A4 landscape;
            margin: 15mm 12mm;
            @bottom-right {
                content: "Page " counter(page) " / " counter(pages);
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                font-size: 9pt;
                color: #64748B;
            }
        }
        body {
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            color: #1E293B;
            margin: 0;
            padding: 0;
            font-size: 10pt;
        }
        .page { page-break-after: always; }
        .page:last-child { page-break-after: avoid; }
        .header-title {
            text-align: center;
            font-size: 16pt;
            font-weight: bold;
            color: #1E3A8A;
            margin-bottom: 14px;
            text-transform: uppercase;
            border-bottom: 2px solid #1E3A8A;
            padding-bottom: 8px;
        }
        .page-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid #E2E8F0;
        }
        .page-header img { height: 32px; }
        .page-header-text {
            font-size: 9.5pt;
            color: #64748B;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.4px;
        }
        .meta-info {
            margin-bottom: 14px;
            background-color: #F8FAFC;
            border: 1px solid #E2E8F0;
            padding: 10px 15px;
            border-radius: 6px;
            line-height: 1.7;
            font-size: 10.5pt;
        }
        .category-title {
            font-size: 13pt;
            color: #0EA5E9;
            font-weight: bold;
            margin-top: 6px;
            margin-bottom: 10px;
            border-left: 4px solid #0EA5E9;
            padding-left: 8px;
        }
        table { width: 100%; border-collapse: collapse; margin-bottom: 14px; }
        th, td { border: 1px solid #CBD5E1; padding: 6px; text-align: left; font-size: 8.5pt; vertical-align: middle; }
        th {
            background-color: #1406BE; color: #FFFFFF; font-weight: bold;
            text-align: center; font-size: 8.5pt;
        }
        .col-equip  { width: 13%; }
        .col-action { width: 22%; }
        .col-resp   { width: 10%; text-align: center; }
        .col-etat   { width: 7%; text-align: center; }
        .col-real   { width: 9%; text-align: center; }
        .col-obs    { width: 25%; }
        .td-chk { text-align: center; }
        .checkbox-box {
            display: inline-block;
            width: 13px;
            height: 13px;
            border: 1.5px solid #1E293B;
            border-radius: 3px;
        }
        .footnote {
            font-size: 8pt;
            color: #475569;
            margin-top: 4px;
        }
        .total-badge {
            display: inline-block; background:#0EA5E9; color:white; font-weight:700;
            padding:3px 12px; border-radius:12px; font-size:9pt; margin-left:8px;
        }
        .table-synthese th {
            background-color: #1406BE; color: #FFFFFF; font-weight: bold;
            text-align: center; font-size: 9pt;
        }
        .table-synthese td {
            font-size: 9.5pt;
        }
        .table-synthese .ligne-total td {
            font-weight: bold;
            background-color: #F1F5F9;
        }
        .synthese-cadre {
            border: 1.5px solid #1E3A8A;
            border-radius: 6px;
            padding: 12px 15px;
            margin-top: 10px;
            min-height: 260px;
        }
        .synthese-titre {
            font-size: 11pt;
            font-weight: bold;
            color: #1E3A8A;
            margin-bottom: 10px;
        }
    </style>
    </head>
    <body>
    """

    for ins in installations:
        d_ins = df_filtre[df_filtre["Installation"] == ins]
        html_content += f"""
        <div class="page">
            <div class="page-header">
                <img src="{logo_url}"/>
                <div class="page-header-text">Tunisie Profilés d'Aluminium — Direction Maintenance &amp; TN</div>
            </div>
            <div class="header-title" style="border-bottom: none; padding-bottom: 0;">Plan d'actions - Contrôle réglementaire</div>
            <div class="meta-info">
                <strong>Sous-pilote :</strong> {nom_par_installation.get(ins, nom_responsable)}<br>
                <strong>Installation :</strong> {ins}<br>
                <strong>Date d'édition :</strong> {date_str}
            </div>
            <div class="category-title">{ins} <span class="total-badge">{len(d_ins)} action(s)</span></div>
            <table>
                <thead>
                    <tr>
                        <th class="col-equip" rowspan="2">Equipement</th>
                        <th class="col-action" rowspan="2">Actions</th>
                        <th class="col-resp" rowspan="2">Responsable</th>
                        <th colspan="3">Etat de suivi</th>
                        <th class="col-real" rowspan="2">Réalisation<br>(O/N)</th>
                        <th class="col-obs" rowspan="2">Suivi d'avancement *</th>
                    </tr>
                    <tr>
                        <th class="col-etat">Immédiat</th>
                        <th class="col-etat">Sous-traitant*</th>
                        <th class="col-etat">Planifié*</th>
                    </tr>
                </thead>
                <tbody>
        """
        if not d_ins.empty:
            for equip, span, observation in _lignes_avec_rowspan(d_ins):
                html_content += "<tr>"
                if span is not None:
                    html_content += f'<td rowspan="{span}">{equip}</td>'
                html_content += f"""
                        <td>{observation}</td>
                        <td class="col-resp"></td>
                        <td class="td-chk"><span class="checkbox-box"></span></td>
                        <td class="td-chk"><span class="checkbox-box"></span></td>
                        <td class="td-chk"><span class="checkbox-box"></span></td>
                        <td></td>
                        <td></td>
                    </tr>
                """
        else:
            html_content += """
                <tr><td colspan="8" style="text-align:center;color:#94A3B8;font-style:italic;">Aucune action</td></tr>
            """
        html_content += """
                </tbody>
            </table>
            <div class="footnote">(*) Suivi d'avancement : Date de réalisation, Besoin PDR, Lancement DA, Nom de sous-traitant...</div>
        </div>
        """


    lignes_synthese_tableau = ""
    for ins in installations:
        nb_ins = len(df_filtre[df_filtre["Installation"] == ins])
        lignes_synthese_tableau += f"""
                    <tr>
                        <td>{ins}</td>
                        <td style="text-align:center;">{nb_ins}</td>
                        <td style="text-align:center;"></td>
                    </tr>
        """

    html_content += f"""
    <div class="page">
        <div class="page-header">
            <img src="{logo_url}"/>
            <div class="page-header-text">Tunisie Profilés d'Aluminium — Direction Maintenance &amp; TN</div>
        </div>
        <div class="header-title">Plan d'actions - Contrôle réglementaire</div>
        <div class="meta-info">
            <strong>Sous-pilote :</strong> {nom_responsable}<br>
            <strong>Total des actions :</strong> {total_general} action(s)<br>
            <strong>Date d'édition :</strong> {date_str}
        </div>

        <table class="table-synthese">
            <thead>
                <tr>
                    <th style="width:50%;">Installation</th>
                    <th style="width:25%;">Nombre d'actions</th>
                    <th style="width:25%;">Taux de réalisation</th>
                </tr>
            </thead>
            <tbody>
                {lignes_synthese_tableau}
                <tr class="ligne-total">
                    <td>Total</td>
                    <td style="text-align:center;">{total_general}</td>
                    <td style="text-align:center;"></td>
                </tr>
            </tbody>
        </table>

        <div class="synthese-cadre">
            <div class="synthese-titre">Synthèse / Observations et remarques</div>
        </div>
    </div>
    </body>
    </html>
    """

    return HTML(string=html_content).write_pdf()
