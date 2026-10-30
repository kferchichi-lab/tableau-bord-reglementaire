"""Rapport PDF des indicateurs (KPI)."""

import datetime
import math

import pandas as pd
from weasyprint import HTML

from tpr.config import COULEURS_INS


def generer_rapport_kpi_pdf(kpi_data, df_reserve, df_nature, carto_b64, logo_url):
    """
    Génère un rapport PDF premium regroupant tous les KPI de l'onglet KPI :
    Taux de réalisation 2026, Taux de respect de délai,
    cartographie du taux de non-conformité, et répartition par site et par pilote.
    """
    date_str = datetime.date.today().strftime('%d/%m/%Y')

    def barre(pct, couleur):
        pct = max(0, min(100, pct))
        return f"""<div style="background:#E2E8F0;border-radius:6px;height:14px;width:100%;overflow:hidden;">
            <div style="background:{couleur};height:100%;width:{pct}%;"></div></div>"""

    k1 = kpi_data["kpi1"]; k2 = kpi_data["kpi2"]

    # ---- Palettes de couleurs (cohérentes avec le tableau de bord Streamlit) ----
    COULEURS_SITE = {"SGB": "#1E3A8A", "MEG": "#0EA5E9"}
    COULEURS_NATURE = {
        "Technique": "#10B981", "Sécurité": "#F97316", "Organisation": "#84CC16",
        "Règlementation": "#EAB308", "Documentation": "#EC4899", "Energétique": "#64748B",
    }
    COULEURS_PILOTE = {
        "Maintenance": "#FACC15", "HSE": "#F97316", "BT": "#EF4444",
        "Chef service BT": "#3B82F6", "DMTN": "#A855F7", "RH": "#92400E", "DG": "#22C55E",
    }

    # ---- Helpers SVG (donut chart et bar chart horizontal, sans dépendance externe) ----
    def _polar(cx, cy, r, angle_deg):
        a = math.radians(angle_deg - 90)
        return (cx + r * math.cos(a), cy + r * math.sin(a))

    def _donut_path(cx, cy, r_out, r_in, a0, a1):
        p0o = _polar(cx, cy, r_out, a0)
        p1o = _polar(cx, cy, r_out, a1)
        p1i = _polar(cx, cy, r_in, a1)
        p0i = _polar(cx, cy, r_in, a0)
        large = 1 if (a1 - a0) > 180 else 0
        return (f"M {p0o[0]:.2f} {p0o[1]:.2f} "
                f"A {r_out:.2f} {r_out:.2f} 0 {large} 1 {p1o[0]:.2f} {p1o[1]:.2f} "
                f"L {p1i[0]:.2f} {p1i[1]:.2f} "
                f"A {r_in:.2f} {r_in:.2f} 0 {large} 0 {p0i[0]:.2f} {p0i[1]:.2f} Z")

    def _donut_chart(data, color_map, titre="", size=190, show_pct_labels=True):
        """data: dict {label: valeur numérique}. Retourne (svg, legend_html).
        Les pourcentages des petites parts sont affichés à l'extérieur (avec un
        trait de rappel) pour rester lisibles ; les grandes parts gardent le
        pourcentage centré à l'intérieur de l'anneau.
        show_pct_labels=False : n'affiche aucun pourcentage sur le graphique lui-même
        (utile quand la légende à côté les affiche déjà, pour éviter la redondance)."""
        data = {k: v for k, v in data.items() if v and v > 0}
        total = sum(data.values())
        if not data or not total:
            return "", ""
        pad = 34 if show_pct_labels else 14  # marge latérale pour les étiquettes extérieures
        cx, cy = size / 2 + pad, size / 2 + 18
        r_out, r_in = size * 0.40, size * 0.40 * 0.58
        angle = 0.0
        slices, labels = "", ""
        for label, val in data.items():
            pct = val / total * 100
            a1 = angle + pct / 100 * 360
            color = color_map.get(label, "#94A3B8")
            slices += f'<path d="{_donut_path(cx,cy,r_out,r_in,angle,a1)}" fill="{color}" stroke="#ffffff" stroke-width="1.5"/>'
            if show_pct_labels:
                mid = (angle + a1) / 2
                if pct >= 6:
                    # part assez grande : pourcentage centré, en blanc, à l'intérieur de l'anneau
                    lx, ly = _polar(cx, cy, (r_out + r_in) / 2, mid)
                    labels += (f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="11" font-weight="700" '
                               f'fill="#ffffff" text-anchor="middle" dominant-baseline="middle">{pct:.1f}%</text>')
                else:
                    # petite part : trait de rappel + pourcentage à l'extérieur, dans la couleur de la part
                    p0 = _polar(cx, cy, r_out, mid)
                    p1 = _polar(cx, cy, r_out + 12, mid)
                    anchor = "start" if p1[0] >= cx else "end"
                    tx = p1[0] + (4 if anchor == "start" else -4)
                    labels += (f'<line x1="{p0[0]:.1f}" y1="{p0[1]:.1f}" x2="{p1[0]:.1f}" y2="{p1[1]:.1f}" '
                               f'stroke="{color}" stroke-width="1.2"/>'
                               f'<text x="{tx:.1f}" y="{p1[1]:.1f}" font-size="9.5" font-weight="700" '
                               f'fill="{color}" text-anchor="{anchor}" dominant-baseline="middle">{pct:.1f}%</text>')
            angle = a1
        titre_svg = (f'<text x="{cx:.1f}" y="16" font-size="12.5" font-weight="700" fill="#0F172A" '
                     f'text-anchor="middle">{titre}</text>') if titre else ""
        w_total = size + 2 * pad
        svg = (f'<svg viewBox="0 0 {w_total} {size+22}" width="{w_total}" height="{size+22}" '
               f'xmlns="http://www.w3.org/2000/svg">{titre_svg}{slices}{labels}</svg>')
        legend = "".join(
            f'<div style="display:flex;align-items:center;margin-bottom:9px;">'
            f'<span style="width:11px;height:11px;min-width:11px;border-radius:3px;'
            f'background:{color_map.get(l,"#94A3B8")};display:inline-block;margin-right:8px;"></span>'
            f'<span style="font-size:10pt;color:#334155;white-space:nowrap;">{l}</span>'
            f'<span style="font-size:10pt;font-weight:800;color:#0F172A;white-space:nowrap;margin-left:14px;">{(v/total*100):.1f}%</span>'
            f'</div>'
            for l, v in data.items()
        )
        return svg, legend

    def _bar_list_html(data_pct, color_map):
        """data_pct: dict {label: pourcentage}, déjà trié décroissant.
        Présentation HTML (et non SVG) : libellé complet + barre + pourcentage en gras
        bien séparés, pour rester lisibles quel que soit le nombre de pilotes ou la
        longueur de leur nom (ex. « Chef service BT »)."""
        if not data_pct:
            return ""
        rows = ""
        for label, pct in data_pct.items():
            color = color_map.get(label, "#F59E0B")
            rows += f"""
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:11px;">
                <div style="flex:0 0 150px;font-size:9.5pt;font-weight:600;color:#334155;
                    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{label}</div>
                <div style="flex:1;background:#E2E8F0;border-radius:5px;height:16px;overflow:hidden;">
                    <div style="height:100%;width:{pct}%;background:{color};border-radius:5px;"></div>
                </div>
                <div style="flex:0 0 58px;text-align:right;font-size:10.5pt;font-weight:800;color:#0F172A;">{pct:.1f}%</div>
            </div>"""
        return rows

    # ---- Section 1 : Actions de contrôle — par site et par installation (source : PointsReserve) ----
    df_r = df_reserve.copy() if (df_reserve is not None and not df_reserve.empty) else pd.DataFrame()
    if not df_r.empty and "Nombre" in df_r.columns:
        df_r["Nombre"] = pd.to_numeric(df_r["Nombre"], errors="coerce").fillna(0)

    site_donut_svg, site_donut_legend = "", ""
    if not df_r.empty and "Site" in df_r.columns:
        site_donut_svg, site_donut_legend = _donut_chart(
            df_r.groupby("Site")["Nombre"].sum().to_dict(), COULEURS_SITE, "Répartition par site", size=210)

    def _ins_donut(site):
        if df_r.empty or "Installation" not in df_r.columns or "Site" not in df_r.columns:
            return "", ""
        d = df_r[df_r["Site"] == site].groupby("Installation")["Nombre"].sum().to_dict()
        return _donut_chart(d, COULEURS_INS, site, size=185, show_pct_labels=False)

    meg_ins_svg, meg_ins_legend = _ins_donut("MEG")
    sgb_ins_svg, sgb_ins_legend = _ins_donut("SGB")

    # ---- Section 2 : Répartition par site — Nature et Pilote (source : PointsReserveNature) ----
    df_n = df_nature.copy() if (df_nature is not None and not df_nature.empty) else pd.DataFrame()
    if not df_n.empty and "Nombre" in df_n.columns:
        df_n["Nombre"] = pd.to_numeric(df_n["Nombre"], errors="coerce").fillna(0)

    def _nature_donut(site):
        if df_n.empty or "Nature" not in df_n.columns or "Site" not in df_n.columns:
            return "", ""
        d = df_n[df_n["Site"] == site].groupby("Nature")["Nombre"].sum().to_dict()
        return _donut_chart(d, COULEURS_NATURE, f"{site} — % par nature", size=185, show_pct_labels=False)

    def _pilote_bar(site):
        if df_n.empty or "Pilote" not in df_n.columns or "Site" not in df_n.columns:
            return ""
        sub = df_n[df_n["Site"] == site]
        total = sub["Nombre"].sum()
        compte = {}
        for _, row in sub.iterrows():
            for e in str(row.get("Pilote", "")).split("+"):
                e = e.strip()
                if not e:
                    continue
                compte[e] = compte.get(e, 0) + row["Nombre"]
        if not compte or not total:
            return ""
        pct_dict = {k: round(v / total * 100, 1) for k, v in sorted(compte.items(), key=lambda x: -x[1])}
        return _bar_list_html(pct_dict, COULEURS_PILOTE)

    sgb_nature_svg, sgb_nature_legend = _nature_donut("SGB")
    meg_nature_svg, meg_nature_legend = _nature_donut("MEG")
    sgb_pilote_svg = _pilote_bar("SGB")
    meg_pilote_svg = _pilote_bar("MEG")


    carto_html = ""
    if carto_b64:
        carto_html = f"""
        <div class="page">
            <div class="category-title">Taux de non-conformité des sites</div>
            <p style="font-size:10pt;color:#475569;margin-bottom:12px;">
            Cartographie de synthèse du taux de non-conformité par site et par installation,
            établie lors de la campagne de contrôle réglementaire 2026.</p>
            <div style="text-align:center;">
                <img src="data:image/png;base64,{carto_b64}" style="max-width:100%;max-height:150mm;width:auto;
                    border-radius:8px;border:1px solid #E2E8F0;"/>
            </div>
        </div>"""

    html_content = f"""
    <html><head><style>
        @page {{ size: A4 landscape; margin: 15mm 18mm;
            @bottom-right {{ content: "Page " counter(page) " / " counter(pages);
                font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:9pt; color:#64748B; }} }}
        body {{ font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; color:#1E293B; margin:0; padding:0; font-size:10pt; }}
        .page {{ page-break-after: always; }}
        .page:last-child {{ page-break-after: avoid; }}
        .logo-box {{ text-align:center; margin-bottom:8px; }}
        .logo-box img {{ height:58px; }}
        .header-title {{ text-align:center; font-size:20pt; font-weight:bold; color:#1E3A8A; margin:6px 0 4px 0;
            text-transform:uppercase; letter-spacing:0.5px; }}
        .header-sub {{ text-align:center; font-size:11pt; color:#64748B; margin-bottom:22px; }}
        .meta-info {{ background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:14px 16px;
            font-size:10pt; line-height:1.7; margin-bottom:25px; }}
        .category-title {{ font-size:15pt; color:#0EA5E9; font-weight:bold; border-left:4px solid #0EA5E9;
            padding-left:10px; margin:10px 0 16px 0; }}
        .kpi-card {{ background:#F8FAFC; border:1px solid #E2E8F0; border-left:5px solid #1E3A8A; border-radius:8px;
            padding:18px; margin-bottom:18px; }}
        .kpi-title {{ font-size:13pt; font-weight:700; color:#0F172A; margin:0 0 6px 0; }}
        .kpi-desc {{ font-size:9.5pt; color:#475569; margin:0 0 12px 0; line-height:1.5; }}
        .kpi-value {{ font-size:26pt; font-weight:800; color:#1E3A8A; margin:0 0 10px 0; }}
        table {{ width:100%; border-collapse:collapse; margin-bottom:20px; }}
        th, td {{ border:1px solid #CBD5E1; padding:8px 10px; text-align:left; font-size:9pt; }}
        th {{ background:#1E3A8A; color:white; text-transform:uppercase; font-size:8.5pt; font-weight:bold; }}
    </style></head><body>

    <div class="page">
        <div class="logo-box"><img src="{logo_url}"/></div>
        <div class="header-title">Rapport KPI</div>
        <div class="header-title">Contrôle Réglementaire</div>
        <div class="header-sub">Tunisie Profilés d'Aluminium — Direction Maintenance &amp; TN</div>
        <div class="meta-info">
            <b>Date d'édition :</b> {date_str}<br>
            <b>Objet :</b> Synthèse des indicateurs de performance du suivi de conformité réglementaire —
            taux de réalisation, respect des délais, non-conformités et actions de contrôle.
        </div>

        <div class="category-title">Indicateurs de performance</div>

       





        <div style="display:flex;gap:20px;align-items:stretch;">
        <div class="kpi-card" style="border-left-color:#0EA5E9;flex:1;">
            <p class="kpi-title">1. Taux de réalisation 2026</p>
            <p class="kpi-desc">Proportion des visites réalisées dont l'écart entre la date réelle de contrôle
            et l'échéance théorique initiale du cycle n'excède pas 1 mois, par rapport au nombre total
            de visites réalisées.</p>
            <p class="kpi-value">{k1['taux']}%</p>
            {barre(k1['taux'], '#10B981')}
            <p style="font-size:9pt;color:#64748B;margin-top:8px;">{k1['realises']} réalisés / {k1['restants']} non réalisés
            — sur {k1['total']} visites planifiées</p>
        </div>

         <div class="kpi-card" style="flex:1;">
            <p class="kpi-title">2. Taux de respect de délai de visite</p>
            <p class="kpi-desc">Proportion des contrôles réglementaires dont l'échéance théorique est comprise
            entre le 01/01/2026 et le 31/12/2026, effectivement réalisés (date réelle de visite enregistrée)
            par rapport au nombre total de contrôles dus sur cette période.</p>
            <p class="kpi-value">{k2['taux']}%</p>
            {barre(k2['taux'], '#0EA5E9')}
            <p style="font-size:9pt;color:#64748B;margin-top:8px;">{k2['respectes']} respectés / {k2['respectes']} réalisés</p>
        </div>
        </div>

    </div>

    {carto_html}

    <div class="page">
        <div class="category-title">Répartition par site et par installation</div>
        <p style="font-size:10pt;color:#475569;margin-bottom:15px;">
        Répartition des actions de contrôle relevées, par site et par installation.</p>

        <div style="display:flex;justify-content:center;gap:30px;align-items:center;margin-bottom:10px;">
            <div>
                {site_donut_svg if site_donut_svg else "<p style='color:#94A3B8;font-size:9pt;'>Aucune donnée</p>"}
            </div>
            <div>{site_donut_legend}</div>
        </div>

        <p style="font-weight:700;font-size:12pt;color:#0F172A;text-align:center;margin:20px 0 12px 0;">
        Répartition par installation</p>

        <div style="display:flex;gap:40px;">
            <div style="flex:1;">
                <p style="font-weight:700;font-size:11pt;color:#0F172A;text-align:center;margin:0 0 10px 0;">MEG</p>
                <div style="display:flex;justify-content:center;align-items:center;gap:20px;">
                    <div style="flex:0 0 auto;">
                        {meg_ins_svg if meg_ins_svg else "<p style='color:#94A3B8;font-size:9pt;'>Aucune donnée MEG</p>"}
                    </div>
                    <div style="flex:0 0 180px;">{meg_ins_legend}</div>
                </div>
            </div>
            <div style="flex:1;">
                <p style="font-weight:700;font-size:11pt;color:#0F172A;text-align:center;margin:0 0 10px 0;">SGB</p>
                <div style="display:flex;justify-content:center;align-items:center;gap:20px;">
                    <div style="flex:0 0 auto;">
                        {sgb_ins_svg if sgb_ins_svg else "<p style='color:#94A3B8;font-size:9pt;'>Aucune donnée SGB</p>"}
                    </div>
                    <div style="flex:0 0 180px;">{sgb_ins_legend}</div>
                </div>
            </div>
        </div>
    </div>

    <div class="page">
        <div class="category-title">Répartition par site : Nature et Pilote</div>
        <p style="font-size:10pt;color:#475569;margin-bottom:15px;">
        Répartition des actions de contrôle relevées, par nature et par pilote, pour chaque site.</p>

        <p style="font-weight:700;font-size:12pt;color:#0F172A;margin:10px 0 12px 0;">SGB</p>
        <div style="display:flex;align-items:center;gap:25px;margin-bottom:25px;">
            <div style="flex:0 0 auto;">
                {sgb_nature_svg if sgb_nature_svg else "<p style='color:#94A3B8;font-size:9pt;'>Aucune donnée</p>"}
            </div>
            <div style="flex:0 0 150px;">{sgb_nature_legend}</div>
            <div style="flex:1;">
                <p style="font-size:9.5pt;font-weight:700;color:#64748B;margin:0 0 10px 0;text-transform:uppercase;">% par pilote</p>
                {sgb_pilote_svg if sgb_pilote_svg else "<p style='color:#94A3B8;font-size:9pt;'>Aucune donnée</p>"}
            </div>
        </div>

        <p style="font-weight:700;font-size:12pt;color:#0F172A;margin:10px 0 12px 0;">MEG</p>
        <div style="display:flex;align-items:center;gap:25px;">
            <div style="flex:0 0 auto;">
                {meg_nature_svg if meg_nature_svg else "<p style='color:#94A3B8;font-size:9pt;'>Aucune donnée</p>"}
            </div>
            <div style="flex:0 0 150px;">{meg_nature_legend}</div>
            <div style="flex:1;">
                <p style="font-size:9.5pt;font-weight:700;color:#64748B;margin:0 0 10px 0;text-transform:uppercase;">% par pilote</p>
                {meg_pilote_svg if meg_pilote_svg else "<p style='color:#94A3B8;font-size:9pt;'>Aucune donnée</p>"}
            </div>
        </div>
    </div>

    </body></html>
    """


    return HTML(string=html_content).write_pdf()
