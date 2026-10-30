"""Petits composants UI réutilisables."""

import base64

from tpr.config import COULEUR_SITE


def badge_site(site: str) -> str:
    """Retourne un petit badge HTML coloré selon le site (MEG bleu / SGB vert)."""
    c = COULEUR_SITE.get(str(site).upper(), {"principale": "#64748B", "claire": "#F1F5F9", "fonce": "#334155"})
    return (f'<span style="background:{c["claire"]};color:{c["fonce"]};padding:2px 10px;'
            f'border-radius:999px;font-weight:700;font-size:12px;">{site}</span>')

def _charger_cartographie_b64():
    """Charge l'image de cartographie du taux de non-conformité en base64 (fichier local)."""
    try:
        with open("Cartographie.png", "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except Exception:
        return None
