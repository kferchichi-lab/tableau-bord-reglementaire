"""Conversion de liens Google Drive."""


def convertir_lien(url):
    try:
        if "drive.google.com" in str(url) and "/file/d/" in str(url):
            file_id = str(url).split('/file/d/')[1].split('/')[0]
            return f"https://drive.google.com/file/d/{file_id}/preview"
    except Exception: pass
    return url
