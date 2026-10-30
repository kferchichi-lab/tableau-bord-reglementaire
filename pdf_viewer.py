"""Aperçus PDF paginés dans l'interface."""

import hashlib

import fitz
import streamlit as st


def afficher_apercu_pdf(pdf_bytes, hauteur=800, cle=None):
    """Aperçu PDF paginé : ne rend (PyMuPDF, 130 DPI) que la page actuellement affichée,
    au lieu de toutes les pages d'un coup — beaucoup plus léger pour les rapports longs."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        nb_pages = len(doc)
        if cle is None:
            cle = hashlib.md5(pdf_bytes[:4096]).hexdigest()[:10]
        etat_key = f"page_apercu_{cle}"
        if etat_key not in st.session_state:
            st.session_state[etat_key] = 0
        st.session_state[etat_key] = max(0, min(st.session_state[etat_key], nb_pages - 1))

        if nb_pages > 1:
            c_prev, c_mid, c_next = st.columns([1, 3, 1])
            with c_prev:
                if st.button("⬅️ Précédente", key=f"prev_{cle}", use_container_width=True, disabled=(st.session_state[etat_key] <= 0)):
                    st.session_state[etat_key] -= 1
                    st.rerun()
            with c_mid:
                st.markdown(f"<p style='text-align:center;margin:0;color:#475569;font-weight:600;'>Page {st.session_state[etat_key] + 1} / {nb_pages}</p>", unsafe_allow_html=True)
            with c_next:
                if st.button("➡️ Suivante ", key=f"next_{cle}", use_container_width=True, disabled=(st.session_state[etat_key] >= nb_pages - 1)):
                    st.session_state[etat_key] += 1
                    st.rerun()

        page = doc[st.session_state[etat_key]]
        pix = page.get_pixmap(dpi=130)
        img_bytes = pix.tobytes("png")
        st.image(img_bytes, use_container_width=True)
        if nb_pages > 1:
            st.caption(f"Page {st.session_state[etat_key] + 1} / {nb_pages}")
        doc.close()
    except Exception as e:
        st.error(f"Impossible d'afficher l'aperçu du PDF : {e}")
        st.info("Vous pouvez tout de même télécharger le rapport ci-dessous.")

def afficher_apercu_pdf_grille(pdf_bytes, colonnes=2, largeur_colonne=380, cle=None, taille_lot=6):
    """Aperçu PDF en grille, chargé par lots (au lieu de rendre toutes les pages en une fois) :
    seules les `taille_lot` premières pages sont rendues, avec un bouton pour en charger davantage."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        nb_pages = len(doc)
        if cle is None:
            cle = hashlib.md5(pdf_bytes[:4096]).hexdigest()[:10]
        etat_key = f"nb_pages_affichees_{cle}"
        if etat_key not in st.session_state:
            st.session_state[etat_key] = min(taille_lot, nb_pages)

        nb_a_afficher = min(st.session_state[etat_key], nb_pages)
        cols = st.columns(colonnes)
        for i in range(nb_a_afficher):
            page = doc[i]
            pix = page.get_pixmap(dpi=110)
            img_bytes = pix.tobytes("png")
            col = cols[i % colonnes]
            with col:
                st.image(img_bytes, width=largeur_colonne)
                st.caption(f"Page {i + 1} / {nb_pages}")

        if nb_a_afficher < nb_pages:
            if st.button(f"⬇️ Afficher {min(taille_lot, nb_pages - nb_a_afficher)} page(s) de plus ({nb_a_afficher}/{nb_pages})", key=f"plus_{cle}", use_container_width=True):
                st.session_state[etat_key] = min(st.session_state[etat_key] + taille_lot, nb_pages)
                st.rerun()
        doc.close()
    except Exception as e:
        st.error(f"Impossible d'afficher l'aperçu du PDF : {e}")
        st.info("Vous pouvez tout de même télécharger le rapport ci-dessous.")
