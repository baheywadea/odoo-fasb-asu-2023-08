import hashlib
import json

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


class CryptoNormalizedTransaction(models.Model):
    _name = "crypto.normalized.transaction"
    _description = "Normalized Digital-Asset Transaction"
    _order = "timestamp desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    source_provider = fields.Char(default="cryptoapis", required=True)
    provider_id = fields.Many2one(
        "payment.provider",
        string="Odoo Payment Provider",
        domain=[("code", "=", "crypto")],
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
        raw_payload = values.get("raw_payload")
        if isinstance(raw_payload, (dict, list)):
            values["raw_payload"] = json.dumps(raw_payload, sort_keys=True)
        timestamp = values.get("timestamp")
        if isinstance(timestamp, str):
            values["timestamp"] = timestamp.replace("T", " ").replace("+00:00", "").replace("Z", "")
        return self.create(values)


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
    period_start = fields.Date(required=True)
    period_end = fields.Date(required=True)
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
    reviewer_notes = fields.Text()
    summary_markdown = fields.Text(readonly=True)
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

    def action_generate_summary(self):
        for record in self:
            exceptions = record.reconciliation_status_ids.filtered(lambda item: item.status == "exception")
            lines = [
                f"# Audit Evidence Package Summary: {record.name}",
                "",
                "This summary is a reviewable support material only. It is not an audit opinion, tax filing, legal conclusion, or accounting certification.",
                "",
                f"- Period: {record.period_start} to {record.period_end}",
                f"- Normalized transactions: {len(record.normalized_transaction_ids)}",
                f"- Fair-value measurements: {len(record.fair_value_measurement_ids)}",
                f"- Journal-entry preparation records: {len(record.journal_preparation_ids)}",
                f"- Reconciliation records: {len(record.reconciliation_status_ids)}",
                f"- Exceptions: {len(exceptions)}",
                "",
                "## Reviewer Notes",
                record.reviewer_notes or "Pending professional review.",
            ]
            record.write({"summary_markdown": "\n".join(lines), "status": "prepared"})


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
    status = fields.Selection(
        [("draft", "Draft"), ("needs_review", "Needs Review"), ("reviewed", "Reviewed"), ("exception", "Exception")],
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
        [("draft", "Draft"), ("needs_review", "Needs Review"), ("reviewed", "Reviewed"), ("exception", "Exception")],
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
