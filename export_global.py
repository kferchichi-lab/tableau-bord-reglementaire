"""Export Excel global de toutes les données."""

import io

import pandas as pd

from tpr.services.repository import lire_exigences, lire_points_reserve, lire_points_reserve_nature


def generer_export_global_excel(df_rapports: pd.DataFrame, df_planning: pd.DataFrame) -> bytes:
    """Génère un classeur Excel unique regroupant toutes les données de l'application
    (rapports, planification, exigences, points de réserve, suivi des actions), un onglet
    par jeu de données — utile pour un export/archivage complet en un clic."""
    from openpyxl.styles import Alignment, Font, PatternFill

    def _ecrire_feuille(writer, df, nom_feuille):
        df_export = df.copy() if df is not None else pd.DataFrame()
        if df_export.empty:
            df_export = pd.DataFrame({"Info": ["Aucune donnée disponible"]})
        df_export.to_excel(writer, index=False, sheet_name=nom_feuille[:31])
        ws = writer.sheets[nom_feuille[:31]]
        header_fill = PatternFill("solid", fgColor="1E3A8A")
        header_font = Font(color="FFFFFF", bold=True)
        for col_idx in range(1, len(df_export.columns) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
        for col_idx, col_name in enumerate(df_export.columns, start=1):
            largeur = min(max(len(str(col_name)), df_export[col_name].astype(str).str.len().max() if len(df_export) else 0) + 4, 45)
            ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = largeur

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        _ecrire_feuille(writer, df_rapports, "Rapports")
        _ecrire_feuille(writer, df_planning, "Planning")
        _ecrire_feuille(writer, lire_exigences(), "Exigences")
        _ecrire_feuille(writer, lire_points_reserve(), "PointsReserve")
        _ecrire_feuille(writer, lire_points_reserve_nature(), "PointsReserveNature")
    output.seek(0)
    return output.getvalue()
