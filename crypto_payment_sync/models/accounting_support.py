import hashlib
import json
import base64
import csv
import io

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


TRANSACTION_STATUS = [
    ("draft", "Draft"),
    ("imported", "Imported"),
    ("normalized", "Normalized"),
    ("needs_review", "Needs Review"),
    ("exception", "Exception"),
    ("reviewed", "Reviewed"),
]


class CryptoImportBatch(models.Model):
    _name = "crypto.import.batch"
    _description = "External Crypto Import Batch"
    _order = "create_date desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, default=lambda self: _("External Import Batch"))
    source_provider = fields.Char(default="manual_import", required=True, tracking=True)
    provider_id = fields.Many2one("payment.provider", domain=[("code", "=", "crypto")])
    network_id = fields.Many2one("crypto.network")
    wallet_id = fields.Many2one("crypto.wallet")
    wallet_address_id = fields.Many2one("crypto.wallet.address")
    import_format = fields.Selection([("csv", "CSV"), ("json", "JSON")], default="csv", required=True)
    import_file = fields.Binary(attachment=True)
    import_filename = fields.Char()
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("imported", "Imported"),
            ("normalized", "Normalized"),
            ("needs_review", "Needs Review"),
            ("exception", "Exception"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    raw_transaction_ids = fields.One2many("crypto.raw.transaction", "import_batch_id")
    normalized_transaction_ids = fields.One2many("crypto.normalized.transaction", "import_batch_id")
    exception_ids = fields.One2many("crypto.ingestion.exception", "import_batch_id")
    raw_count = fields.Integer(compute="_compute_counts")
    normalized_count = fields.Integer(compute="_compute_counts")
    exception_count = fields.Integer(compute="_compute_counts")
    notes = fields.Text()

    @api.depends("raw_transaction_ids", "normalized_transaction_ids", "exception_ids")
    def _compute_counts(self):
        for record in self:
            record.raw_count = len(record.raw_transaction_ids)
            record.normalized_count = len(record.normalized_transaction_ids)
            record.exception_count = len(record.exception_ids.filtered(lambda item: item.status != "resolved"))

    def action_import_file(self):
        for record in self:
            rows = record._read_import_rows()
            if not rows:
                raise UserError(_("The import file did not contain any rows."))
            for index, payload in enumerate(rows, start=1):
                payload_json = json.dumps(payload, sort_keys=True, default=str)
                payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
                existing = self.env["crypto.raw.transaction"].search([
                    ("payload_hash", "=", payload_hash),
                    ("import_batch_id", "=", record.id),
                ], limit=1)
                if existing:
                    continue
                self.env["crypto.raw.transaction"].create({
                    "name": "%s / row %s" % (record.name, index),
                    "import_batch_id": record.id,
                    "source_provider": record.source_provider,
                    "provider_id": record.provider_id.id,
                    "network_id": record.network_id.id,
                    "wallet_id": record.wallet_id.id,
                    "wallet_address_id": record.wallet_address_id.id,
                    "source_row_number": index,
                    "raw_payload": payload_json,
                    "payload_hash": payload_hash,
                    "validation_status": "imported",
                })
            record.status = "imported"

    def action_normalize_raw_transactions(self):
        for record in self:
            for raw in record.raw_transaction_ids.filtered(lambda item: item.validation_status in ("imported", "exception")):
                raw.action_normalize()
            if record.exception_ids.filtered(lambda item: item.status != "resolved"):
                record.status = "needs_review"
            elif record.raw_transaction_ids:
                record.status = "normalized"

    def _read_import_rows(self):
        self.ensure_one()
        if not self.import_file:
            raise UserError(_("Upload a CSV or JSON import file first."))
        content = base64.b64decode(self.import_file)
        text = content.decode("utf-8-sig")
        if self.import_format == "json":
            data = json.loads(text)
            if isinstance(data, dict):
                data = data.get("items") or data.get("transactions") or [data]
            if not isinstance(data, list):
                raise UserError(_("JSON imports must contain an object or a list of objects."))
            return [item for item in data if isinstance(item, dict)]
        reader = csv.DictReader(io.StringIO(text))
        return [dict(row) for row in reader]


class CryptoRawTransaction(models.Model):
    _name = "crypto.raw.transaction"
    _description = "External Raw Crypto Transaction"
    _order = "create_date desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True)
    import_batch_id = fields.Many2one("crypto.import.batch", ondelete="cascade")
    source_provider = fields.Char(default="manual_import", required=True)
    provider_id = fields.Many2one("payment.provider", domain=[("code", "=", "crypto")])
    network_id = fields.Many2one("crypto.network")
    wallet_id = fields.Many2one("crypto.wallet")
    wallet_address_id = fields.Many2one("crypto.wallet.address")
    source_row_number = fields.Integer()
    raw_payload = fields.Text(required=True)
    payload_hash = fields.Char(index=True)
    source_transaction_id = fields.Char(index=True)
    transaction_hash = fields.Char(index=True)
    validation_status = fields.Selection(
        [
            ("draft", "Draft"),
            ("imported", "Imported"),
            ("normalized", "Normalized"),
            ("exception", "Exception"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    error_message = fields.Text()
    normalized_transaction_id = fields.Many2one("crypto.normalized.transaction", readonly=True)
    exception_ids = fields.One2many("crypto.ingestion.exception", "raw_transaction_id")

    _sql_constraints = [
        (
            "crypto_raw_transaction_payload_hash_batch_uniq",
            "unique(import_batch_id, payload_hash)",
            "This raw transaction payload is already imported in the same batch.",
        ),
    ]

    def action_normalize(self):
        for record in self:
            try:
                values = record._normalized_values()
                normalized = self.env["crypto.normalized.transaction"].create_from_normalized_dict(values)
                record.write({
                    "normalized_transaction_id": normalized.id,
                    "transaction_hash": normalized.transaction_hash,
                    "source_transaction_id": normalized.source_transaction_id,
                    "validation_status": "normalized",
                    "error_message": False,
                })
            except Exception as exc:
                message = str(exc)
                record.write({"validation_status": "exception", "error_message": message})
                self.env["crypto.ingestion.exception"].create({
                    "name": _("Raw transaction normalization failed"),
                    "import_batch_id": record.import_batch_id.id,
                    "raw_transaction_id": record.id,
                    "severity": "error",
                    "exception_type": "normalization",
                    "message": message,
                    "suggested_action": _("Review the raw payload and required mapping fields."),
                })

    def _normalized_values(self):
        self.ensure_one()
        payload = json.loads(self.raw_payload or "{}")
        tx_hash = self._first_payload_value(payload, ["transaction_hash", "tx_hash", "hash", "transactionHash"])
        source_tx_id = self._first_payload_value(payload, ["source_transaction_id", "external_reference", "id", "transactionId"])
        timestamp = self._first_payload_value(payload, ["timestamp", "datetime", "date", "minedInBlockTimestamp"])
        asset_symbol = self._first_payload_value(payload, ["asset_symbol", "symbol", "asset", "unit"]) or ""
        quantity = self._float_payload_value(payload, ["quantity", "amount", "value"])
        fee_quantity = self._float_payload_value(payload, ["fee_quantity", "fee", "feeAmount"])
        tx_type = self._first_payload_value(payload, ["transaction_type", "type"]) or "unknown"
        allowed_types = dict(self.env["crypto.normalized.transaction"]._fields["transaction_type"].selection)
        if tx_type not in allowed_types:
            tx_type = "unknown"

        if not timestamp:
            raise ValidationError(_("Raw transaction is missing a timestamp."))
        if not asset_symbol:
            raise ValidationError(_("Raw transaction is missing an asset symbol."))
        if quantity is None and tx_type not in ("fee", "remeasurement_event"):
            raise ValidationError(_("Raw transaction is missing a quantity or amount."))

        asset = self.env["res.currency"].search([("name", "=", asset_symbol.upper()), ("type", "=", "crypto")], limit=1)
        raw_payload = self.raw_payload or "{}"
        values = {
            "import_batch_id": self.import_batch_id.id,
            "raw_transaction_id": self.id,
            "source_provider": self.source_provider,
            "provider_id": self.provider_id.id,
            "network_id": self.network_id.id,
            "wallet_id": self.wallet_id.id,
            "wallet_address_id": self.wallet_address_id.id,
            "source_transaction_id": source_tx_id,
            "transaction_hash": tx_hash,
            "timestamp": timestamp,
            "asset_id": asset.id,
            "asset_symbol": asset_symbol.upper(),
            "asset_contract_address": self._first_payload_value(payload, ["asset_contract_address", "contractAddress"]),
            "chain_reference": self._first_payload_value(payload, ["chain_reference", "blockchain", "network"]),
            "quantity": quantity or 0.0,
            "fee_quantity": fee_quantity or 0.0,
            "fee_asset_symbol": self._first_payload_value(payload, ["fee_asset_symbol", "feeAsset", "feeUnit"]),
            "transaction_type": tx_type,
            "counterparty": self._first_payload_value(payload, ["counterparty", "from", "to", "address"]),
            "raw_payload": raw_payload,
            "processing_status": "normalized" if tx_type != "unknown" else "needs_review",
        }
        return values

    def _first_payload_value(self, payload, keys):
        for key in keys:
            value = payload.get(key)
            if value not in (None, ""):
                return value
        return False

    def _float_payload_value(self, payload, keys):
        value = self._first_payload_value(payload, keys)
        if value in (False, None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


class CryptoIngestionException(models.Model):
    _name = "crypto.ingestion.exception"
    _description = "Crypto Ingestion Exception"
    _order = "create_date desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True)
    import_batch_id = fields.Many2one("crypto.import.batch", ondelete="cascade")
    raw_transaction_id = fields.Many2one("crypto.raw.transaction", ondelete="cascade")
    normalized_transaction_id = fields.Many2one("crypto.normalized.transaction", ondelete="set null")
    severity = fields.Selection([("info", "Info"), ("warning", "Warning"), ("error", "Error")], default="warning")
    exception_type = fields.Char(required=True)
    message = fields.Text(required=True)
    suggested_action = fields.Text()
    assigned_user_id = fields.Many2one("res.users")
    status = fields.Selection(
        [
            ("open", "Open"),
            ("in_review", "In Review"),
            ("resolved", "Resolved"),
            ("ignored", "Ignored"),
        ],
        default="open",
        required=True,
        tracking=True,
    )
    resolution_notes = fields.Text()
    resolved_by = fields.Many2one("res.users")
    resolved_date = fields.Datetime()

    def action_mark_in_review(self):
        self.write({"status": "in_review"})

    def action_resolve(self):
        self.write({
            "status": "resolved",
            "resolved_by": self.env.user.id,
            "resolved_date": fields.Datetime.now(),
        })


class CryptoNormalizedTransaction(models.Model):
    _name = "crypto.normalized.transaction"
    _description = "External Crypto Normalization Support"
    _order = "timestamp desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    source_provider = fields.Char(default="cryptoapis", required=True)
    import_batch_id = fields.Many2one("crypto.import.batch", string="Import Batch", ondelete="set null")
    raw_transaction_id = fields.Many2one("crypto.raw.transaction", string="Raw Transaction", ondelete="set null")
    provider_id = fields.Many2one(
        "payment.provider",
        string="Odoo Payment Provider",
        domain=[("code", "=", "crypto")],
    )
    payment_transaction_id = fields.Many2one("payment.transaction", string="Odoo Payment Transaction", index=True)
    account_payment_id = fields.Many2one("account.payment", string="Odoo Account Payment", index=True)
    account_move_line_ids = fields.One2many(
        "account.move.line",
        "crypto_normalized_transaction_id",
        string="Odoo Journal Lines",
    )
    blockchain_id = fields.Many2one("crypto.blockchain", string="Blockchain")
    network_id = fields.Many2one("crypto.network", string="Network")
    wallet_id = fields.Many2one("crypto.wallet", string="Wallet / Source Account")
    wallet_address_id = fields.Many2one("crypto.wallet.address", string="Wallet Address")
    source_transaction_id = fields.Char(index=True)
    transaction_hash = fields.Char(index=True)
    timestamp = fields.Datetime(index=True)
    asset_id = fields.Many2one("res.currency", string="Asset", domain=[("type", "=", "crypto")])
    asset_symbol = fields.Char(required=True)
    asset_contract_address = fields.Char()
    chain_reference = fields.Char(help="Provider-specific chain or network reference.")
    quantity = fields.Float(digits=(20, 8))
    fee_quantity = fields.Float(digits=(20, 8))
    fee_asset_symbol = fields.Char()
    transaction_type = fields.Selection(
        [
            ("acquisition", "Acquisition"),
            ("disposal", "Disposal"),
            ("transfer", "Transfer"),
            ("payment_receipt", "Payment Receipt"),
            ("payment_settlement", "Payment Settlement"),
            ("fee", "Fee"),
            ("remeasurement_event", "Remeasurement Event"),
            ("unknown", "Unknown / Needs Review"),
        ],
        default="unknown",
        required=True,
    )
    counterparty = fields.Char()
    raw_payload = fields.Text()
    payload_hash = fields.Char(compute="_compute_payload_hash", store=True, index=True)
    duplicate_key = fields.Char(compute="_compute_duplicate_key", store=True, index=True)
    processing_status = fields.Selection(TRANSACTION_STATUS, default="draft", required=True)
    exception_reason = fields.Text()
    reviewer_notes = fields.Text()
    fair_value_measurement_ids = fields.One2many(
        "crypto.fair.value.measurement",
        "normalized_transaction_id",
        string="Fair-Value Measurements",
    )
    journal_preparation_ids = fields.One2many(
        "crypto.journal.entry.preparation",
        "normalized_transaction_id",
        string="Journal-Entry Preparations",
    )

    _sql_constraints = [
        (
            "crypto_normalized_transaction_duplicate_key_uniq",
            "unique(duplicate_key)",
            "A normalized transaction with the same source/network/account duplicate key already exists.",
        ),
    ]

    @api.depends("transaction_hash", "source_transaction_id", "asset_symbol", "timestamp")
    def _compute_name(self):
        for record in self:
            reference = record.transaction_hash or record.source_transaction_id or _("Unreferenced")
            record.name = f"{record.asset_symbol or 'Asset'} - {reference}"

    @api.depends("raw_payload")
    def _compute_payload_hash(self):
        for record in self:
            payload = record.raw_payload or ""
            record.payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest() if payload else False

    @api.depends(
        "source_provider",
        "network_id",
        "wallet_id",
        "wallet_address_id",
        "transaction_hash",
        "source_transaction_id",
        "payload_hash",
    )
    def _compute_duplicate_key(self):
        for record in self:
            if not (record.transaction_hash or record.source_transaction_id or record.payload_hash):
                record.duplicate_key = False
                continue
            network = record.network_id.id or "none"
            account = record.wallet_address_id.id or record.wallet_id.id or "none"
            tx_ref = record.transaction_hash or record.source_transaction_id or record.payload_hash or "none"
            raw = f"{record.source_provider or 'unknown'}|{network}|{account}|{tx_ref}"
            record.duplicate_key = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @api.constrains("processing_status", "exception_reason")
    def _check_exception_reason(self):
        for record in self:
            if record.processing_status == "exception" and not record.exception_reason:
                raise ValidationError(_("Exception transactions require an exception reason."))

    def action_mark_reviewed(self):
        self.write({"processing_status": "reviewed"})

    def action_mark_needs_review(self):
        self.write({"processing_status": "needs_review"})

    @api.model
    def create_from_normalized_dict(self, values):
        """Create or return a normalized transaction using the duplicate key."""
        duplicate_key = values.get("duplicate_key")
        if duplicate_key:
            existing = self.search([("duplicate_key", "=", duplicate_key)], limit=1)
            if existing:
                return existing
        existing = self._find_existing_normalized_transaction(values)
        if existing:
            return existing
        raw_payload = values.get("raw_payload")
        if isinstance(raw_payload, (dict, list)):
            values["raw_payload"] = json.dumps(raw_payload, sort_keys=True)
        for field_name in (
            "provider_id",
            "network_id",
            "wallet_id",
            "wallet_address_id",
            "asset_id",
            "import_batch_id",
            "raw_transaction_id",
            "payment_transaction_id",
            "account_payment_id",
        ):
            if not values.get(field_name):
                values.pop(field_name, None)
        timestamp = values.get("timestamp")
        if isinstance(timestamp, str):
            values["timestamp"] = timestamp.replace("T", " ").replace("+00:00", "").replace("Z", "")
        return self.create(values)

    @api.model
    def _find_existing_normalized_transaction(self, values):
        tx_ref_field = False
        tx_ref_value = False
        for field_name in ("transaction_hash", "source_transaction_id"):
            if values.get(field_name):
                tx_ref_field = field_name
                tx_ref_value = values[field_name]
                break
        if not tx_ref_field:
            return self.browse()
        domain = [
            ("source_provider", "=", values.get("source_provider") or "unknown"),
            (tx_ref_field, "=", tx_ref_value),
        ]
        for field_name in ("network_id", "wallet_id", "wallet_address_id"):
            if values.get(field_name):
                domain.append((field_name, "=", values[field_name]))
        return self.search(domain, limit=1)

    @api.model
    def action_sync_from_odoo_crypto_activity(self):
        transactions = self.env["payment.transaction"].search([
            ("provider_id.code", "=", "crypto"),
            "|",
            ("crypto_address", "!=", False),
            ("crypto_tx_hash", "!=", False),
        ])
        created_or_matched = self.browse()
        for tx in transactions:
            created_or_matched |= self._sync_payment_transaction(tx)

        payments = self.env["account.payment"].search([
            "|",
            ("crypto_transaction_id", "!=", False),
            ("journal_id.is_crypto", "=", True),
        ])
        for payment in payments:
            if hasattr(payment, "_apply_crypto_traceability_to_move"):
                payment._apply_crypto_traceability_to_move()
            if payment.payment_transaction_id:
                created_or_matched |= self._sync_payment_transaction(payment.payment_transaction_id, payment=payment)
        return {
            "type": "ir.actions.act_window",
            "name": _("External Normalization Support"),
            "res_model": "crypto.normalized.transaction",
            "view_mode": "list,form",
            "domain": [("id", "in", created_or_matched.ids)],
        }

    @api.model
    def _sync_payment_transaction(self, tx, payment=False):
        wallet_address = tx.crypto_address
        wallet = wallet_address.wallet_id if wallet_address else self.env["crypto.wallet"]
        asset = tx.currency_id if tx.currency_id and tx.currency_id.type == "crypto" else wallet.currency_id
        raw_payload = {
            "source": "odoo.payment.transaction",
            "payment_transaction_id": tx.id,
            "reference": tx.reference,
            "state": tx.state,
            "amount": tx.amount,
            "currency": tx.currency_id.name,
            "crypto_amount": tx.crypto_amount_eth,
            "crypto_tx_hash": tx.crypto_tx_hash,
            "wallet_address": wallet_address.name if wallet_address else False,
            "account_payment_id": payment.id if payment else False,
        }
        quantity = tx.crypto_amount_eth or (tx.amount if tx.currency_id and tx.currency_id.type == "crypto" else 0.0)
        values = {
            "source_provider": "odoo_payment",
            "provider_id": tx.provider_id.id,
            "payment_transaction_id": tx.id,
            "account_payment_id": payment.id if payment else False,
            "network_id": wallet.network_id.id if wallet else False,
            "wallet_id": wallet.id if wallet else False,
            "wallet_address_id": wallet_address.id if wallet_address else False,
            "source_transaction_id": tx.reference,
            "transaction_hash": tx.crypto_tx_hash,
            "timestamp": tx.create_date,
            "asset_id": asset.id if asset else False,
            "asset_symbol": asset.name if asset else (tx.currency_id.name or "UNKNOWN"),
            "quantity": quantity,
            "transaction_type": "payment_receipt",
            "counterparty": tx.partner_id.display_name,
            "raw_payload": json.dumps(raw_payload, sort_keys=True, default=str),
            "processing_status": "normalized" if tx.crypto_tx_hash else "needs_review",
            "reviewer_notes": _("Generated from Odoo payment transaction for professional review support."),
        }
        normalized = self.create_from_normalized_dict(values)
        lines = self.env["account.move.line"].search([
            "|",
            ("crypto_payment_transaction_id", "=", tx.id),
            ("crypto_transaction_hash", "=", tx.crypto_tx_hash or "__none__"),
        ])
        if lines:
            lines.write({"crypto_normalized_transaction_id": normalized.id})
        return normalized


class CryptoFairValueMeasurement(models.Model):
    _name = "crypto.fair.value.measurement"
    _description = "Fair-Value Measurement Support"
    _order = "measurement_datetime desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    normalized_transaction_id = fields.Many2one(
        "crypto.normalized.transaction",
        string="Normalized Transaction",
        ondelete="set null",
    )
    asset_id = fields.Many2one("res.currency", string="Asset", domain=[("type", "=", "crypto")])
    asset_symbol = fields.Char(required=True)
    measurement_datetime = fields.Datetime(required=True, default=fields.Datetime.now)
    pricing_source = fields.Char(required=True, default="Manual / fixture")
    source_api_provider = fields.Char(default="cryptoapis")
    exchange_rate = fields.Float(digits=(20, 8))
    reporting_currency_id = fields.Many2one(
        "res.currency",
        string="Reporting Currency",
        default=lambda self: self.env.company.currency_id,
    )
    quantity = fields.Float(digits=(20, 8))
    fair_value_amount = fields.Float(compute="_compute_amounts", store=True)
    carrying_amount = fields.Float(string="Carrying Amount Support")
    unrealized_gain_loss_amount = fields.Float(compute="_compute_amounts", store=True)
    valuation_status = fields.Selection(
        [
            ("draft", "Draft"),
            ("captured", "Captured"),
            ("needs_review", "Needs Review"),
            ("reviewed", "Reviewed"),
            ("exception", "Exception"),
        ],
        default="draft",
        required=True,
    )
    principal_market_notes = fields.Text(
        help="Review field for principal-market or valuation-policy assumptions."
    )
    reviewer_notes = fields.Text()
    raw_payload = fields.Text()
    payload_hash = fields.Char(compute="_compute_payload_hash", store=True)

    @api.depends("asset_symbol", "measurement_datetime")
    def _compute_name(self):
        for record in self:
            record.name = f"{record.asset_symbol or 'Asset'} fair value - {record.measurement_datetime or ''}"

    @api.depends("quantity", "exchange_rate", "carrying_amount")
    def _compute_amounts(self):
        for record in self:
            record.fair_value_amount = (record.quantity or 0.0) * (record.exchange_rate or 0.0)
            record.unrealized_gain_loss_amount = record.fair_value_amount - (record.carrying_amount or 0.0)

    @api.depends("raw_payload")
    def _compute_payload_hash(self):
        for record in self:
            payload = record.raw_payload or ""
            record.payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest() if payload else False

    def action_mark_reviewed(self):
        self.write({"valuation_status": "reviewed"})


class CryptoJournalEntryPreparation(models.Model):
    _name = "crypto.journal.entry.preparation"
    _description = "Journal-Entry Preparation Support"
    _order = "entry_date desc, id desc"

    name = fields.Char(required=True)
    entry_date = fields.Date(required=True, default=fields.Date.context_today)
    normalized_transaction_id = fields.Many2one("crypto.normalized.transaction", ondelete="set null")
    fair_value_measurement_id = fields.Many2one("crypto.fair.value.measurement", ondelete="set null")
    journal_id = fields.Many2one("account.journal")
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("prepared", "Prepared"),
            ("needs_review", "Needs Review"),
            ("approved_for_posting", "Approved for Posting"),
            ("posted", "Posted"),
            ("exception", "Exception"),
        ],
        default="draft",
        required=True,
    )
    line_ids = fields.One2many(
        "crypto.journal.entry.preparation.line",
        "preparation_id",
        string="Preview Lines",
    )
    total_debit = fields.Float(compute="_compute_totals", store=True)
    total_credit = fields.Float(compute="_compute_totals", store=True)
    is_balanced = fields.Boolean(compute="_compute_totals", store=True)
    account_move_id = fields.Many2one("account.move", string="Draft Journal Entry", readonly=True)
    reviewer_notes = fields.Text()
    exception_reason = fields.Text()

    @api.depends("line_ids.debit", "line_ids.credit")
    def _compute_totals(self):
        for record in self:
            record.total_debit = sum(record.line_ids.mapped("debit"))
            record.total_credit = sum(record.line_ids.mapped("credit"))
            record.is_balanced = abs(record.total_debit - record.total_credit) < 0.00001

    def action_mark_prepared(self):
        for record in self:
            if not record.is_balanced:
                record.write({"status": "needs_review", "exception_reason": _("Preview lines are not balanced.")})
            else:
                record.write({"status": "prepared"})

    def action_mark_reviewed(self):
        self.write({"status": "approved_for_posting"})

    def action_create_draft_move(self):
        for record in self:
            if not record.is_balanced:
                raise UserError(_("Draft journal entries require balanced preview lines."))
            if not record.journal_id:
                raise UserError(_("Select a journal before creating a draft journal entry."))
            lines = []
            for line in record.line_ids:
                lines.append(
                    (
                        0,
                        0,
                        {
                            "name": line.name or record.name,
                            "account_id": line.account_id.id,
                            "debit": line.debit,
                            "credit": line.credit,
                        },
                    )
                )
            move = self.env["account.move"].create(
                {
                    "journal_id": record.journal_id.id,
                    "date": record.entry_date,
                    "ref": record.name,
                    "line_ids": lines,
                }
            )
            record.write({"account_move_id": move.id, "status": "approved_for_posting"})


class CryptoJournalEntryPreparationLine(models.Model):
    _name = "crypto.journal.entry.preparation.line"
    _description = "Journal-Entry Preparation Line"

    preparation_id = fields.Many2one(
        "crypto.journal.entry.preparation",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(required=True)
    account_id = fields.Many2one("account.account", required=True)
    debit = fields.Float()
    credit = fields.Float()
    source_note = fields.Char()

    @api.constrains("debit", "credit")
    def _check_debit_credit(self):
        for record in self:
            if record.debit and record.credit:
                raise ValidationError(_("A preview line cannot have both debit and credit amounts."))


class CryptoReconciliationStatus(models.Model):
    _name = "crypto.reconciliation.status"
    _description = "Digital-Asset Reconciliation Status"
    _order = "period_end desc, id desc"

    name = fields.Char(required=True)
    period_start = fields.Date(required=True)
    period_end = fields.Date(required=True)
    normalized_transaction_id = fields.Many2one("crypto.normalized.transaction")
    fair_value_measurement_id = fields.Many2one("crypto.fair.value.measurement")
    journal_preparation_id = fields.Many2one("crypto.journal.entry.preparation")
    tax_1099da_id = fields.Many2one("crypto.tax.readiness.1099da")
    form8949_id = fields.Many2one("crypto.form8949.reconciliation")
    status = fields.Selection(
        [
            ("matched", "Matched"),
            ("pending", "Pending Review"),
            ("exception", "Exception"),
            ("excluded", "Excluded from Sample Output"),
        ],
        default="pending",
        required=True,
    )
    exception_reason = fields.Text()
    reviewer_notes = fields.Text()


class CryptoAuditEvidencePackage(models.Model):
    _name = "crypto.audit.evidence.package"
    _description = "Audit Evidence Package Support"
    _order = "period_end desc, id desc"

    name = fields.Char(required=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    period_start = fields.Date(required=True)
    period_end = fields.Date(required=True)
    payment_transaction_ids = fields.Many2many(
        "payment.transaction",
        relation="crypto_aep_payment_transaction_rel",
        string="Odoo Payment Transactions",
    )
    account_payment_ids = fields.Many2many(
        "account.payment",
        relation="crypto_aep_account_payment_rel",
        string="Odoo Account Payments",
    )
    account_move_line_ids = fields.Many2many(
        "account.move.line",
        relation="crypto_aep_account_move_line_rel",
        string="Odoo Journal Lines",
    )
    normalized_transaction_ids = fields.Many2many(
        "crypto.normalized.transaction",
        relation="crypto_aep_normalized_transaction_rel",
    )
    fair_value_measurement_ids = fields.Many2many(
        "crypto.fair.value.measurement",
        relation="crypto_aep_fair_value_measurement_rel",
    )
    journal_preparation_ids = fields.Many2many(
        "crypto.journal.entry.preparation",
        relation="crypto_aep_journal_preparation_rel",
    )
    reconciliation_status_ids = fields.Many2many(
        "crypto.reconciliation.status",
        relation="crypto_aep_reconciliation_status_rel",
    )
    tax_1099da_ids = fields.Many2many(
        "crypto.tax.readiness.1099da",
        relation="crypto_aep_tax_1099da_rel",
        string="1099-DA Readiness Lines",
    )
    form8949_ids = fields.Many2many(
        "crypto.form8949.reconciliation",
        relation="crypto_aep_form8949_rel",
        string="Form 8949 Support Lines",
    )
    reviewed_by_id = fields.Many2one("res.users", readonly=True, copy=False)
    reviewed_date = fields.Datetime(readonly=True, copy=False)
    reviewer_notes = fields.Text()
    summary_markdown = fields.Text(readonly=True)
    attachment_ids = fields.Many2many("ir.attachment", string="Generated Review Files")
    crypto_journal_line_count = fields.Integer(compute="_compute_review_counts")
    payment_transaction_count = fields.Integer(compute="_compute_review_counts")
    exception_count = fields.Integer(compute="_compute_review_counts")
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("prepared", "Prepared"),
            ("needs_review", "Needs Review"),
            ("reviewed", "Reviewed"),
        ],
        default="draft",
        required=True,
    )

    @api.depends("account_move_line_ids", "payment_transaction_ids", "reconciliation_status_ids")
    def _compute_review_counts(self):
        for record in self:
            record.crypto_journal_line_count = len(record.account_move_line_ids)
            record.payment_transaction_count = len(record.payment_transaction_ids)
            record.exception_count = len(record.reconciliation_status_ids.filtered(lambda item: item.status == "exception"))

    def action_print_cpa_review_package(self):
        self.ensure_one()
        return self.env.ref("crypto_payment_sync.action_report_crypto_cpa_review_package").report_action(self)

    def action_print_1099da_readiness(self):
        self.ensure_one()
        return self.env.ref("crypto_payment_sync.action_report_crypto_1099da_readiness").report_action(self)

    def action_print_form8949_support(self):
        self.ensure_one()
        return self.env.ref("crypto_payment_sync.action_report_crypto_8949_support").report_action(self)

    def action_mark_reviewed(self):
        for record in self:
            if not record.summary_markdown:
                raise UserError(_("Generate the review summary before marking this package as reviewed."))
            open_exceptions = record.reconciliation_status_ids.filtered(lambda item: item.status == "exception")
            if open_exceptions:
                raise UserError(_("Resolve or document reconciliation exceptions before marking this package as reviewed."))
            reviewable_lines = record.account_move_line_ids.filtered(
                lambda line: line.crypto_review_status in ("needs_review", "exception")
            )
            reviewable_lines.write({"crypto_review_status": "reviewed"})
            record.write({
                "status": "reviewed",
                "reviewed_by_id": self.env.user.id,
                "reviewed_date": fields.Datetime.now(),
            })

    def action_return_to_needs_review(self):
        for record in self:
            record.write({
                "status": "needs_review",
                "reviewed_by_id": False,
                "reviewed_date": False,
            })

    def action_collect_odoo_crypto_activity(self):
        for record in self:
            self.env["crypto.normalized.transaction"].action_sync_from_odoo_crypto_activity()
            line_domain = [
                ("date", ">=", record.period_start),
                ("date", "<=", record.period_end),
                ("company_id", "=", record.company_id.id),
                "|", "|", "|", "|",
                ("crypto_payment_transaction_id", "!=", False),
                ("crypto_account_payment_id", "!=", False),
                ("crypto_wallet_address_id", "!=", False),
                ("crypto_transaction_hash", "!=", False),
                ("crypto_asset_currency_id", "!=", False),
            ]
            move_lines = self.env["account.move.line"].search(line_domain)
            payment_transactions = move_lines.mapped("crypto_payment_transaction_id")
            account_payments = move_lines.mapped("crypto_account_payment_id")
            start_dt = "%s 00:00:00" % record.period_start
            end_dt = "%s 23:59:59" % record.period_end
            normalized = self.env["crypto.normalized.transaction"].search([
                ("timestamp", ">=", start_dt),
                ("timestamp", "<=", end_dt),
            ])
            record.write({
                "account_move_line_ids": [(6, 0, move_lines.ids)],
                "payment_transaction_ids": [(6, 0, payment_transactions.ids)],
                "account_payment_ids": [(6, 0, account_payments.ids)],
                "normalized_transaction_ids": [(6, 0, normalized.ids)],
                "status": "needs_review",
            })
            record._generate_reconciliation_from_odoo_lines(move_lines)

    def _generate_reconciliation_from_odoo_lines(self, move_lines):
        self.ensure_one()
        reconciliations = self.env["crypto.reconciliation.status"]
        for line in move_lines:
            status = "matched" if line.crypto_transaction_hash or line.crypto_payment_transaction_id else "pending"
            exception_reason = False
            if not line.crypto_transaction_hash:
                status = "exception"
                exception_reason = _("Missing blockchain transaction hash on Odoo journal line.")
            reconciliations |= self.env["crypto.reconciliation.status"].create({
                "name": "%s / %s" % (line.move_id.name or line.move_id.ref or line.id, line.account_id.display_name),
                "period_start": self.period_start,
                "period_end": self.period_end,
                "status": status,
                "exception_reason": exception_reason,
                "reviewer_notes": _("Generated from Odoo account.move.line for CPA/accountant review support."),
            })
        self.write({"reconciliation_status_ids": [(6, 0, reconciliations.ids)]})

    def action_generate_summary(self):
        for record in self:
            exceptions = record.reconciliation_status_ids.filtered(lambda item: item.status == "exception")
            asset_totals = record._transaction_asset_totals()
            asset_lines = [
                "| Asset | Transaction Quantity | Fiat Amount Support | Transactions | Journal Lines |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
            for symbol, totals in sorted(asset_totals.items()):
                asset_lines.append(
                    "| %s | %.8f | %.2f | %s | %s |"
                    % (symbol, totals["quantity"], totals["fiat_amount"], totals["transactions"], totals["lines"])
                )
            lines = [
                f"# Audit Evidence Package Summary: {record.name}",
                "",
                "This summary is a reviewable support material only. It is not an audit opinion, tax filing, legal conclusion, or accounting certification.",
                "",
                f"- Period: {record.period_start} to {record.period_end}",
                f"- Odoo payment transactions: {len(record.payment_transaction_ids)}",
                f"- Odoo account payments: {len(record.account_payment_ids)}",
                f"- Odoo journal lines with crypto traceability: {len(record.account_move_line_ids)}",
                f"- Normalized transactions: {len(record.normalized_transaction_ids)}",
                f"- Fair-value measurements: {len(record.fair_value_measurement_ids)}",
                f"- Journal-entry preparation records: {len(record.journal_preparation_ids)}",
                f"- Reconciliation records: {len(record.reconciliation_status_ids)}",
                f"- 1099-DA readiness lines: {len(record.tax_1099da_ids)}",
                f"- Form 8949 support lines: {len(record.form8949_ids)}",
                f"- Exceptions: {len(exceptions)}",
                "",
                "## FASB ASU 2023-08 Support View",
                "",
                "The table below summarizes transaction-level digital-asset activity linked to Odoo-native journal lines. It avoids double-counting quantities that appear on both debit and credit lines. Fair-value conclusions and accounting-policy decisions remain subject to professional review.",
                "",
                *asset_lines,
                "",
                "## CPA / Accountant Review Focus",
                "",
                "- Confirm that crypto asset quantities reconcile to wallet/source activity.",
                "- Review fair-value measurement source and timing for period-end reporting.",
                "- Confirm journal classification, revenue/receivable/clearing treatment, and any fee treatment.",
                "- Resolve missing transaction hashes, missing valuation data, and unmatched source records.",
                "",
                "## Reviewer Notes",
                record.reviewer_notes or "Pending professional review.",
            ]
            journal_attachment = record._create_journal_line_csv_attachment()
            transaction_attachment = record._create_transaction_summary_csv_attachment()
            attachments = [item.id for item in (journal_attachment, transaction_attachment) if item]
            record.write({
                "summary_markdown": "\n".join(lines),
                "attachment_ids": [(4, attachment_id) for attachment_id in attachments],
                "status": "prepared",
            })

    def _transaction_asset_totals(self):
        self.ensure_one()
        totals = {}
        for tx in self.payment_transaction_ids:
            wallet = tx.crypto_address.wallet_id if tx.crypto_address else self.env["crypto.wallet"]
            asset = tx.currency_id if tx.currency_id and tx.currency_id.type == "crypto" else wallet.currency_id
            symbol = self._asset_network_label_for_payment_transaction(tx)
            bucket = totals.setdefault(symbol, {"quantity": 0.0, "fiat_amount": 0.0, "transactions": 0, "lines": 0})
            bucket["quantity"] += tx.crypto_amount_eth or (tx.amount if tx.currency_id.type == "crypto" else 0.0)
            bucket["fiat_amount"] += tx.amount if tx.currency_id.type != "crypto" else 0.0
            bucket["transactions"] += 1
            bucket["lines"] += len(self.account_move_line_ids.filtered(lambda line: line.crypto_payment_transaction_id == tx))
        if not totals:
            for line in self.account_move_line_ids:
                symbol = line.crypto_asset_currency_id.name or line.currency_id.name or "Unspecified"
                bucket = totals.setdefault(symbol, {"quantity": 0.0, "fiat_amount": 0.0, "transactions": 0, "lines": 0})
                bucket["fiat_amount"] += line.debit or line.credit or 0.0
                bucket["lines"] += 1
        return totals

    def _asset_network_label_for_payment_transaction(self, payment_tx):
        wallet = payment_tx.crypto_address.wallet_id if payment_tx and payment_tx.crypto_address else self.env["crypto.wallet"]
        asset = (
            payment_tx.currency_id
            if payment_tx and payment_tx.currency_id and payment_tx.currency_id.type == "crypto"
            else wallet.currency_id
        )
        asset_label = asset.display_name or asset.name if asset else False
        if not asset_label and payment_tx and payment_tx.currency_id:
            asset_label = payment_tx.currency_id.display_name or payment_tx.currency_id.name
        network = wallet.network_id if wallet else self.env["crypto.network"]
        network_label = network.display_name or network.name if network else False
        if asset_label and network_label:
            return "%s - %s" % (asset_label.upper(), network_label.upper())
        return (asset_label or network_label or "Unspecified").upper()

    def _asset_network_label_for_normalized_transaction(self, normalized):
        payment_tx = normalized.payment_transaction_id
        if payment_tx:
            return self._asset_network_label_for_payment_transaction(payment_tx)
        asset_label = normalized.asset_id.display_name or normalized.asset_symbol or "Digital asset"
        network_label = normalized.network_id.display_name or normalized.chain_reference
        if asset_label and network_label:
            return "%s - %s" % (asset_label.upper(), network_label.upper())
        return (asset_label or "Digital asset").upper()

    def _source_reference_for_normalized_transaction(self, normalized):
        payment_tx = normalized.payment_transaction_id
        account_payment = normalized.account_payment_id
        references = []
        if normalized.transaction_hash:
            references.append(_("Blockchain hash: %s") % normalized.transaction_hash)
        if normalized.source_transaction_id:
            references.append(_("Odoo reference: %s") % normalized.source_transaction_id)
        if payment_tx and payment_tx.reference and payment_tx.reference not in references:
            references.append(_("Payment transaction: %s") % payment_tx.reference)
        if account_payment:
            payment_ref = account_payment.name
            if not payment_ref and "memo" in account_payment._fields:
                payment_ref = account_payment.memo
            if not payment_ref and "ref" in account_payment._fields:
                payment_ref = account_payment.ref
            if payment_ref:
                references.append(_("Account payment: %s") % payment_ref)
            memo = account_payment.memo if "memo" in account_payment._fields else False
            if memo and memo != payment_ref:
                references.append(_("Payment memo: %s") % memo)
        if not references:
            references.append(_("Source provider: %s") % (normalized.source_provider or "Needs Review"))
        return "\n".join(references)

    def _gross_support_for_normalized_transaction(self, normalized):
        payment_tx = normalized.payment_transaction_id
        if payment_tx:
            return payment_tx.amount or 0.0
        account_payment = normalized.account_payment_id
        if account_payment:
            return account_payment.amount or 0.0
        return 0.0

    def _cost_basis_support_for_normalized_transaction(self, normalized, gross_support):
        payment_tx = normalized.payment_transaction_id
        if payment_tx and payment_tx.amount:
            return payment_tx.amount
        account_payment = normalized.account_payment_id
        if account_payment and account_payment.amount:
            return account_payment.amount
        return gross_support or 0.0

    def _create_or_update_fair_value_measurement(self, normalized, gross_support, cost_basis_support):
        if not normalized.timestamp or not normalized.quantity:
            return self.env["crypto.fair.value.measurement"]
        existing = self.fair_value_measurement_ids.filtered(
            lambda item: item.normalized_transaction_id == normalized
        )[:1] or self.env["crypto.fair.value.measurement"].search(
            [("normalized_transaction_id", "=", normalized.id)],
            limit=1,
        )
        exchange_rate = gross_support / normalized.quantity if normalized.quantity else 0.0
        values = {
            "normalized_transaction_id": normalized.id,
            "asset_id": normalized.asset_id.id,
            "asset_symbol": normalized.asset_symbol,
            "measurement_datetime": normalized.timestamp,
            "pricing_source": _("Odoo payment amount / transaction quantity"),
            "source_api_provider": "odoo_payment",
            "exchange_rate": exchange_rate,
            "quantity": normalized.quantity,
            "carrying_amount": cost_basis_support,
            "valuation_status": "needs_review",
            "principal_market_notes": _(
                "Derived from Odoo payment support for reviewer convenience. Confirm valuation source, timing, and accounting policy before financial reporting use."
            ),
            "reviewer_notes": self._source_reference_for_normalized_transaction(normalized),
        }
        if existing:
            existing.write(values)
            return existing
        return self.env["crypto.fair.value.measurement"].create(values)

    def action_generate_tax_readiness_outputs(self):
        for record in self:
            record.tax_1099da_ids.unlink()
            record.form8949_ids.unlink()
            payment_transactions = record.payment_transaction_ids | record.account_move_line_ids.mapped("crypto_payment_transaction_id")
            if not payment_transactions and not record.account_move_line_ids:
                record.action_collect_odoo_crypto_activity()
                payment_transactions = record.payment_transaction_ids | record.account_move_line_ids.mapped("crypto_payment_transaction_id")
            normalized = record.normalized_transaction_ids
            for payment_tx in payment_transactions:
                normalized |= self.env["crypto.normalized.transaction"]._sync_payment_transaction(payment_tx)
            if normalized:
                record.write({"normalized_transaction_ids": [(6, 0, normalized.ids)]})
            tax_lines = self.env["crypto.tax.readiness.1099da"]
            form_lines = self.env["crypto.form8949.reconciliation"]
            fair_value_lines = record.fair_value_measurement_ids
            for tx in record.normalized_transaction_ids:
                payment_tx = tx.payment_transaction_id
                gross_support = record._gross_support_for_normalized_transaction(tx)
                cost_basis_support = record._cost_basis_support_for_normalized_transaction(tx, gross_support)
                source_reference = record._source_reference_for_normalized_transaction(tx)
                fair_value_lines |= record._create_or_update_fair_value_measurement(
                    tx,
                    gross_support,
                    cost_basis_support,
                )
                ready_for_preparer = bool(
                    tx.timestamp
                    and tx.asset_symbol
                    and tx.quantity
                    and gross_support
                    and tx.transaction_hash
                    and tx.wallet_address_id
                )
                status = "ready_for_review" if ready_for_preparer else "needs_review"
                missing_notes = []
                if not tx.transaction_hash:
                    missing_notes.append(_("Missing blockchain transaction hash."))
                if not tx.wallet_address_id:
                    missing_notes.append(_("Missing wallet/source address."))
                if not tx.quantity:
                    missing_notes.append(_("Missing digital-asset quantity."))
                if not gross_support:
                    missing_notes.append(_("Missing gross proceeds/value support."))
                tax_lines |= self.env["crypto.tax.readiness.1099da"].create({
                    "normalized_transaction_id": tx.id,
                    "transaction_datetime": tx.timestamp,
                    "asset_symbol": tx.asset_symbol,
                    "quantity": tx.quantity,
                    "gross_proceeds_support": gross_support,
                    "wallet_source_reference": tx.wallet_address_id.name,
                    "transaction_hash": tx.transaction_hash,
                    "broker_source_reference": source_reference,
                    "cost_basis_support": cost_basis_support,
                    "federal_income_tax_withheld": 0.0,
                    "status": status,
                    "missing_data_notes": " ".join(missing_notes) or _(
                        "Core payment fields are populated. Cost basis and withholding are derived from Odoo support fields where available and require preparer review."
                    ),
                })
                form_lines |= self.env["crypto.form8949.reconciliation"].create({
                    "normalized_transaction_id": tx.id,
                    "description_of_property": "%s digital asset - %s review" % (
                        record._asset_network_label_for_normalized_transaction(tx),
                        dict(tx._fields["transaction_type"].selection).get(tx.transaction_type, tx.transaction_type),
                    ),
                    "date_acquired": tx.timestamp.date() if tx.timestamp else False,
                    "date_disposed": tx.timestamp.date() if tx.timestamp else False,
                    "proceeds_support": gross_support,
                    "cost_basis_support": cost_basis_support,
                    "holding_period_support": "needs_review",
                    "source_links": source_reference,
                    "status": status,
                    "reviewer_notes": _(
                        "Screening row generated from Odoo crypto payment activity. Date and basis fields are derived from available Odoo support records and require preparer review before final use."
                    ),
                })
            record.write({
                "tax_1099da_ids": [(6, 0, tax_lines.ids)],
                "form8949_ids": [(6, 0, form_lines.ids)],
                "fair_value_measurement_ids": [(6, 0, fair_value_lines.ids)],
                "status": "needs_review",
            })

    def _create_journal_line_csv_attachment(self):
        self.ensure_one()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "date",
            "move",
            "account",
            "partner",
            "debit",
            "credit",
            "asset",
            "quantity",
            "tx_hash",
            "wallet_address",
            "payment_reference",
            "review_status",
        ])
        for line in self.account_move_line_ids:
            writer.writerow([
                line.date,
                line.move_id.name or line.move_id.ref,
                line.account_id.display_name,
                line.partner_id.display_name,
                line.debit,
                line.credit,
                line.crypto_asset_currency_id.name,
                line.crypto_asset_quantity,
                line.crypto_transaction_hash,
                line.crypto_wallet_address_id.name,
                line.crypto_source_reference,
                line.crypto_review_status,
            ])
        data = base64.b64encode(output.getvalue().encode("utf-8"))
        return self.env["ir.attachment"].create({
            "name": "%s_crypto_journal_lines.csv" % (self.name.replace("/", "_")),
            "type": "binary",
            "datas": data,
            "res_model": self._name,
            "res_id": self.id,
            "mimetype": "text/csv",
        })

    def _create_transaction_summary_csv_attachment(self):
        self.ensure_one()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "reference",
            "created_on",
            "customer",
            "payment_provider",
            "state",
            "asset",
            "crypto_quantity",
            "transaction_currency",
            "transaction_amount",
            "tx_hash",
            "wallet_address",
            "journal_moves",
            "journal_line_count",
            "review_status",
        ])
        for tx in self.payment_transaction_ids.sorted(lambda item: item.create_date or fields.Datetime.now()):
            tx_lines = self.account_move_line_ids.filtered(lambda line: line.crypto_payment_transaction_id == tx)
            wallet = tx.crypto_address.wallet_id if tx.crypto_address else self.env["crypto.wallet"]
            asset = tx.currency_id if tx.currency_id and tx.currency_id.type == "crypto" else wallet.currency_id
            review_status = "needs_review"
            if tx.crypto_tx_hash and tx_lines:
                review_status = "ready_for_review"
            writer.writerow([
                tx.reference,
                tx.create_date,
                tx.partner_id.display_name,
                tx.provider_id.name,
                tx.state,
                asset.name,
                tx.crypto_amount_eth or (tx.amount if tx.currency_id.type == "crypto" else 0.0),
                tx.currency_id.name,
                tx.amount,
                tx.crypto_tx_hash,
                tx.crypto_address.name,
                ", ".join(sorted(set(tx_lines.mapped("move_id.name")))),
                len(tx_lines),
                review_status,
            ])
        data = base64.b64encode(output.getvalue().encode("utf-8"))
        return self.env["ir.attachment"].create({
            "name": "%s_crypto_transaction_summary.csv" % (self.name.replace("/", "_")),
            "type": "binary",
            "datas": data,
            "res_model": self._name,
            "res_id": self.id,
            "mimetype": "text/csv",
        })


class CryptoTaxReadiness1099DA(models.Model):
    _name = "crypto.tax.readiness.1099da"
    _description = "1099-DA Field-Mapping Readiness"
    _order = "transaction_datetime desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    normalized_transaction_id = fields.Many2one("crypto.normalized.transaction")
    transaction_datetime = fields.Datetime()
    asset_symbol = fields.Char()
    quantity = fields.Float(digits=(20, 8))
    gross_proceeds_support = fields.Float()
    wallet_source_reference = fields.Char()
    transaction_hash = fields.Char()
    broker_source_reference = fields.Char()
    cost_basis_support = fields.Float()
    federal_income_tax_withheld = fields.Float()
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("ready_for_review", "Ready for Preparer Review"),
            ("needs_review", "Needs Review"),
            ("reviewed", "Reviewed"),
            ("exception", "Exception"),
        ],
        default="needs_review",
        required=True,
    )
    missing_data_notes = fields.Text()
    reviewer_notes = fields.Text()

    @api.depends("asset_symbol", "transaction_hash", "transaction_datetime")
    def _compute_name(self):
        for record in self:
            record.name = f"1099-DA readiness - {record.asset_symbol or 'Asset'} - {record.transaction_hash or record.transaction_datetime or ''}"


class CryptoForm8949Reconciliation(models.Model):
    _name = "crypto.form8949.reconciliation"
    _description = "Form 8949 Reconciliation Support"
    _order = "date_disposed desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    normalized_transaction_id = fields.Many2one("crypto.normalized.transaction")
    description_of_property = fields.Char(required=True)
    date_acquired = fields.Date()
    date_disposed = fields.Date()
    proceeds_support = fields.Float()
    cost_basis_support = fields.Float()
    gain_loss_support = fields.Float(compute="_compute_gain_loss", store=True)
    holding_period_support = fields.Selection(
        [("short_term", "Short Term"), ("long_term", "Long Term"), ("needs_review", "Needs Review")],
        default="needs_review",
    )
    source_links = fields.Text()
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("ready_for_review", "Ready for Preparer Review"),
            ("needs_review", "Needs Review"),
            ("reviewed", "Reviewed"),
            ("exception", "Exception"),
        ],
        default="needs_review",
        required=True,
    )
    reviewer_notes = fields.Text()

    @api.depends("description_of_property", "date_disposed")
    def _compute_name(self):
        for record in self:
            record.name = f"Form 8949 support - {record.description_of_property or 'Asset'} - {record.date_disposed or ''}"

    @api.depends("proceeds_support", "cost_basis_support")
    def _compute_gain_loss(self):
        for record in self:
            record.gain_loss_support = (record.proceeds_support or 0.0) - (record.cost_basis_support or 0.0)
