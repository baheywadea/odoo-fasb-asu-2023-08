from odoo import _, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    crypto_payment_transaction_id = fields.Many2one(
        "payment.transaction",
        string="Crypto Payment Transaction",
        copy=False,
        index=True,
    )
    crypto_normalized_transaction_id = fields.Many2one(
        "crypto.normalized.transaction",
        string="External Normalization Support",
        copy=False,
        index=True,
    )
    crypto_account_payment_id = fields.Many2one(
        "account.payment",
        string="Crypto Account Payment",
        copy=False,
        index=True,
    )
    crypto_source_reference = fields.Char(string="Crypto Source Reference", copy=False, index=True)
    crypto_transaction_hash = fields.Char(string="Crypto Transaction Hash", copy=False, index=True)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    crypto_payment_transaction_id = fields.Many2one(
        "payment.transaction",
        string="Crypto Payment Transaction",
        copy=False,
        index=True,
    )
    crypto_normalized_transaction_id = fields.Many2one(
        "crypto.normalized.transaction",
        string="External Normalization Support",
        copy=False,
        index=True,
    )
    crypto_account_payment_id = fields.Many2one(
        "account.payment",
        string="Crypto Account Payment",
        copy=False,
        index=True,
    )
    crypto_wallet_address_id = fields.Many2one(
        "crypto.wallet.address",
        string="Crypto Wallet Address",
        copy=False,
        index=True,
    )
    crypto_transaction_evm_id = fields.Many2one(
        "crypto.transaction.evm",
        string="EVM Transaction",
        copy=False,
        index=True,
    )
    crypto_asset_currency_id = fields.Many2one(
        "res.currency",
        string="Crypto Asset",
        copy=False,
        domain=[("type", "=", "crypto")],
    )
    crypto_asset_quantity = fields.Float(string="Crypto Quantity", digits=(24, 12), copy=False)
    crypto_source_reference = fields.Char(string="Crypto Source Reference", copy=False, index=True)
    crypto_transaction_hash = fields.Char(string="Crypto Transaction Hash", copy=False, index=True)
    crypto_review_status = fields.Selection(
        [
            ("not_applicable", "Not Applicable"),
            ("needs_review", "Needs Review"),
            ("reviewed", "Reviewed"),
            ("exception", "Exception"),
        ],
        string="Crypto Review Status",
        default="not_applicable",
        copy=False,
    )


class AccountPayment(models.Model):
    _inherit = "account.payment"

    crypto_move_line_count = fields.Integer(compute="_compute_crypto_move_line_count")
    digital_asset_move_line_count = fields.Integer(compute="_compute_crypto_move_line_count")

    def _crypto_traceable_move_lines(self):
        self.ensure_one()
        move = self.move_id if "move_id" in self._fields else self.env["account.move"]
        return move.line_ids.filtered(
            lambda line: line.crypto_payment_transaction_id
            or line.crypto_account_payment_id
            or line.crypto_wallet_address_id
            or line.crypto_transaction_hash
            or line.crypto_transaction_evm_id
        )

    def _compute_crypto_move_line_count(self):
        for record in self:
            count = len(record._crypto_traceable_move_lines()) if record.id else 0
            record.crypto_move_line_count = count
            record.digital_asset_move_line_count = count

    def action_view_crypto_move_lines(self):
        self.ensure_one()
        lines = self._crypto_traceable_move_lines()
        list_view = self.env.ref("crypto_payment_sync.view_account_move_line_crypto_traceability_list")
        form_view = self.env.ref("crypto_payment_sync.view_account_move_line_crypto_traceability_form")
        return {
            "type": "ir.actions.act_window",
            "name": _("Crypto Accounting Lines"),
            "res_model": "account.move.line",
            "view_mode": "list,form",
            "views": [(list_view.id, "list"), (form_view.id, "form")],
            "domain": [("id", "in", lines.ids)],
        }

    def action_view_digital_asset_move_lines(self):
        return self.action_view_crypto_move_lines()

    def action_post(self):
        result = super().action_post()
        for payment in self:
            payment._apply_crypto_traceability_to_move()
        return result

    def _apply_crypto_traceability_to_move(self):
        self.ensure_one()
        if not self.move_id:
            return

        payment_tx = self.payment_transaction_id if "payment_transaction_id" in self._fields else False
        wallet_address = payment_tx.crypto_address if payment_tx and payment_tx.crypto_address else False
        tx_hash = (
            payment_tx.crypto_tx_hash
            if payment_tx and payment_tx.crypto_tx_hash
            else self.crypto_transaction_id.tx_hash if self.crypto_transaction_id else False
        )
        source_reference = (
            payment_tx.reference
            if payment_tx
            else self.memo if "memo" in self._fields
            else self.ref if "ref" in self._fields
            else self.name
        )

        if not (payment_tx or wallet_address or tx_hash or self.crypto_transaction_id or self.is_crypto):
            return

        move_values = {
            "crypto_payment_transaction_id": payment_tx.id if payment_tx else False,
            "crypto_account_payment_id": self.id,
            "crypto_source_reference": source_reference,
            "crypto_transaction_hash": tx_hash,
        }
        self.move_id.write({key: value for key, value in move_values.items() if value})

        line_values = dict(move_values)
        line_values.update({
            "crypto_wallet_address_id": wallet_address.id if wallet_address else False,
            "crypto_transaction_evm_id": self.crypto_transaction_id.id if self.crypto_transaction_id else False,
            "crypto_asset_currency_id": self.currency_id.id if self.currency_id and self.currency_id.type == "crypto" else False,
            "crypto_asset_quantity": self.amount if self.currency_id and self.currency_id.type == "crypto" else 0.0,
            "crypto_review_status": "needs_review" if tx_hash or wallet_address or self.is_crypto else "not_applicable",
        })
        clean_values = {key: value for key, value in line_values.items() if value not in (False, None, "")}
        for line in self.move_id.line_ids:
            if line.display_type in ("line_section", "line_note"):
                continue
            line.write(clean_values)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    crypto_move_line_count = fields.Integer(compute="_compute_crypto_move_line_count")
    digital_asset_move_line_count = fields.Integer(compute="_compute_crypto_move_line_count")

    def _crypto_traceable_move_lines(self):
        self.ensure_one()
        payments = self.env["account.payment"].search([("payment_transaction_id", "=", self.id)])
        lines = payments.mapped("move_id.line_ids").filtered(
            lambda line: line.crypto_payment_transaction_id
            or line.crypto_account_payment_id
            or line.crypto_wallet_address_id
            or line.crypto_transaction_hash
            or line.crypto_transaction_evm_id
        )
        if not lines and self.crypto_tx_hash:
            lines = self.env["account.move.line"].search([("crypto_transaction_hash", "=", self.crypto_tx_hash)])
        return lines

    def _compute_crypto_move_line_count(self):
        for record in self:
            count = len(record._crypto_traceable_move_lines()) if record.id else 0
            record.crypto_move_line_count = count
            record.digital_asset_move_line_count = count

    def action_view_crypto_move_lines(self):
        self.ensure_one()
        lines = self._crypto_traceable_move_lines()
        list_view = self.env.ref("crypto_payment_sync.view_account_move_line_crypto_traceability_list")
        form_view = self.env.ref("crypto_payment_sync.view_account_move_line_crypto_traceability_form")
        return {
            "type": "ir.actions.act_window",
            "name": _("Crypto Accounting Lines"),
            "res_model": "account.move.line",
            "view_mode": "list,form",
            "views": [(list_view.id, "list"), (form_view.id, "form")],
            "domain": [("id", "in", lines.ids)],
        }

    def action_view_digital_asset_move_lines(self):
        return self.action_view_crypto_move_lines()
