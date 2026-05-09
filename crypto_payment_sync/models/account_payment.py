from odoo import _, fields, models
from odoo.exceptions import UserError


class ResPartnerCryptoAddress(models.Model):
    _name = 'res.partner.crypto.address'
    _description = 'Contact Crypto Address'

    name = fields.Char(string="Address", required=True)

    network_id = fields.Many2one('crypto.network', string="Network", required=True)

    blockchain_id = fields.Many2one('crypto.blockchain', related="network_id.blockchain_id", string="Blockchain")

    currency_id = fields.Many2one('res.currency', string="Currency", domain=[('type', '=', 'crypto')])

    partner_id = fields.Many2one("res.partner", string="Partner")


class ResPartner(models.Model):
    _inherit = 'res.partner'

    crypto_address_ids = fields.One2many("res.partner.crypto.address", "partner_id", string="Crypto Addresses")


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_crypto = fields.Boolean(string="Is Crypto")


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    from_address_id = fields.Many2one("res.partner.crypto.address", string="From Crypto Address")
    to_address_id = fields.Many2one("res.partner.crypto.address", string="To Crypto Address")
    crypto_transaction_id = fields.Many2one("crypto.transaction.evm", string="Crypto Transaction")

    is_crypto = fields.Boolean(related="journal_id.is_crypto", string="is_crypto")

    def action_post(self):
        for record in self:
            if (
                record.journal_id.is_crypto
                and record.payment_type == "outbound"
                and record.currency_id.type != 'fiat'
            ):
                if not record.to_address_id or not record.from_address_id:
                    raise UserError(_(
                        "To record payments with %(journal_name)s, the recipient crypto address account must be selected "
                        "You should select the partner crypto address account of %(partner)s or select Other Journal",
                        journal_name=record.journal_id.name,
                        partner=record.partner_id.display_name,
                    ))

            wallet_address_id = self.env['crypto.wallet.address'].search(
                [('name', '=', record.from_address_id.name)], limit=1
            )
            if wallet_address_id:
                trans = self.env["crypto.transaction.evm"].create({
                    'recipient': record.to_address_id.name,
                    'sender': record.from_address_id.name,
                    'value_amount': record.amount,
                    'wallet_address_id': wallet_address_id.id
                })
                record.write({'crypto_transaction_id': trans.id})
                allow_broadcast = self.env['ir.config_parameter'].sudo().get_param(
                    'crypto_payment_sync.allow_transaction_broadcast'
                ) == '1'
                if not allow_broadcast:
                    raise UserError(_(
                        "Automatic crypto transaction signing and broadcast is disabled by default. "
                        "Set crypto_payment_sync.allow_transaction_broadcast to 1 only in an approved test workflow."
                    ))
                trans.send_native_from_odoo()
                continue  # Move to next record

            if record.payment_transaction_id and record.payment_transaction_id.crypto_address:
                to_address_id = self.env['res.partner.crypto.address'].search(
                    [('name', '=', record.payment_transaction_id.crypto_address.name)], limit=1
                )
                if not to_address_id:
                    to_address_id = self.env['res.partner.crypto.address'].create({
                        'partner_id': record.company_id.partner_id.id,
                        'name': record.payment_transaction_id.crypto_address.name,
                        'network_id': record.payment_transaction_id.crypto_address.wallet_id.network_id.id,
                        'blockchain_id': record.payment_transaction_id.crypto_address.wallet_id.blockchain_id.id,
                        'currency_id': record.currency_id.id
                    })
                trans = self.env["crypto.transaction.evm"].create({
                    'wallet_address_id': record.payment_transaction_id.crypto_address.id,
                    'tx_hash': record.payment_transaction_id.crypto_tx_hash
                })
                trans.get_transaction_details()
                from_address_id = self.env['res.partner.crypto.address'].search(
                    [('name', '=', trans.sender)], limit=1
                )
                if not from_address_id:
                    from_address_id = self.env['res.partner.crypto.address'].create({
                        'partner_id': record.partner_id.id,
                        'name': trans.sender,
                        'network_id': record.payment_transaction_id.crypto_address.wallet_id.network_id.id,
                        'blockchain_id': record.payment_transaction_id.crypto_address.wallet_id.blockchain_id.id,
                        'currency_id': record.currency_id.id
                    })
                record.write({
                    'crypto_transaction_id': trans.id,
                    'from_address_id': from_address_id.id,
                    'to_address_id': to_address_id.id
                })

        return super(AccountPayment, self).action_post()







