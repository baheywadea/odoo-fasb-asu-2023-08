from odoo import models, fields, api, _
from odoo.exceptions import UserError
import time
from datetime import datetime, timedelta
from mnemonic import Mnemonic
from bip32 import BIP32


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

    def _compute_transactions_evm_count(self):
        TxEvm = self.env['crypto.transaction.evm']
        for record in self:
            record.transactions_evm_count = TxEvm.search_count([
                ('wallet_address_id.wallet_id', '=', record.id),
            ])

    @api.depends('wallet_address_ids')
    def _compute_wallet_address_count(self):
        for record in self:
            record['wallet_address_count'] = self.env['crypto.wallet.address'].search_count(
                [('wallet_id', '=', record.id)])

    @api.depends('network_id')
    def _compute_is_testnet(self):
        for record in self:
            record.is_testnet = 'test' in (record.network_id.name or '').lower()

    def _cryptoapis_path_parts(self):
        self.ensure_one()
        blockchain = self.blockchain_id.cryptoapis_slug or self.blockchain_id.technical_name or self.blockchain_id.name
        network = self.network_id.cryptoapis_network or self.network_id.technical_name or self.network_id.name
        blockchain = (blockchain or "").lower().strip()
        network = (network or "").lower().strip()
        if not blockchain or not network:
            raise UserError(_("Set Crypto APIs blockchain and network codes before calling Crypto APIs."))
        if self.network_id.is_evm_compatible or "ether" in blockchain or blockchain in ("ethereum", "polygon", "base"):
            family = "evm"
        elif "bitcoin" in blockchain:
            family = "utxo"
        else:
            family = None
        return family, blockchain, network

    def _cryptoapis_hd_wallet_path(self, suffix):
        self.ensure_one()
        family, blockchain, network = self._cryptoapis_path_parts()
        family_prefix = "%s/" % family if family else ""
        return f"hd-wallets/{family_prefix}{blockchain}/{network}/{self.xpub}/{suffix.lstrip('/')}"

    def action_generate_wallet_from_api(self):
        for rec in self:
            allow_generation = self.env['ir.config_parameter'].sudo().get_param(
                'crypto_payment_sync.allow_local_wallet_generation'
            ) == '1'
            if not allow_generation:
                raise UserError(_(
                    "Local mnemonic generation is disabled by default. Set "
                    "crypto_payment_sync.allow_local_wallet_generation to 1 only in an approved test workflow."
                ))
            provider = rec.payment_provider_id
            provider._cryptoapis_headers()

            # Step 1: Generate mnemonic
            mnemo = Mnemonic("english")
            mnemonic_words = mnemo.generate(strength=128)
            # Step 2: Generate seed from mnemonic
            seed = mnemo.to_seed(mnemonic_words)

            # Step 3: Derive xPub at path m/44'/60'/0'
            bip32 = BIP32.from_seed(seed)

            # Hardened path: m/44'/60'/0'
            purpose = 44 + 0x80000000
            coin = 60 + 0x80000000
            account = 0 + 0x80000000
            xpub = bip32.get_xpub_from_path([purpose, coin, account])

            _family, blockchain, network = rec._cryptoapis_path_parts()

            payload = {
                "context": "create_hd_wallet_from_odoo",
                "data": {
                    "item": {
                        # "walletName": rec.name
                    }
                }
            }
            wallet_data = provider._cryptoapis_post(
                f"hd-wallets/manage/{blockchain}/{network}/{xpub}/sync",
                payload=payload,
            ).get('data', {}).get('item', {})
            rec.write({
                # 'wallet_id': wallet_data.get('walletId'),
                'xpub': wallet_data.get('extendedPublicKey'),
                'mnemonic': mnemonic_words,
            })
            # self.message_post(body=_("Wallet created successfully from Crypto APIs."))

    def sync_addresses(self):
        total_created = 0
        total_existing = 0
        for rec in self:
            provider = rec.payment_provider_id
            provider._cryptoapis_headers()
            limit = provider._cryptoapis_page_size()
            max_pages = provider._cryptoapis_max_pages()
            family, _blockchain, _network = rec._cryptoapis_path_parts()
            address_format = "p2wpkh" if family == "utxo" else ("classic" if not family else "standard")
            address_obj = self.env['crypto.wallet.address']
            total_items = 100000
            count = 0
            page = 0
            while count < total_items and page < max_pages:
                time.sleep(provider._cryptoapis_request_delay())
                data = provider._cryptoapis_get(
                    rec._cryptoapis_hd_wallet_path("addresses"),
                    params={
                        "context": "list_synced_addresses_odoo",
                        "addressFormat": address_format,
                        "limit": limit,
                        "offset": page * limit,
                    },
                ).get('data', {})
                total_items = data.get('total') or total_items
                wallet_addresses = data.get('items') or []
                if not wallet_addresses:
                    break
                for address in wallet_addresses:
                    count += 1
                    address_val = address.get('address')
                    if not address_val:
                        continue
                    if not address_obj.search([('name', '=', address_val)], limit=1):
                        address_obj.create({'name': address_val, 'wallet_id': rec.id, 'index': address.get('index')})
                        total_created += 1
                    else:
                        total_existing += 1
                page += 1
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Crypto Wallet Address Sync"),
                "message": _("Address sync completed. Created %s address(es), skipped %s existing address(es).") % (
                    total_created,
                    total_existing,
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def get_balance(self):
        for record in self:
            # Calculate the difference
            if record.last_synced_balance:
                time_diff = datetime.now() - record.last_synced_balance
            else:
                time_diff = timedelta(hours=1)
            # Check if more than one minute
            if time_diff.total_seconds() > 60:
                extendedPublicKey = record.xpub
                if not extendedPublicKey:
                    raise UserError(_("Set the wallet XPUB before syncing wallet balance."))
                item = record.payment_provider_id._cryptoapis_get(
                    record._cryptoapis_hd_wallet_path("details"),
                    params={"context": "OdooGetWalletDetails"},
                ).get("data", {}).get("item", {})
                confirmedBalance = item.get("confirmedBalance")
                totalReceived = item.get("totalReceived")
                totalSpent = item.get("totalSpent")
                record.write({'confirmed_balance': confirmedBalance,
                              'total_received': totalReceived,
                              'total_spent': totalSpent,
                              'last_synced_balance': fields.Datetime.now()})

    def get_confirmed_transactions(self):

        for record in self:
            data = record.payment_provider_id._cryptoapis_get(
                record._cryptoapis_hd_wallet_path("transactions"),
                params={"context": "OdooGetWalletTransactions"},
            ).get("data", {})
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
            provider = rec.payment_provider_id
            provider._cryptoapis_headers()

            payload = {
                "context": "OdooDeriveNewAddresses",
                "data": {
                    "item": {
                        # "walletName": rec.name
                    }
                }
            }

            wallet_addresses = provider._cryptoapis_post(
                rec._cryptoapis_hd_wallet_path("addresses/derive-and-sync"),
                payload=payload,
                params={"context": "OdooDeriveNewAddresses"},
            ).get('data', {}).get('items', [])
            address_obj = self.env['crypto.wallet.address']
            if len(wallet_addresses) <= 0:
                break
            for address in wallet_addresses:
                # count = count + 1
                address_val = address.get('address')
                address_exist = address_obj.search([('name', '=', address_val)])
                if not address_exist:
                    address_obj.create({'name': address_val, 'wallet_id': rec.id, 'index': address.get(
                        'index')})
