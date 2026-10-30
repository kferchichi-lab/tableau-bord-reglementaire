"""Contexte d'exécution partagé entre les vues (profil, droits, jeux de données)."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class AppContext:
    """Photographie de la session pour un cycle de rendu Streamlit."""

    role: str                                  # "Visiteur" | "Responsable" | "Admin"
    password_correct: bool                     # True si le code Admin saisi est valide
    responsable_connecte: bool
    responsable_actif: str | None
    email_visiteur: str | None
    responsables: dict[str, dict]
    df_rapports: pd.DataFrame = field(repr=False)
    df_planning: pd.DataFrame = field(repr=False)

    # ---- Droits -------------------------------------------------------------------------
    @property
    def est_admin(self) -> bool:
        return self.role == "Admin" and self.password_correct

    @property
    def est_responsable(self) -> bool:
        return self.role == "Responsable" and self.responsable_connecte

    @property
    def est_visiteur(self) -> bool:
        return self.role == "Visiteur" and bool(self.email_visiteur)

    @property
    def acces_autorise(self) -> bool:
        return self.est_admin or self.est_responsable or self.est_visiteur

    @property
    def peut_suivre_actions(self) -> bool:
        return self.est_admin or self.est_responsable

    # ---- Identité -----------------------------------------------------------------------
    @property
    def email_actif(self) -> str | None:
        if self.est_admin:
            return "responsable@admin"
        if self.est_responsable and self.responsable_actif:
            return f"{self.responsable_actif.lower()}@responsable"
        if self.est_visiteur:
            return self.email_visiteur
        return None

    @property
    def libelle_utilisateur(self) -> str:
        """Libellé inscrit dans le journal d'audit."""
        if self.est_admin:
            return "Admin"
        if self.est_responsable:
            return f"Responsable : {self.responsable_actif or '?'}"
        if self.est_visiteur:
            return f"Visiteur : {self.email_visiteur}"
        return "inconnu"

    @property
    def val_total(self) -> int:
        return 0 if self.df_rapports.empty else len(self.df_rapports)
