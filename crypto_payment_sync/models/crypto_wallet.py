import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import time
from datetime import datetime, timedelta
from mnemonic import Mnemonic
from bip32 import BIP32
import hashlib

_logger = logging.getLogger(__name__)


class CryptoWallet(models.Model):
    _name = 'crypto.wallet'
    _description = 'Crypto Wallet'

    name = fields.Char(string="Wallet Name", required=True)

    network_id = fields.Many2one('crypto.network', string="Network", required=True)

    blockchain_id = fields.Many2one('crypto.blockchain', related="network_id.blockchain_id", string="Blockchain")

    currency_id = fields.Many2one('res.currency', string="Currency", domain=[('type', '=', 'crypto')])

    wallet_id = fields.Char(string="CryptoAPIs Wallet ID")

    deposit_address = fields.Char(string="Deposit Address")

    payment_provider_id = fields.Many2one('payment.provider', string="Payment Provider",
                                          domain=[('code', '=', 'crypto')], required=True)

    is_default = fields.Boolean(string="Is Default",
                                help="Use this wallet for receiving payments for the selected currency.")

    xpub = fields.Char(string="XPUB (if HD wallet)")

    mnemonic = fields.Char(string="Mnemonic Seed (Encrypted)")  # Store the seed securely!

    active = fields.Boolean(default=True)

    is_testnet = fields.Boolean(compute='_compute_is_testnet', store=True)

    wallet_address_count = fields.Integer(compute="_compute_wallet_address_count", store=False)

    confirmed_balance = fields.Float(string="ConfirmedBalance")

    total_received = fields.Float(string="totalReceived")

    total_spent = fields.Float(string="totalSpent")

    last_synced_balance = fields.Datetime(string="Last Synced Time")

    wallet_address_ids = fields.One2many('crypto.wallet.address', 'wallet_id', string="Wallet Addresses")

    transactions_evm_count = fields.Integer(compute="_compute_transactions_evm_count", store=False)

    transaction_evm_ids = fields.One2many('crypto.transaction.evm', 'wallet_id', string="Wallet Addresses")

    company_id = fields.Many2one("res.company", string="Company")

    _sql_constraints = [
        ('xpub_uniq', 'unique (xpub)', 'The xpub Key must be unique!')
    ]

    @api.depends('transaction_evm_ids')
    def _compute_transactions_evm_count(self):
        for record in self:
            record['transactions_evm_count'] = len(record.transaction_evm_ids)

    @api.depends('wallet_address_ids')
    def _compute_wallet_address_count(self):
        for record in self:
            record['wallet_address_count'] = self.env['crypto.wallet.address'].search_count(
                [('wallet_id', '=', record.id)])

    @api.depends('network_id')
    def _compute_is_testnet(self):
        for record in self:
            record.is_testnet = 'test' in (record.network_id.name or '').lower()

    def action_generate_wallet_from_api(self):
        for rec in self:
            api_key = rec.payment_provider_id.cryptoapis_api_key
            if not api_key:
                raise UserError(
                    _("Crypto API Key not configured. Set it in System Parameters with key: crypto_api.key"))

            # Step 1: Generate mnemonic
            mnemo = Mnemonic("english")
            mnemonic_words = mnemo.generate(strength=128)
            print("🔐 Mnemonic:", mnemonic_words)

            # Step 2: Generate seed from mnemonic
            seed = mnemo.to_seed(mnemonic_words)

            # Step 3: Derive xPub at path m/44'/60'/0'
            bip32 = BIP32.from_seed(seed)

            # Hardened path: m/44'/60'/0'
            purpose = 44 + 0x80000000
            coin = 60 + 0x80000000
            account = 0 + 0x80000000
            xpub = bip32.get_xpub_from_path([purpose, coin, account])

            print("🔑 xPub:", xpub)

            # === 2. Use Crypto APIs to Get Address ===

            blockchain = self.blockchain_id.name.lower()
            network = self.network_id.name.lower().replace(" ", "-").replace(blockchain, "").replace("testnet",
                                                                                                     "").replace("-",
                                                                                                                 "")

            # CryptoAPIs endpoint to derive address from xpub

            url = f"https://rest.cryptoapis.io/hd-wallets/manage/{blockchain}/{network}/{xpub}/sync"

            headers = {
                "Content-Type": "application/json",
                "X-API-Key": api_key
            }

            payload = {
                "context": "create_hd_wallet_from_odoo",
                "data": {
                    "item": {
                        # "walletName": rec.name
                    }
                }
            }
            _logger.info('Reuested URL' + str(url))
            response = requests.post(url, json=payload, headers=headers)
            _logger.info('Response Statuse Code' + str(response.status_code))
            if response.status_code != 200:
                raise UserError(_("Wallet creation failed: %s") % response.text)

            wallet_data = response.json().get('data', {}).get('item', {})
            _logger.info('Response wallet_data ' + str(wallet_data))
            rec.write({
                # 'wallet_id': wallet_data.get('walletId'),
                'xpub': wallet_data.get('extendedPublicKey'),
                'mnemonic': mnemonic_words,
            })
            # self.message_post(body=_("Wallet created successfully from Crypto APIs."))

    def sync_addresses(self):
        for rec in self:
            api_key = rec.payment_provider_id.cryptoapis_api_key
            if not api_key:
                raise UserError(
                    _("Crypto API Key not configured. Set it in System Parameters with key: crypto_api.key"))
            total_items = 100000
            max_count = 500
            count = 0
            times = 0
            limit = 50
            while count < total_items and count < max_count:
                time.sleep(2)
                offset = times * limit
                blockchain = self.blockchain_id.name.lower()
                network = self.network_id.name.lower().replace('testnet', "").replace(blockchain, "").replace(" ", "")
                if 'ether' in blockchain:
                    url = f"https://rest.cryptoapis.io/hd-wallets/evm/{blockchain}/{network}/{rec.xpub}/addresses" \
                          f"?context=list_synced_addresses_odoo&addressFormat=standard&isChangeAddress=0&limit=50&offset=" + str(
                        offset)
                if 'bitcoin' in blockchain:
                    url = f"https://rest.cryptoapis.io/hd-wallets/utxo/{blockchain}/{network}/{rec.xpub}/addresses" \
                          f"?context=list_synced_addresses_odoo&addressFormat=p2wpkh&isChangeAddress=0&limit=50&offset=" + str(
                        offset)
                if 'xrp' in blockchain:
                    url = f"https://rest.cryptoapis.io/hd-wallets/{blockchain}/{network}/{rec.xpub}/addresses" \
                          f"?context=list_synced_addresses_odoo&addressFormat=classic&isChangeAddress=0&limit=50&offset=" + str(
                        offset)

                headers = {
                    "Content-Type": "application/json",
                    "X-API-Key": api_key
                }

                _logger.info('Reuested URL' + str(url))
                response = requests.get(url, headers=headers)
                _logger.info('Response Statuse Code' + str(response.status_code))
                if response.status_code != 200:
                    raise UserError(_("Wallet Sync Addresses failed: %s") % response.text)

                wallet_addresses = response.json().get('data', {}).get('items', {})
                _logger.info('Response wallet_data ' + str(wallet_addresses))
                address_obj = self.env['crypto.wallet.address']
                if len(wallet_addresses) <= 0:
                    break;
                for address in wallet_addresses:
                    count = count + 1
                    address_val = address.get('address')
                    address_exist = address_obj.search([('name', '=', address_val)])
                    if not address_exist:
                        address_obj.create({'name': address_val, 'wallet_id': rec.id, 'index': address.get(
                            'index')})
                times = times + 1

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
                blockchain = record.blockchain_id.name.lower()
                network = record.network_id.name.lower().replace('testnet', "").replace(blockchain, "").replace(" ", "")
                extendedPublicKey = record.xpub
                if 'ether' in blockchain:
                    url = f"https://rest.cryptoapis.io/hd-wallets/evm/{blockchain}/{network}/{extendedPublicKey}/details?context=OdooGetWalletDetails"
                if 'bitcoin' in blockchain:
                    url = f"https://rest.cryptoapis.io/hd-wallets/utxo/{blockchain}/{network}/{extendedPublicKey}/details?context=OdooGetWalletDetails"
                if 'xrp' in blockchain:
                    url = f"https://rest.cryptoapis.io/hd-wallets/{blockchain}/{network}/{extendedPublicKey}/details?context=OdooGetWalletDetails"

                headers = {
                    "X-API-Key": record.payment_provider_id.cryptoapis_api_key
                }
                response = requests.get(url, headers=headers)
                if response.status_code != 200:
                    raise Exception(f"Failed to fetch crypto currencies: {response.text}")
                _logger.info('response' + str(response))
                data = response.json().get("data", [])
                _logger.info('response Json Data' + str(data))
                item = data.get("item", [])
                _logger.info('response Json Item' + str(item))
                confirmedBalance = item.get("confirmedBalance")
                totalReceived = item.get("totalReceived")
                totalSpent = item.get("totalSpent")
                record.write({'confirmed_balance': confirmedBalance,
                              'total_received': totalReceived,
                              'total_spent': totalSpent,
                              'last_synced_balance': fields.Datetime.now()})

    def get_confirmed_transactions(self):

        for record in self:
            blockchain = record.blockchain_id.name.lower()
            network = record.network_id.name.lower().replace('testnet', "").replace(blockchain, "").replace(
                " ", "")
            address = record.name

            if 'ether' in blockchain:
                url = f"https://rest.cryptoapis.io/hd-wallets/evm/{blockchain}/{network}/{record.xpub}/transactions?context=OdooGetWalletTransactions"
            if 'bitcoin' in blockchain:
                url = f"https://rest.cryptoapis.io/hd-wallets/utxo/{blockchain}/{network}/{record.xpub}/transactions?context=OdooGetWalletTransactions"
            if 'xrp' in blockchain:
                url = f"https://rest.cryptoapis.io/hd-wallets/{blockchain}/{network}/{record.xpub}/transactions?context=OdooGetWalletTransactions"

            headers = {
                "X-API-Key": record.payment_provider_id.cryptoapis_api_key
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
                    trx_id = transaction_obj.create_from_wallet_json(item)
                    wallet_address = self.env['crypto.wallet.address'].search([('name', '=', trx_id.recipient)])
                    if len(wallet_address) <= 0:
                        wallet_address = self.env['crypto.wallet.address'].search([('name', '=', trx_id.sender)])
                    if len(wallet_address) > 0:
                        trx_id.write({'wallet_address_id': wallet_address[0].id})

    def derive_new_addresses(self):
        for rec in self:
            api_key = rec.payment_provider_id.cryptoapis_api_key
            if not api_key:
                raise UserError(
                    _("Crypto API Key not configured. Set it in System Parameters with key: crypto_api.key"))

            blockchain = self.blockchain_id.name.lower()
            network = self.network_id.name.lower().replace('testnet', "").replace(blockchain, "").replace(" ", "")
            if 'ether' in blockchain:
                url = f"https://rest.cryptoapis.io/hd-wallets/evm/{blockchain}/{network}/{rec.xpub}/addresses/derive-and-sync?context=OdooDeriveNewAddresses"
            if 'bitcoin' in blockchain:
                url = f"https://rest.cryptoapis.io/hd-wallets/utxo/{blockchain}/{network}/{rec.xpub}/addresses/derive-and-sync?context=OdooDeriveNewAddresses"
            if 'xrp' in blockchain:
                url = f"https://rest.cryptoapis.io/hd-wallets/{blockchain}/{network}/{rec.xpub}/addresses/derive-and-sync?context=OdooDeriveNewAddresses"

            headers = {
                "Content-Type": "application/json",
                "X-API-Key": api_key
            }

            payload = {
                "context": "OdooDeriveNewAddresses",
                "data": {
                    "item": {
                        # "walletName": rec.name
                    }
                }
            }

            _logger.info('Reuested URL' + str(url))
            response = requests.post(url, json=payload, headers=headers)
            _logger.info('Response Statuse Code' + str(response.status_code))
            if response.status_code != 200:
                raise UserError(_("Wallet Sync Addresses failed: %s") % response.text)

            wallet_addresses = response.json().get('data', {}).get('items', {})
            _logger.info('Response wallet_data ' + str(wallet_addresses))
            address_obj = self.env['crypto.wallet.address']
            if len(wallet_addresses) <= 0:
                break;
            for address in wallet_addresses:
                # count = count + 1
                address_val = address.get('address')
                address_exist = address_obj.search([('name', '=', address_val)])
                if not address_exist:
                    address_obj.create({'name': address_val, 'wallet_id': rec.id, 'index': address.get(
                        'index')})
