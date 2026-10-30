"""Export PDF du calendrier de contrôle."""

import math

import pandas as pd
from weasyprint import HTML

from tpr.config import LOGO_URL
from tpr.domain.calendrier import calculer_taux_realisation


def generer_calendrier_controle_pdf(df_calendrier: pd.DataFrame, annee_reference: int) -> bytes:
    """Génère le PDF du calendrier de contrôle (paysage, une ligne par installation, Site fusionné)."""

    col_realisation = f"Réalisation {annee_reference}"
    logo_url = LOGO_URL

    lignes_html = ""
    for site in df_calendrier["Site"].unique():
        df_site = df_calendrier[df_calendrier["Site"] == site].reset_index(drop=True)
        for i, row in df_site.iterrows():
            pct_val = row[col_realisation]
            if pct_val == "A planifier" or pd.isna(pct_val):
                couleur = "#94A3B8"
            else:
                try:
                    pct_num = int(round(float(str(pct_val).replace("%", "").strip() or 0)))
                except (ValueError, TypeError):
                    pct_num = 0
                couleur = "#16A34A" if pct_num >= 80 else "#F97316" if pct_num >= 50 else "#EF4444"

            lignes_html += "<tr>"
            if i == 0:
                lignes_html += f"<td rowspan='{len(df_site)}' class='site-cell'>{site}</td>"
            lignes_html += f"""
                <td class="ci-cell">{row['CI']}</td>
                <td>{row['Installation']}</td>
                <td class="center">{row['Nbr visite/An']}</td>
                <td class="center">{row['Nbr jour']}</td>
                <td class="center">{row['Dates réalisées']}</td>
                <td class="center" style="color:{couleur};font-weight:700;">{pct_val}</td>
                <td class="center planifiee">{row['Dates planifiées']}</td>
            </tr>"""

    # ----- Bloc graphiques : taux de réalisation par site (barres horizontales) + taux global (anneau) -----
    taux = calculer_taux_realisation(df_calendrier)
    taux_meg, taux_sgb, taux_global = taux.get("MEG", 0.0), taux.get("SGB", 0.0), taux.get("Global", 0.0)

    couleurs_site = {"MEG": "#2563EB", "SGB": "#059669"}
    barres_html = ""
    for site_lbl, val in (("MEG", taux_meg), ("SGB", taux_sgb)):
        barres_html += f"""
        <div class="bar-row">
            <div class="bar-label">{site_lbl}</div>
            <div class="bar-track">
                <div class="bar-fill" style="width:{val}%; background:{couleurs_site[site_lbl]};"></div>
            </div>
            <div class="bar-value">{val}%</div>
        </div>"""

    # ----- Jauge semi-circulaire (même forme que la jauge Plotly affichée sur le site) -----
    g_cx, g_cy, g_ro, g_ri = 110, 108, 84, 58

    def _pt_jauge(frac, rayon):
        # frac : 0 = extrémité gauche, 1 = extrémité droite (arc passant par le haut)
        theta = math.pi * (1 - frac)
        return (g_cx + rayon * math.cos(theta), g_cy - rayon * math.sin(theta))

    def _arc_jauge(f0, f1):
        if f1 <= f0:
            return ""
        p0o, p1o = _pt_jauge(f0, g_ro), _pt_jauge(f1, g_ro)
        p1i, p0i = _pt_jauge(f1, g_ri), _pt_jauge(f0, g_ri)
        return (f"M {p0o[0]:.2f} {p0o[1]:.2f} "
                f"A {g_ro} {g_ro} 0 0 1 {p1o[0]:.2f} {p1o[1]:.2f} "
                f"L {p1i[0]:.2f} {p1i[1]:.2f} "
                f"A {g_ri} {g_ri} 0 0 0 {p0i[0]:.2f} {p0i[1]:.2f} Z")

    frac_global = max(0.0, min(1.0, taux_global / 100))
    jauge_fond = _arc_jauge(0.0, 1.0)
    jauge_valeur = _arc_jauge(0.0, frac_global)

    jauge_graduations = ""
    for graduation in (25, 50, 75):
        gx, gy = _pt_jauge(graduation / 100, g_ro + 9)
        jauge_graduations += (f'<text x="{gx:.1f}" y="{gy:.1f}" font-size="9" fill="#64748B" '
                              f'text-anchor="middle" dominant-baseline="middle">{graduation}</text>')
    jauge_graduations += (f'<text x="{g_cx - (g_ro + g_ri) / 2:.1f}" y="{g_cy + 12}" font-size="9" '
                          f'fill="#64748B" text-anchor="middle">0</text>'
                          f'<text x="{g_cx + (g_ro + g_ri) / 2:.1f}" y="{g_cy + 12}" font-size="9" '
                          f'fill="#64748B" text-anchor="middle">100</text>')

    taux_global_txt = f"{taux_global:g}%"

    html_content = f"""
    <html><head><style>
        @page {{ size: A4 landscape; margin: 10mm 12mm; }}
        * {{ box-sizing: border-box; }}
        body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color:#1E293B; font-size:9pt; }}
        .header {{ display:flex; align-items:center; gap:12px; margin-bottom:10px; border-bottom:2px solid #1E3A8A; padding-bottom:6px; }}
        .header img {{ height:28px; }}
        .header-texts {{ display:flex; flex-direction:column; }}
        .header-title {{ font-size:14pt; font-weight:800; color:#1E3A8A; text-transform:uppercase; }}
        .header-company {{ font-size:9pt; font-weight:700; color:#334155; }}
        .header-entite {{ font-size:8.3pt; font-weight:700; color:#0EA5E9; text-transform:uppercase; letter-spacing:0.3px; }}
        .subtitle {{ font-size:9pt; color:#64748B; margin:0 0 10px 0; }}
        table {{ width:100%; border-collapse:collapse; margin-bottom:14px; }}
        th, td {{ border:1px solid #CBD5E1; padding:8px 9px; text-align:left; }}
        th {{ background:#1E3A8A; color:white; font-size:8.5pt; text-transform:uppercase; }}
        .site-cell {{ font-weight:800; text-align:center; background:#F1F5F9; color:#1E3A8A; }}
        .ci-cell {{ font-weight:700; text-align:center; }}
        .center {{ text-align:center; }}
        .planifiee {{ font-weight:700; }}
        tr:nth-child(even) td:not(.site-cell) {{ background:#F8FAFC; }}

        .charts-title {{ font-size:11pt; font-weight:800; color:#1E3A8A; margin:10px 0 8px 0; text-align:center; }}
        .charts-wrap {{ display:flex; gap:16px; align-items:stretch; }}
        .charts-left {{ flex:1.5; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:12px 16px; }}
        .charts-left-title {{ font-size:9.5pt; font-weight:700; color:#0F172A; margin-bottom:10px; text-align:center; }}
        .bar-row {{ display:flex; align-items:center; margin-bottom:12px; }}
        .bar-label {{ width:55px; font-weight:700; color:#0F172A; }}
        .bar-track {{ flex:1; height:18px; background:#E2E8F0; border-radius:5px; overflow:hidden; }}
        .bar-fill {{ height:100%; border-radius:5px; }}
        .bar-value {{ width:50px; text-align:right; font-weight:800; color:#0F172A; }}
        .charts-right {{ flex:1; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:8px 16px; text-align:center; }}
        .charts-right-title {{ font-size:9.5pt; font-weight:700; color:#0F172A; margin-bottom:4px; }}
    </style></head>
    <body>
        <div class="header">
            <img src="{logo_url}"/>
            <div class="header-texts">
                <span class="header-title">Calendrier de contrôle réglementaire</span>
                <span class="header-company">Tunisie Profilés d'Aluminium</span>
                <span class="header-entite">DMTN - BT</span>
            </div>
        </div>
        <p class="subtitle">Année : {annee_reference}</p>
        <table>
            <thead><tr>
                <th>Sites</th><th>CI</th><th>Les installations</th><th>Nbr visite/An</th><th>Nbr jour</th>
                <th>Les visites réalisées</th><th>Réalisation {annee_reference}</th><th>Les visites planifiées</th>
            </tr></thead>
            <tbody>{lignes_html}</tbody>
        </table>

        <div class="charts-title">Taux de réalisation des contrôles — {annee_reference}</div>
        <div class="charts-wrap">
            <div class="charts-left">
                <div class="charts-left-title">Taux de réalisation par site</div>
                {barres_html}
            </div>
            <div class="charts-right">
                <div class="charts-right-title">Taux global {annee_reference}</div>
                <svg width="220" height="130" viewBox="0 0 220 130" xmlns="http://www.w3.org/2000/svg">
                    <path d="{jauge_fond}" fill="#E2E8F0"/>
                    <path d="{jauge_valeur}" fill="#1E3A8A"/>
                    {jauge_graduations}
                    <text x="{g_cx}" y="{g_cy - 12}" text-anchor="middle" font-size="30" font-weight="400" fill="#0F172A">{taux_global_txt}</text>
                </svg>
            </div>
        </div>
    </body></html>
    """
    return HTML(string=html_content).write_pdf()
