import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from datetime import datetime, timedelta
from odoo.http import request
import time

_logger = logging.getLogger(__name__)


class CryptoWalletAddress(models.Model):
    _name = 'crypto.wallet.address'
    _description = 'Crypto Wallet Address'

    name = fields.Char(string="Address", required=True)

    wallet_id = fields.Many2one('crypto.wallet', string="Wallet", required=True)

    index = fields.Integer(string="Index", required=True)

    confirmed_balance = fields.Float(string="ConfirmedBalance")

    last_synced_balance = fields.Datetime(string="Last Synced Time")

    transactions_evm_count = fields.Integer(compute="_compute_transactions_evm_count", store=False)

    transaction_evm_ids = fields.One2many('crypto.transaction.evm', 'wallet_address_id', string="Wallet Addresses")

    event_ids = fields.One2many('crypto.wallet.address.event', 'address_id', string="Wallet Addresses")

    events_count = fields.Integer(compute="_compute_events_count", store=False)

    order = fields.Char(string="Order Temporary For Event Create")

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The Address must be unique!')
    ]

    payment_transaction_id = fields.Many2one("payment.transaction", string="Payment Transaction")

    @api.depends('transaction_evm_ids')
    def _compute_transactions_evm_count(self):
        for record in self:
            record['transactions_evm_count'] = self.env['crypto.transaction.evm'].search_count(
                [('wallet_address_id', '=', record.id)])

    @api.depends('event_ids')
    def _compute_events_count(self):
        for record in self:
            record['events_count'] = self.env['crypto.wallet.address.event'].search_count(
                [('address_id', '=', record.id)])

    def get_balance(self):

        for record in self:
            # Calculate the difference
            if record.last_synced_balance:
                time_diff = datetime.now() - record.last_synced_balance
            else:
                time_diff = timedelta(hours=1)
            _logger.info('time_diff ' + str(time_diff.total_seconds()))
            # Check if more than one minute
            if time_diff.total_seconds() > 60:
                _logger.info('Inside IF')
                blockchain = record.wallet_id.blockchain_id.name.lower()
                network = record.wallet_id.network_id.name.lower().replace('testnet', "").replace(blockchain,
                                                                                                  "").replace(" ", "")
                address = record.name
                url = f"https://rest.cryptoapis.io/addresses-latest/evm/{blockchain}/{network}/{address}/balance?context=OdooGetAddressBalance"
                if 'ether' in blockchain:
                    url = f"https://rest.cryptoapis.io/addresses-latest/evm/{blockchain}/{network}/{address}/balance?context=OdooGetAddressBalance"

                if 'bitcoin' in blockchain:
                    url = f"https://rest.cryptoapis.io/addresses-latest/utxo/{blockchain}/{network}/{address}/balance?context=OdooGetAddressBalance"
                if 'xrp' in blockchain:
                    url = f"https://rest.cryptoapis.io/addresses-latest/{blockchain}/{network}/{address}/balance?context=OdooGetAddressBalance"

                headers = {
                    "X-API-Key": record.wallet_id.payment_provider_id.cryptoapis_api_key
                }
                response = requests.get(url, headers=headers)
                if response.status_code != 200:
                    raise Exception(f"Failed to fetch crypto currencies: {response.text}")
                _logger.info('response' + str(response))
                data = response.json().get("data", [])
                _logger.info('response Json Data' + str(data))
                item = data.get("item", [])
                _logger.info('response Json Item' + str(item))
                confirmedBalance = item.get("confirmedBalance", [])
                amount = confirmedBalance.get("amount")
                record.write({'confirmed_balance': amount, 'last_synced_balance': fields.Datetime.now()})

    def get_confirmed_transactions(self):

        for record in self:
            blockchain = record.wallet_id.blockchain_id.name.lower()
            network = record.wallet_id.network_id.name.lower().replace('testnet', "").replace(blockchain, "").replace(
                " ", "")
            address = record.name
            if 'ether' in blockchain:
                url = f"https://rest.cryptoapis.io/addresses-latest/evm/{blockchain}/{network}/{address}/transactions?context=OdooEVMGetConfirmedTransactions&limit=10&sortingOrder=descending"
            if 'bitcoin' in blockchain:
                url = f"https://rest.cryptoapis.io/addresses-latest/utxo/{blockchain}/{network}/{address}/transactions?context=OdooEVMGetConfirmedTransactions&limit=10&sortingOrder=descending"
            if 'xrp' in blockchain:
                url = f"https://rest.cryptoapis.io/addresses-latest/{blockchain}/{network}/{address}/transactions?context=OdooEVMGetConfirmedTransactions&limit=10&sortingOrder=descending"

            headers = {
                "X-API-Key": record.wallet_id.payment_provider_id.cryptoapis_api_key
            }
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                raise Exception(f"Failed to fetch crypto transactions: {response.text}")
            _logger.info('response' + str(response))
            data = response.json().get("data", [])
            _logger.info('response Json Data' + str(data))
            items = data.get("items", [])
            transaction_obj = self.env['crypto.transaction.evm']
            for item in items:
                is_Exist = transaction_obj.search([('tx_hash', '=', item.get('hash'))])
                if not is_Exist:
                    trx_id = transaction_obj.create_from_json(item)
                    trx_id.write({'wallet_address_id': record.id})

    def action_generate_event_old(self, param_order=None):
        for rec in self:
            if rec.order or param_order:
                order = param_order or rec.order
                api_key = rec.wallet_id.payment_provider_id.cryptoapis_api_key
                website = request.env['website'].get_current_website()
                odoo_base_url = website.domain or request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                blockchain = rec.wallet_id.blockchain_id.name.lower()
                network = rec.wallet_id.network_id.name.lower().replace(" ", "-").replace(blockchain, "").replace("testnet",
                                                                                                         "").replace(
                    "-",
                    "")

                # CryptoAPIs endpoint to derive address from xpub

                url = f"https://rest.cryptoapis.io/blockchain-events/{blockchain}/{network}/address-coins-transactions-confirmed"

                headers = {
                    "Content-Type": "application/json",
                    "X-API-Key": api_key
                }

                payload = {
                    "context": "create_address_event_from_odoo",
                    "data": {
                        "item": {
                            "address": rec.name,
                            "allowDuplicates": False,
                            "callbackSecretKey": order,
                            "callbackUrl": f"{odoo_base_url}/invoice_link/crypto/callback",
                            "receiveCallbackOn": 3
                        }
                    }
                }
                _logger.info('Reuested URL' + str(url))
                response = requests.post(url, json=payload, headers=headers)
                _logger.info('Response Statuse Code' + str(response.status_code))
                if response.status_code != 200 and response.status_code != 201 :
                    raise UserError(_("Event creation failed: %s") % response.text)

                event_data = response.json().get('data', {}).get('item', {})
                self.env['crypto.wallet.address.event'].create({'reference_id': event_data.get('referenceId'),
                                                                "address_id": rec.id,
                                                                "callback_secretkey": event_data.get(
                                                                    "callbackSecretKey"),
                                                                "name": event_data.get("callbackUrl"),
                                                                "created_timestamp": datetime.utcfromtimestamp(
                                                                    event_data.get(
                                                                        'createdTimestamp')) if event_data.get(
                                                                    'createdTimestamp') else False,
                                                                "event_type": event_data.get("eventType"),
                                                                "active": event_data.get("isActive"),
                                                                "reference_id": event_data.get("referenceId"),
                                                                })
                return event_data

    def action_generate_event(self, tx_id, secret_token):
        """
        Create CryptoAPIs subscription for this address.
        callbackUrl includes tx_id.
        callbackSecretKey is a string secret (secret_token).
        """
        self.ensure_one()

        api_key = self.wallet_id.payment_provider_id.cryptoapis_api_key
        if not api_key:
            raise UserError(_("CryptoAPIs API key is missing on the payment provider."))

        # ✅ Stable base url (do NOT use request.env/website.domain)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
        base_url = base_url.rstrip('/')

        blockchain = (self.wallet_id.blockchain_id.name or '').lower().strip()
        network = (self.wallet_id.network_id.name or '').lower().strip()

        # ⚠️ Better: store CryptoAPIs network code explicitly in your crypto.network model.
        # Keeping your normalization but safer:
        network = network.replace(" ", "-").replace(blockchain, "").replace("testnet", "")
        network = network.replace("-", "").strip()

        url = f"https://rest.cryptoapis.io/blockchain-events/{blockchain}/{network}/address-coins-transactions-confirmed"

        headers = {"Content-Type": "application/json", "X-API-Key": api_key}

        # ✅ Ensure address is a string
        address_str = self.name.name if hasattr(self.name, "name") else self.name
        address_str = (address_str or "").strip()
        if not address_str:
            raise UserError(_("Address is empty; cannot create event subscription."))

        callback_url = f"{base_url}/invoice_link/crypto/callback/{int(tx_id)}"

        payload = {
            "context": "create_address_event_from_odoo",
            "data": {
                "item": {
                    "address": address_str,
                    "allowDuplicates": False,
                    "callbackSecretKey": str(secret_token),  # ✅ MUST be string
                    "callbackUrl": callback_url,  # ✅ includes tx_id
                    "receiveCallbackOn": 3
                }
            }
        }

        _logger.info("CryptoAPIs Event URL: %s", url)
        _logger.info("CryptoAPIs Payload: %s", payload)

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        _logger.info("CryptoAPIs Response Code: %s", response.status_code)
        _logger.info("CryptoAPIs Response Body: %s", response.text)

        if response.status_code not in (200, 201):
            raise UserError(_("Event creation failed: %s") % response.text)

        event_data = (response.json() or {}).get('data', {}).get('item', {}) or {}

        # ✅ Store event record (avoid duplicates if you want: search first by tx/address/event_type)
        self.env['crypto.wallet.address.event'].sudo().create({
            "address_id": self.id,
            "callback_secretkey": event_data.get("callbackSecretKey") or str(secret_token),
            "name": event_data.get("callbackUrl") or callback_url,
            "created_timestamp": datetime.utcfromtimestamp(event_data.get('createdTimestamp'))
            if event_data.get('createdTimestamp') else False,
            "event_type": event_data.get("eventType"),
            "active": event_data.get("isActive"),
            "reference_id": event_data.get("referenceId"),
            # (اختياري) احفظ tx_id عندك في event model لو عندك field
            # "payment_transaction_id": int(tx_id),
        })

        return event_data

    def get_events(self):


            for record in self:
                total_items = 100000
                max_count = 500
                count = 0
                times = 0
                limit = 50
                while count < total_items and count < max_count:
                    time.sleep(2)
                    offset = times * limit
                    blockchain = record.wallet_id.blockchain_id.name.lower()
                    network = record.wallet_id.network_id.name.lower().replace('testnet', "").replace(blockchain, "").replace(
                        " ", "")
                    address = record.name
                    url = f"https://rest.cryptoapis.io/blockchain-events/{blockchain}/{network}?context=list_event_odoo&limit=50&offset=" + str(offset)
                    headers = {
                        "X-API-Key": record.wallet_id.payment_provider_id.cryptoapis_api_key
                    }
                    response = requests.get(url, headers=headers)
                    if response.status_code != 200:
                        raise Exception(f"Failed to fetch crypto transactions: {response.text}")
                    _logger.info('response' + str(response))
                    data = response.json().get("data", [])
                    _logger.info('response Json Data' + str(data))
                    items = data.get("items", [])
                    if len(items) <= 0:
                        break;
                    event_obj = self.env['crypto.wallet.address.event']
                    for item in items:
                        count = count + 1
                        is_Exist = event_obj.search([('reference_id', '=', item.get('referenceId'))])
                        if not is_Exist:
                            address_id = self.env['crypto.wallet.address'].search([('name','=',item.get("address"))])
                            event_id = event_obj.create({
                                'address_id': address_id.id,
                                "callback_secretkey": item.get("callbackSecretKey"),
                                "name": item.get("callbackUrl"),
                                "confirmations_count": item.get("confirmationsCount"),
                                "created_timestamp": datetime.utcfromtimestamp(data.get('createdTimestamp')) if data.get(
                                    'createdTimestamp') else False,

                                "event_type": item.get("eventType"),
                                "active": item.get("isActive"),
                                "reference_id": item.get("referenceId"),

                            })
                    times = times + 1

