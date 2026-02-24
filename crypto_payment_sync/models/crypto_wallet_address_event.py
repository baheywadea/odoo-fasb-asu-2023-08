import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


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
            blockchain = record.wallet_id.blockchain_id.name.lower()
            network = record.wallet_id.network_id.name.lower().replace('testnet', "").replace(blockchain, "").replace(" ", "")
            # address = record.name
            referenceId = record.reference_id
            url = f"https://rest.cryptoapis.io/blockchain-events/{blockchain}/{network}/{referenceId}?context=OdooGetEvent"
            headers = {
                "X-API-Key": record.wallet_id.payment_provider_id.cryptoapis_api_key
            }
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                raise Exception(f"Failed to fetch Event : {response.text}")
            _logger.info('response' + str(response))
            data = response.json().get("data", [])
            _logger.info('response Json Data' + str(data))
            item = data.get("item", [])

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

