class ThirdpartySchema:
    """
    Représentation d'une ressource Dolibarr (non persistée localement).
    Sert de contrat entre l'adaptater Dolibarr et le reste de l'application.
    """

    def __init__(self, raw_data: dict):
        self.raw_data = raw_data or {}
        self.id = self.raw_data.get("id")
        self.name = self.raw_data.get("name") or self.raw_data.get("nom")
        self.email = self.raw_data.get("email")
        self.phone = self.raw_data.get("phone")
        self.address = self.raw_data.get("address")
        self.zip = self.raw_data.get("zip")
        self.town = self.raw_data.get("town") or self.raw_data.get("city")
        self.country = self.raw_data.get("country_code") or self.raw_data.get("country")
        self.client = self.raw_data.get("client")
        self.supplier = self.raw_data.get("fournisseur")
        self.code_client = self.raw_data.get("code_client")
        self.note = self.raw_data.get("note_public")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
            "zip": self.zip,
            "town": self.town,
            "country": self.country,
            "client": self.client,
            "supplier": self.supplier,
            "code_client": self.code_client,
            "note": self.note,
        }
