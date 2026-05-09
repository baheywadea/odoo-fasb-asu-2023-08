from odoo import models, fields, api,_
import logging
# from odoo.addons.crypto_payment_sync.const import SUPPORTED_CURRENCIES
import requests
import time
import datetime
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)


class CryptoNetwork(models.Model):
    _name = 'crypto.network'
    _description = 'Blockchain Network'

    name = fields.Char(string="Network Name", required=True)  # e.g. mainnet, sepolia
    technical_name = fields.Char(string="Technical Name", required=True)
    cryptoapis_network = fields.Char(string="Crypto APIs Network")
    chain_id = fields.Integer(string="Chain ID", required=True)
    is_testnet = fields.Boolean(string="Is Testnet")
    is_evm_compatible = fields.Boolean(string="EVM Compatible")
    native_asset_symbol = fields.Char(string="Native Asset Symbol")
    rpc_url = fields.Char(string="RPC URL", required=True)
    explorer_url = fields.Char(string="Explorer URL")
    # currency_code = fields.Char(string="Currency Code", required=True)
    blockchain_id = fields.Many2one('crypto.blockchain', string="Blockchain", required=True)
    active = fields.Boolean(default=True)

    def sync_wallets(self):
        for network in self:
            provider = self.env['payment.provider'].search([('code', '=', 'crypto')])
            if provider:
                total_items = 100000;
                count = 0
                times = 0
                limit = 50
                while count < total_items:
                    time.sleep(2)
                    offset = times * limit
                    # CryptoAPIs endpoint to derive address from xpub

                    url = f"https://rest.cryptoapis.io/hd-wallets/manage/{network.blockchain_id.technical_name}/{network.technical_name}"

                    headers = {
                        "Content-Type": "application/json",
                        "X-API-Key": provider.cryptoapis_api_key
                    }
                    url +="?context=list_hd_wallet_to_odoo&limit=50&offset="+str(offset)


                    response = requests.get(url, headers=headers)
                    if response.status_code != 200:
                        raise Exception(f"Failed to fetch crypto currencies: {response.text}")
                    _logger.info('response' + str(response))
                    data = response.json().get("data", [])
                    total_items = data.get("total")
                    _logger.info('response Json Data' + str(data))
                    assets = data.get("items", [])
                    _logger.info('response Json assets' + str(assets))
                    for asset in assets:
                        count = count + 1
                        extendedPublicKey = asset.get("extendedPublicKey")
                        # name = asset.get("name")
                        # referenceid = asset.get("referenceId")
                        wallet_by_name = self.env['crypto.wallet'].search([('xpub', '=', extendedPublicKey)])
                        if len(wallet_by_name) <= 0:
                            self.env['crypto.wallet'].create({
                                'name': network.blockchain_id.name + ' - '+network.name,
                                'xpub': extendedPublicKey,
                                'network_id': network.id,
                                # 'blockchain_id': symbol,
                                'payment_provider_id': provider.id,
                                'active': True,
                            })
                        if wallet_by_name:
                            wallet_by_name.write({'xpub': extendedPublicKey})
                    times = times + 1
