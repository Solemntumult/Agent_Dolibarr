"""Adaptateur factures clients — lecture, création et agrégats via l'API REST Dolibarr.

Points d'accès (cahier des charges §4.3) : /invoices, /invoices/{id}.
Statuts Dolibarr (field fk_statut) : 0 brouillon, 1 validée/non payée, 2 réglée (payée),
3 annulée, 4 abandonnée.
"""
from datetime import datetime, timedelta, timezone

from adaptater.dolibarr.dolibarr_client_adaptater import DolibarrClientAdaptater, DolibarrClientError
from commons.instances.instances import logger
from data.schemas.invoice_schema import InvoiceSchema


def _days_late(due_date: str) -> int:
    try:
        due = datetime.strptime(str(due_date)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - due).days
    except (ValueError, TypeError):
        return 0


class InvoiceAdaptater:

    @staticmethod
    def list_invoices(status: str = "unpaid", limit: int = 100, client_id: int = None) -> list:
        """Liste les factures selon leur statut : 'unpaid' | 'paid' | 'draft' | 'all'."""
        try:
            params = {"limit": min(int(limit) or 100, 500), "sortfield": "t.datef", "sortorder": "DESC"}
            status_filter = {
                "unpaid": "(t.fk_statut:=:1)",
                "paid": "(t.fk_statut:=:2)",
                "draft": "(t.fk_statut:=:0)",
            }.get(status)
            filters = []
            if status_filter:
                filters.append(status_filter)
            if client_id:
                filters.append(f"(t.fk_soc:=:{int(client_id)})")
            if filters:
                params["sqlfilters"] = " AND ".join(filters)
            raw_list = DolibarrClientAdaptater.get("invoices", params=params)
            result = [InvoiceSchema(raw).to_dict() for raw in raw_list if isinstance(raw, dict)]

            # L'API factures ne renvoie pas le nom du client : on l'enrichit par requête
            # groupée sur les tiers (opérateur :in:).
            socids = {int(i["client_id"]) for i in result if i.get("client_id")}
            if socids:
                try:
                    batch = DolibarrClientAdaptater.get("thirdparties", params={
                        "limit": min(len(socids), 100),
                        "sortfield": "t.rowid",
                        "sqlfilters": f"(t.rowid:in:{','.join(str(s) for s in sorted(socids))})",
                    })
                    names = {int(t.get("id")): t.get("name") for t in batch if isinstance(t, dict)}
                    for i in result:
                        if not i.get("client_name") and i.get("client_id"):
                            i["client_name"] = names.get(int(i["client_id"])) or i["client_name"]
                except DolibarrClientError as e:
                    logger.warning(f"InvoiceAdaptater: enrichissement noms clients ignoré: {e}")
            return result
        except DolibarrClientError as e:
            logger.error(f"InvoiceAdaptater.list_invoices failed: {e}")
            raise e

    @staticmethod
    def get_unpaid(min_days_late: int = 0, client_id: int = None, limit: int = 25) -> dict:
        """Factures ouvertes (statut validée), avec jours de retard calculés côté backend."""
        try:
            invoices = InvoiceAdaptater.list_invoices(status="unpaid", limit=100, client_id=client_id)
            filtered = []
            total_due = 0.0
            for inv in invoices:
                days = _days_late(inv.get("due_date") or inv.get("date"))
                if days >= int(min_days_late or 0):
                    ttc = float(inv.get("total_ttc") or 0)
                    total_due += ttc
                    filtered.append({
                        "id": inv.get("id"),
                        "ref": inv.get("ref"),
                        "client_id": inv.get("client_id"),
                        "client_name": inv.get("client_name") or "Inconnu",
                        "total_ttc": ttc,
                        "total_ht": float(inv.get("total_ht") or 0),
                        "date": inv.get("date"),
                        "due_date": inv.get("due_date"),
                        "days_late": days,
                        "status": inv.get("status"),
                    })
            # Tri par retard décroissant
            filtered.sort(key=lambda x: x["days_late"], reverse=True)
            max_items = min(int(limit) or 25, 50)
            return {
                "total_count": len(filtered),
                "total_amount_ttc": round(total_due, 2),
                "returned_count": min(len(filtered), max_items),
                "factures": filtered[:max_items],
            }
        except DolibarrClientError as e:
            logger.error(f"InvoiceAdaptater.get_unpaid failed: {e}")
            raise e

    @staticmethod
    def get_by_id(invoice_id: int) -> dict:
        try:
            raw = DolibarrClientAdaptater.get(f"invoices/{int(invoice_id)}")
            return InvoiceSchema(raw).to_dict()
        except DolibarrClientError as e:
            logger.error(f"InvoiceAdaptater.get_by_id({invoice_id}) failed: {e}")
            raise e

    @staticmethod
    def get_by_ref(ref: str) -> dict:
        try:
            import re
            prov_match = re.search(r"PROV(\d+)", ref, re.IGNORECASE)
            if prov_match:
                try:
                    return InvoiceAdaptater.get_by_id(int(prov_match.group(1)))
                except DolibarrClientError:
                    pass

            clean_ref = ref.replace("(", "").replace(")", "").strip()
            raw_list = DolibarrClientAdaptater.get("invoices", params={"sqlfilters": f"(t.ref:=:'{clean_ref}')"})
            if raw_list and isinstance(raw_list, list) and len(raw_list) > 0 and isinstance(raw_list[0], dict):
                return InvoiceAdaptater.get_by_id(int(raw_list[0]["id"]))
            raise DolibarrClientError(f"Facture introuvable pour la référence {ref}.")
        except DolibarrClientError as e:
            logger.error(f"InvoiceAdaptater.get_by_ref({ref}) failed: {e}")
            raise e

    @staticmethod
    def get_by_id_or_ref(identifier) -> dict:
        """Récupère une facture soit par son ID numérique soit par sa référence."""
        import re
        str_val = str(identifier).strip()
        if str_val.isdigit():
            return InvoiceAdaptater.get_by_id(int(str_val))
        prov_match = re.search(r"PROV(\d+)", str_val, re.IGNORECASE)
        if prov_match:
            try:
                return InvoiceAdaptater.get_by_id(int(prov_match.group(1)))
            except Exception:
                pass
        return InvoiceAdaptater.get_by_ref(str_val)


    @staticmethod
    def get_avg_payment_delay() -> dict:
        """Délai moyen de paiement (jours entre date facture et date règlement) sur les factures payées du mois."""
        try:
            now = datetime.now(timezone.utc)
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            filters = [
                "(t.fk_statut:=:2)",
                f"(t.datef:>=:{start.strftime('%Y-%m-%d')})",
            ]
            params = {"limit": 200, "sqlfilters": " AND ".join(filters), "sortfield": "t.datef", "sortorder": "DESC"}
            rows = DolibarrClientAdaptater.get("invoices", params=params)
            if not isinstance(rows, list) or not rows:
                return {"avg_days": None, "count": 0}
            delays = []
            for inv in rows:
                try:
                    datef = datetime.strptime(str(inv.get("datef", ""))[:10], "%Y-%m-%d")
                    paye = inv.get("date_paye") or inv.get("paye")
                    if paye:
                        datep = datetime.strptime(str(paye)[:10], "%Y-%m-%d")
                        delays.append((datep - datef).days)
                except (ValueError, TypeError):
                    continue
            if not delays:
                return {"avg_days": None, "count": 0}
            return {"avg_days": round(sum(delays) / len(delays), 1), "count": len(delays)}
        except DolibarrClientError as e:
            logger.warning(f"InvoiceAdaptater.get_avg_payment_delay failed: {e}")
            return {"avg_days": None, "count": 0}

    @staticmethod
    def get_top_products(period: str = "mois", limit: int = 5) -> list:
        """Top produits par CA sur la période (basé sur les lignes de factures)."""
        try:
            now = datetime.now(timezone.utc)
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            filters = [
                "(t.fk_statut:in:1,2)",
                f"(t.datef:>=:{start.strftime('%Y-%m-%d')})",
            ]
            params = {"limit": 500, "sqlfilters": " AND ".join(filters)}
            rows = DolibarrClientAdaptater.get("invoices", params=params)
            if not isinstance(rows, list):
                return []
            product_sales = {}
            for inv in rows:
                inv_id = inv.get("id")
                if not inv_id:
                    continue
                try:
                    detail = DolibarrClientAdaptater.get(f"invoices/{int(inv_id)}")
                    lines = detail.get("lines") or []
                    for line in lines:
                        label = line.get("label") or line.get("desc") or "Service/Produit"
                        qty = float(line.get("qty") or 0)
                        up = float(line.get("subprice") or line.get("price") or 0)
                        total = qty * up
                        if label not in product_sales:
                            product_sales[label] = {"label": label, "total_ttc": 0, "qty": 0}
                        product_sales[label]["total_ttc"] += total
                        product_sales[label]["qty"] += qty
                except DolibarrClientError:
                    continue
            top = sorted(product_sales.values(), key=lambda x: x["total_ttc"], reverse=True)[:limit]
            return [{"label": t["label"], "total_ttc": round(t["total_ttc"], 2), "qty": round(t["qty"], 1)} for t in top]
        except Exception as e:
            logger.warning(f"InvoiceAdaptater.get_top_products failed: {e}")
            return []

    @staticmethod
    def create(data: dict) -> dict:
        """Crée une facture client. data: client_id, lines=[{label, qty, price, vat}], date, ref_client.

        Les factures sont créées à l'état brouillon (statut 0), puis validées par un
        utilisateur habilité (cahier des charges §3.2).
        """
        try:
            lines = data.get("lines") or []
            if not lines:
                raise DolibarrClientError("La facture doit contenir au moins une ligne.")
            payload = {
                "socid": int(data.get("client_id")),
                "date": data.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "status": 0,  # brouillon — validation ultérieure par un utilisateur habilité
                "ref_client": data.get("ref_client", ""),
                "note_public": data.get("note", ""),
                "lines": [
                    {
                        "label": line.get("label", ""),
                        "qty": float(line.get("qty", 1)),
                        "subprice": float(line.get("price", 0)),
                        "tva_tx": float(line.get("vat", 0)),
                    }
                    for line in lines
                ],
            }
            result = DolibarrClientAdaptater.post("invoices", payload)
            # L'API renvoie l'identifiant en entier brut (ou un dict {id: ...} sur certaines versions)
            invoice_id = result if isinstance(result, int) else (result.get("id") if isinstance(result, dict) else None)
            if not invoice_id:
                raise DolibarrClientError(f"Création de facture sans identifiant retourné: {result}")
            # La ref (ex. "(PROV11)" en brouillon) n'est pas renvoyée par le POST : on la récupère
            # via GET /invoices/{id} — nécessaire pour générer le PDF (§4.4).
            ref = result.get("ref") if isinstance(result, dict) else None
            if not ref:
                try:
                    detail = DolibarrClientAdaptater.get(f"invoices/{int(invoice_id)}")
                    ref = detail.get("ref") if isinstance(detail, dict) else None
                except DolibarrClientError as e:
                    logger.warning(f"InvoiceAdaptater: ref non récupérée après création: {e}")
            return {"id": invoice_id, "ref": ref}
        except DolibarrClientError as e:
            logger.error(f"InvoiceAdaptater.create failed: {e}")
            raise e

    @staticmethod
    def get_sales_statistics(period: str = "mois") -> dict:
        """Chiffre d'affaires facturé (factures validées + payées) sur une période donnée,
        comparé à la période précédente (cahier des charges §3.4 : analyse et reporting).
        period: 'mois' | 'trimestre' | 'semestre' | 'annee'
        """
        try:
            now = datetime.now(timezone.utc)
            if period == "trimestre":
                delta = 90
            elif period == "semestre":
                delta = 182
            elif period == "annee":
                delta = 365
            else:
                delta = 30  # mois

            start_current = now.replace(day=1)
            start_previous = (now - timedelta(days=delta)).replace(day=1)

            def aggregate(start, end):
                filters = [
                    "(t.fk_statut:in:1,2)",
                    f"(t.datef:>=:{start.strftime('%Y-%m-%d')})",
                    f"(t.datef:<:{end.strftime('%Y-%m-%d')})",
                ]
                params = {"limit": 500, "sqlfilters": " AND ".join(filters), "sortfield": "t.datef", "sortorder": "ASC"}
                rows = DolibarrClientAdaptater.get("invoices", params=params)
                if not isinstance(rows, list):
                    rows = []

                # Enrichit les noms clients (non fournis par l'API de liste)
                socids = {int(inv.get("socid")) for inv in rows if inv.get("socid")}
                names = {}
                if socids:
                    try:
                        batch = DolibarrClientAdaptater.get("thirdparties", params={
                            "limit": min(len(socids), 100),
                            "sortfield": "t.rowid",
                            "sqlfilters": f"(t.rowid:in:{','.join(str(s) for s in sorted(socids))})",
                        })
                        names = {int(t.get("id")): t.get("name") for t in batch if isinstance(t, dict)}
                    except DolibarrClientError:
                        pass

                total = 0.0
                clients = {}
                for inv in rows:
                    total += float(inv.get("total_ttc") or 0)
                    name = names.get(int(inv.get("socid"))) if inv.get("socid") else None
                    name = name or "Inconnu"
                    clients[name] = clients.get(name, 0) + float(inv.get("total_ttc") or 0)
                top = sorted(clients.items(), key=lambda kv: kv[1], reverse=True)[:5]
                return {"total_ttc": round(total, 2), "count": len(rows),
                        "top_clients": [{"name": k, "total_ttc": round(v, 2)} for k, v in top]}

            current = aggregate(start_current, now + timedelta(days=1))
            previous = aggregate(start_previous, start_current)
            evolution = None
            if previous["total_ttc"]:
                evolution = round((current["total_ttc"] - previous["total_ttc"]) / previous["total_ttc"] * 100, 1)

            return {
                "period": period,
                "current_period": {"label": f"{start_current.strftime('%Y-%m-%d')} -> {now.strftime('%Y-%m-%d')}", **current},
                "previous_period": {"label": f"{start_previous.strftime('%Y-%m-%d')} -> {start_current.strftime('%Y-%m-%d')}", **previous},
                "evolution_pct": evolution,
            }
        except DolibarrClientError as e:
            logger.error(f"InvoiceAdaptater.get_sales_statistics failed: {e}")
            raise e
