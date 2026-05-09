from odoo import models, fields, _
from odoo.exceptions import UserError
from datetime import datetime


class CryptoWalletAddressEvent(models.Model):
    _name = 'crypto.wallet.address.event'
    _description = 'Crypto Wallet Address Event'

    name = fields.Char(string="Call Back URL", required=True)

    address_id = fields.Many2one('crypto.wallet.address', string="Address", required=True)

    wallet_id = fields.Many2one('crypto.wallet', related="address_id.wallet_id", string="Crypto Wallet")

    network_id = fields.Many2one('crypto.network', related="wallet_id.network_id", string="Network")

    blockchain_id = fields.Many2one('crypto.blockchain', related="network_id.blockchain_id", string="Blockchain")

    created_timestamp = fields.Datetime(string="Created Timestamp")

    event_type = fields.Char("Event Type")

    active = fields.Boolean(string="Active")

    allow_duplicates = fields.Boolean(string="Allow Dupilcates")

    callback_secretkey = fields.Char(string="Callback SecretKey")

    receive_callback_on = fields.Integer(string="Receive Callback On")

    confirmations_count = fields.Integer(string="Confirmations Count")

    reference_id = fields.Char(string="ReferenceId")

    transaction_id = fields.Char(string="Transaction ID")

    deactivation_reasons = fields.Char(string="Deactivation Reasons")

    deactivation_timestamp = fields.Datetime(string="Deactivation Timestamp")



    def get_event_details(self):

        for record in self:
            referenceId = record.reference_id
            if not referenceId:
                raise UserError(_("Set the Crypto APIs event reference before fetching event details."))
            provider = record.wallet_id.payment_provider_id
            _family, blockchain, network = record.wallet_id._cryptoapis_path_parts()
            data = provider._cryptoapis_get(
                f"blockchain-events/{blockchain}/{network}/{referenceId}",
                params={"context": "OdooGetEvent"},
            ).get("data") or {}
            item = data.get("item") or {}

            record.write({
                # "address": "tb1qtm44m6xmuasy4sc7nl7thvuxcerau2dfvkkgsc",
                # "blockchain": "bitcoin",
                "callback_secretkey": item.get("callbackSecretKey"),
                "name": item.get("callbackUrl"),
                "confirmations_count": item.get("confirmationsCount"),
                "created_timestamp": datetime.utcfromtimestamp(data.get('createdTimestamp')) if data.get('createdTimestamp') else False,

                "event_type": item.get("eventType"),
                "active": item.get("isActive"),
                "reference_id": item.get("referenceId"),
                "transaction_id": item.get("transactionId"),

            })
