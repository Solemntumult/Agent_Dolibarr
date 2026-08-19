from datetime import datetime, timezone


def _to_iso_date(value):
    """Convertit un timestamp Unix (int ou chaîne) en date ISO 'YYYY-MM-DD'."""
    if value in (None, ""):
        return None
    try:
        ts = int(value)
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
    except (ValueError, TypeError, OverflowError):
        s = str(value)
        return s[:10] if len(s) >= 10 else (s or None)


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class InvoiceSchema:
    """
    Représentation d'une ressource Dolibarr (non persistée localement).
    Sert de contrat entre l'adaptater Dolibarr et le reste de l'application.
    """

    def __init__(self, raw_data: dict):
        self.raw_data = raw_data or {}
        self.id = self.raw_data.get("id")
        self.ref = self.raw_data.get("ref")
        self.socid = self.raw_data.get("socid")
        # L'API de liste renvoie le nom du tiers dans le champ "name"
        self.socname = self.raw_data.get("socname") or self.raw_data.get("thirdparty_name") \
            or self.raw_data.get("name")
        self.date = _to_iso_date(self.raw_data.get("date"))
        self.date_lim_reglement = _to_iso_date(self.raw_data.get("date_lim_reglement"))
        self.total_ht = _to_float(self.raw_data.get("total_ht"))
        self.total_ttc = _to_float(self.raw_data.get("total_ttc"))
        self.status = self.raw_data.get("status")
        self.status_label = self.raw_data.get("statut") or self.raw_data.get("status_label")
        self.paid = self.raw_data.get("paye") or self.raw_data.get("paid")
        self.note = self.raw_data.get("note_public")
        self.lines = self.raw_data.get("lines") or []

    def to_dict(self):
        return {
            "id": self.id,
            "ref": self.ref,
            "client_id": self.socid,
            "client_name": self.socname,
            "date": self.date,
            "due_date": self.date_lim_reglement,
            "total_ht": self.total_ht,
            "total_ttc": self.total_ttc,
            "status": self.status,
            "status_label": self.status_label,
            "paid": self.paid,
            "note": self.note,
            "lines": self.lines,
        }
