import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
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
        counts = {
            row['wallet_address_id'][0]: row['wallet_address_id_count']
            for row in self.env['crypto.transaction.evm'].read_group(
                [('wallet_address_id', 'in', self.ids)],
                ['wallet_address_id'],
                ['wallet_address_id'],
            )
            if row.get('wallet_address_id')
        }
        for record in self:
            record.transactions_evm_count = counts.get(record.id, 0)

    @api.depends('event_ids')
    def _compute_events_count(self):
        counts = {
            row['address_id'][0]: row['address_id_count']
            for row in self.env['crypto.wallet.address.event'].read_group(
                [('address_id', 'in', self.ids)],
                ['address_id'],
                ['address_id'],
            )
            if row.get('address_id')
        }
        for record in self:
            record.events_count = counts.get(record.id, 0)

    def action_view_transactions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Address Transactions'),
            'res_model': 'crypto.transaction.evm',
            'view_mode': 'list,form',
            'domain': [('wallet_address_id', '=', self.id)],
            'context': {'default_wallet_address_id': self.id},
        }

    def action_view_events(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Address Events'),
            'res_model': 'crypto.wallet.address.event',
            'view_mode': 'list,form',
            'domain': [('address_id', '=', self.id)],
            'context': {'default_address_id': self.id},
        }

    def _cryptoapis_path_parts(self):
        self.ensure_one()
        return self.wallet_id._cryptoapis_path_parts()

    def _cryptoapis_address_latest_path(self, suffix):
        self.ensure_one()
        family, blockchain, network = self._cryptoapis_path_parts()
        family_prefix = "%s/" % family if family else ""
        return f"addresses-latest/{family_prefix}{blockchain}/{network}/{self.name}/{suffix.lstrip('/')}"

    def _cryptoapis_blockchain_events_path(self, suffix=""):
        self.ensure_one()
        _family, blockchain, network = self._cryptoapis_path_parts()
        suffix = suffix.strip("/")
        path = f"blockchain-events/{blockchain}/{network}"
        return f"{path}/{suffix}" if suffix else path

    def get_balance(self):

        for record in self:
            # Calculate the difference
            if record.last_synced_balance:
                time_diff = datetime.now() - record.last_synced_balance
            else:
                time_diff = timedelta(hours=1)
            # Check if more than one minute
            if time_diff.total_seconds() > 60:
                item = record.wallet_id.payment_provider_id._cryptoapis_get(
                    record._cryptoapis_address_latest_path("balance"),
                    params={"context": "OdooGetAddressBalance"},
                ).get("data", {}).get("item", {})
                confirmedBalance = item.get("confirmedBalance", [])
                amount = confirmedBalance.get("amount")
                record.write({'confirmed_balance': amount, 'last_synced_balance': fields.Datetime.now()})

    def get_confirmed_transactions(self):

        for record in self:
            data = record.wallet_id.payment_provider_id._cryptoapis_get(
                record._cryptoapis_address_latest_path("transactions"),
                params={
                    "context": "OdooEVMGetConfirmedTransactions",
                    "limit": record.wallet_id.payment_provider_id._cryptoapis_page_size(),
                    "sortingOrder": "descending",
                },
            ).get("data", {})
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
                website = request.env['website'].get_current_website()
                odoo_base_url = website.domain or request.env['ir.config_parameter'].sudo().get_param('web.base.url')

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
                event_data = rec.wallet_id.payment_provider_id._cryptoapis_post(
                    rec._cryptoapis_blockchain_events_path("address-coins-transactions-confirmed"),
                    payload=payload,
                ).get('data', {}).get('item', {})
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

        provider = self.wallet_id.payment_provider_id
        provider._cryptoapis_headers()

        # Use Odoo's configured base URL for the webhook callback target.
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
        base_url = base_url.rstrip('/')

        # Ensure address is a string.
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
                    "callbackSecretKey": str(secret_token),
                    "callbackUrl": callback_url,
                    "receiveCallbackOn": 3
                }
            }
        }

        event_data = provider._cryptoapis_post(
            self._cryptoapis_blockchain_events_path("address-coins-transactions-confirmed"),
            payload=payload,
        ).get('data', {}).get('item', {}) or {}

        # Store the returned event reference without logging callback secrets.
        self.env['crypto.wallet.address.event'].sudo().create({
            "address_id": self.id,
            "callback_secretkey": event_data.get("callbackSecretKey") or str(secret_token),
            "name": event_data.get("callbackUrl") or callback_url,
            "created_timestamp": datetime.utcfromtimestamp(event_data.get('createdTimestamp'))
            if event_data.get('createdTimestamp') else False,
            "event_type": event_data.get("eventType"),
            "active": event_data.get("isActive"),
            "reference_id": event_data.get("referenceId"),
            # "payment_transaction_id": int(tx_id),
        })

        return event_data

    def get_events(self):
        for record in self:
            provider = record.wallet_id.payment_provider_id
            limit = provider._cryptoapis_page_size()
            max_pages = provider._cryptoapis_max_pages()
            event_obj = self.env['crypto.wallet.address.event']
            total_items = 100000
            count = 0
            page = 0
            while count < total_items and page < max_pages:
                time.sleep(provider._cryptoapis_request_delay())
                data = provider._cryptoapis_get(
                    record._cryptoapis_blockchain_events_path(),
                    params={
                        "context": "list_event_odoo",
                        "limit": limit,
                        "offset": page * limit,
                    },
                ).get("data", {})
                total_items = data.get("total") or total_items
                items = data.get("items") or []
                if not items:
                    break
                for item in items:
                    count += 1
                    if event_obj.search([('reference_id', '=', item.get('referenceId'))], limit=1):
                        continue
                    address_id = self.env['crypto.wallet.address'].search(
                        [('name', '=', item.get("address"))], limit=1)
                    if not address_id:
                        _logger.warning(
                            "get_events: no address in Odoo for %s, skipping event %s",
                            item.get("address"), item.get("referenceId"))
                        continue
                    event_obj.create({
                        'address_id': address_id.id,
                        'callback_secretkey': item.get("callbackSecretKey"),
                        'name': item.get("callbackUrl") or "/",
                        'confirmations_count': item.get("confirmationsCount"),
                        'created_timestamp': datetime.utcfromtimestamp(item.get('createdTimestamp'))
                        if item.get('createdTimestamp') else False,
                        'event_type': item.get("eventType"),
                        'active': item.get("isActive"),
                        'reference_id': item.get("referenceId"),
                    })
                page += 1
