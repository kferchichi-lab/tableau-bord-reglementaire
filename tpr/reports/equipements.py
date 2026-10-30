"""Rapport PDF des équipements soumis à exigence."""


import pandas as pd
from weasyprint import HTML

from tpr.config import LOGO_URL


def generer_rapport_equipements_pdf(df_exigences, site_filtre):
    installations = [
        "Installations électriques",
        "Equipements de levage",
        "Sécurité incendie",
        "Installations de gaz",
        "Appareil pression de gaz"
    ]
    
    df_eq = df_exigences[df_exigences.iloc[:, 0].astype(str).str.strip().str.lower() == "equipement"]
    
    df_eq = df_eq[df_eq.iloc[:, 1].astype(str).str.strip().str.upper() == site_filtre.upper()]
    logo_url = LOGO_URL
    
    html_content = """
    <html>
    <head>
    <style>
        @page {
            size: A4 portrait;
            margin: 20mm 15mm;
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
        .page {
            page-break-after: always;
        }
        .page:last-child {
            page-break-after: avoid;
        }
        .page-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 22px;
            padding-bottom: 10px;
            border-bottom: 1px solid #E2E8F0;
        }
        .page-header img {
            height: 30px;
        }
        .page-header-text {
            font-size: 9.5pt;
            color: #1E3A8A;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.4px;
        }
        .header-title {
            text-align: center;
            font-size: 17pt;
            font-weight: bold;
            color: #1E3A8A;
            margin-bottom: 22px;
            text-transform: uppercase;
            border-bottom: 2px solid #1E3A8A;
            padding-bottom: 14px;
            line-height: 1.35;
        }
        .meta-info {
            margin-bottom: 28px;
            background-color: #F8FAFC;
            border: 1px solid #E2E8F0;
            padding: 16px 18px;
            border-radius: 6px;
            line-height: 2.1;
            font-size: 11pt;
        }
        .meta-info .dots {
            color: #94A3B8;
            letter-spacing: 1px;
        }
        .category-title {
            font-size: 14pt;
            color: #0EA5E9;
            font-weight: bold;
            margin-top: 10px;
            margin-bottom: 15px;
            border-left: 4px solid #0EA5E9;
            padding-left: 8px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
        }
        th, td {
            border: 1px solid #CBD5E1;
            padding: 10px;
            text-align: left;
        }
        th {
            background-color: #1E3A8A;
            color: white;
            font-weight: bold;
            text-transform: uppercase;
            font-size: 9pt;
        }
        .col-sub { width: 60%; }
        .col-nb { width: 20%; text-align: center; }
        .col-chk { width: 20%; text-align: center; }
        .td-center { text-align: center; }

        .checkbox-box {
            display: inline-block;
            width: 14px;
            height: 14px;
            border: 1px solid #475569;
            border-radius: 2px;
            margin-top: 3px;
        }
        .signature-section {
            margin-top: 40px;
            width: 100%;
            border-top: 1px dashed #CBD5E1;
            padding-top: 15px;
        }
        .signature-title {
            font-weight: bold;
            text-decoration: underline;
            margin-bottom: 60px;
        }
        .empty-message {
            color: #94A3B8;
            font-size: 11pt;
        }
    </style>
    </head>
    <body>
    """

    def bloc_entete():
        return f"""
        <div class="page-header">
            <img src="{logo_url}"/>
            <span class="page-header-text">Tunisie Profilés d'Aluminium — Direction Maintenance &amp; TN</span>
        </div>
        <div class="header-title">Rapport d'inspection réglementaire — Site {site_filtre.upper()}</div>
        <div class="meta-info">
            <strong>Inspecteur technique :</strong> <span class="dots">…………………………………………………………………</span><br>
            <strong>Accompagnant :</strong> <span class="dots">……………………………………………………………………………</span><br>
            <strong>Date :</strong> <span class="dots">………………………………………………………………………………………</span>
        </div>
        """

    def bloc_signature():
        return """
        <div class="signature-section">
            <p class="signature-title">Signature :</p>
        </div>
        """

    if df_eq.empty:
        html_content += f"""
        <div class="page">
            {bloc_entete()}
            <p class="empty-message">Aucun équipement enregistré pour ce site.</p>
            {bloc_signature()}
        </div>
        """
    else:
        pages_generees = 0
        for installation in installations:
            df_ins = df_eq[df_eq.get("Installation", pd.Series(dtype=str)).astype(str).str.strip() == installation]
            if df_ins.empty:
                continue
            lignes_html = ""
            for _, row in df_ins.iterrows():
                sous_eq = row.get("Sous_equipement", "")
                try:
                    nombre = int(float(row.get("Nombre", 0) or 0))
                except (ValueError, TypeError):
                    nombre = row.get("Nombre", "")
                lignes_html += f"""
                <tr>
                    <td class="col-sub">{sous_eq}</td>
                    <td class="col-nb td-center">{nombre}</td>
                    <td class="col-chk td-center"><span class="checkbox-box"></span></td>
                </tr>"""

            html_content += f"""
            <div class="page">
                {bloc_entete()}
                <div class="category-title">{installation}</div>
                <table>
                    <thead>
                        <tr>
                            <th class="col-sub">Sous-équipements</th>
                            <th class="col-nb">Nombre</th>
                            <th class="col-chk">Case à cocher</th>
                        </tr>
                    </thead>
                    <tbody>{lignes_html}</tbody>
                </table>
                {bloc_signature()}
            </div>
            """
            pages_generees += 1

        if pages_generees == 0:
            html_content += f"""
            <div class="page">
                {bloc_entete()}
                <p class="empty-message">Aucun équipement enregistré pour ce site.</p>
                {bloc_signature()}
            </div>
            """

    html_content += """
    </body>
    </html>
    """

    return HTML(string=html_content).write_pdf()
