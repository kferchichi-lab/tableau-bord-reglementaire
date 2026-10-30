"""Règles métier liées aux pilotes / responsables."""


from tpr.config import NATURE_PILOTE, SOUS_PILOTE_NOMS


def _codes_pour_pilote(pilote_choisi):
    """Retourne la liste des codes (T,S,E,D,O,R) dont le champ Pilote (potentiellement
    combiné avec '+') contient l'entité choisie."""
    codes = []
    for code, (_, pilote_str) in NATURE_PILOTE.items():
        entites = [e.strip() for e in pilote_str.split("+") if e.strip()]
        if pilote_choisi in entites:
            codes.append(code)
    return codes

def nom_pour_pilote_site(pilote, site=None):
    """Renvoie le nom du responsable à afficher pour un pilote donné, en tenant compte du site
    lorsque plusieurs responsables se partagent le même pilote (ex : Maintenance -> Saber pour MEG,
    Chafik pour SGB)."""
    if pilote == "Maintenance":
        site_norm = (site or "").strip().upper()
        if site_norm == "MEG":
            return "Saber BEN CHAABEN"
        if site_norm == "SGB":
            return "Chafik ABID"
        return "Maintenance (Saber BEN CHAABEN — MEG / Chafik ABID — SGB)"
    return SOUS_PILOTE_NOMS.get(pilote, pilote)
