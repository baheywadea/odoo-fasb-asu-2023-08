from odoo import models, fields, api
import logging
# from odoo.addons.crypto_payment_sync.const import SUPPORTED_CURRENCIES
import requests
import time
import datetime
from odoo.exceptions import UserError
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class CryptoPaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(selection_add=[("crypto", "Crypto Payment")], ondelete={"crypto": "cascade"})
    # crypto_wallet_address = fields.Char(string="Company Wallet Address")
    cryptoapis_api_key = fields.Char(string="API KEY", help="API KEY")
    cryptoapis_api_key_masked = fields.Char(
        string="Masked API Key",
        compute="_compute_cryptoapis_api_key_masked",
    )
    payment_provider_id_crypto_wallet_count = fields.Integer(compute="_compute_crypto_wallet_count", store=True)
    provider_id_payment_transaction_count = fields.Integer(compute="_compute_crypto_transaction_count", store=True)

    def _compute_cryptoapis_api_key_masked(self):
        for record in self:
            api_key = record.cryptoapis_api_key or ""
            if not api_key:
                record.cryptoapis_api_key_masked = ""
            elif len(api_key) <= 8:
                record.cryptoapis_api_key_masked = "****"
            else:
                record.cryptoapis_api_key_masked = f"{api_key[:4]}...{api_key[-4:]}"

    def _compute_crypto_wallet_count(self):
        for record in self:
            record['payment_provider_id_crypto_wallet_count'] = self.env['crypto.wallet'].search_count(
                [('payment_provider_id', '=', record.id)])

    def _compute_crypto_transaction_count(self):
        for record in self:
            record['provider_id_payment_transaction_count'] = self.env['payment.transaction'].search_count(
                [('provider_id', '=', record.id)])

    def _get_default_payment_method_id(self, code):
        self.ensure_one()
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'crypto':
            return default_codes
        return self.env.ref('crypto_payment_sync.account_payment_method_crypto').id

    def _crypto_get_api_url(self):
        """ Return the API URL according to the state """
        self.ensure_one()
        if self.state == 'enabled':
            return 'https://rest.cryptoapis.io/'
        else:
            return 'https://rest.cryptoapis.io/'

    def sync_crypto_currencies(self):
        for rec in self:
            total_items = 100000
            max_count = 200
            count = 0
            times = 0
            limit = 50
            while count < total_items and count < max_count:
                time.sleep(2)
                offset = times * limit
                url = "https://rest.cryptoapis.io/market-data/metadata/assets?context=Odoo&limit=50&offset=" + str(
                    offset) + "&type=crypto"
                headers = {
                    "X-API-Key": rec.cryptoapis_api_key
                }
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
                    symbol = asset.get("symbol")
                    name = asset.get("name")
                    referenceid = asset.get("referenceId")
                    crypto_by_name = self.env['res.currency'].search([('name', '=', name.upper())])
                    if len(crypto_by_name) <= 0:
                        self.env['res.currency'].create({
                            'full_name': name.upper(),
                            'name': name.upper(),
                            'symbol': symbol.upper(),
                            'currency_unit_label': symbol,
                            'currency_subunit_label': symbol,
                            'rounding': 0.00000001,  # Adjust as needed
                            'active': True,
                            'type': 'crypto',
                            'cryptoapis_referenceId': referenceid,
                        })
                    if crypto_by_name:
                        crypto_by_name.write({'cryptoapis_referenceId': referenceid})
                times = times + 1

    def sync_fiat_currencies(self):
        for rec in self:
            total_items = 100000;
            count = 0
            times = 0
            limit = 50
            while count < total_items:
                time.sleep(2)
                offset = times * limit
                url = "https://rest.cryptoapis.io/market-data/metadata/assets?context=Odoo&limit=50&offset=" + str(
                    offset) + "&type=fiat"
                headers = {
                    "X-API-Key": rec.cryptoapis_api_key
                }
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
                    symbol = asset.get("symbol")
                    name = asset.get("name")
                    referenceid = asset.get("referenceId")
                    crypto_by_name = self.env['res.currency'].search([('name', '=', symbol.upper())])
                    if len(crypto_by_name) <= 0:
                        self.env['res.currency'].create({
                            'full_name': name.upper(),
                            'name': name.upper(),
                            'symbol': symbol.upper(),
                            'currency_unit_label': symbol,
                            'currency_subunit_label': symbol,
                            'rounding': 0.00000001,  # Adjust as needed
                            'active': True,
                            'type': 'fiat',
                            'cryptoapis_referenceId': referenceid,
                        })
                    if crypto_by_name:
                        crypto_by_name.write({'cryptoapis_referenceId': referenceid})
                times = times + 1

    def sync_currencies_rate(self):

        calculation_timestamp = int(time.time())

        for rec in self:
            currencies = self.env['res.currency'].search(
                [('id', '!=', rec.company_id.currency_id.id), ('cryptoapis_referenceId', '!=', '')])
            for currency in currencies:
                # / market - data / exchange - rates / by - symbol / {fromAssetSymbol} / {toAssetSymbol}

                url = "https://rest.cryptoapis.io/market-data/exchange-rates/by-id/" + rec.company_id.currency_id.cryptoapis_referenceId + "/" + currency.cryptoapis_referenceId + "?context=OdooRates&calculationTimestamp=" + str(
                    calculation_timestamp)
                headers = {
                    "X-API-Key": rec.cryptoapis_api_key
                }
                response = requests.get(url, headers=headers)
                if response.status_code != 200:
                    raise Exception(f"Failed to fetch crypto currencies: {response.text}")
                _logger.info('response' + str(response))
                data = response.json().get("data", [])
                _logger.info('response Json Data' + str(data))
                rate = data.get("item", [])
                _logger.info('response Json assets' + str(rate))
                # for rate in rates:
                rate_val = rate.get("rate")
                calculationTimestamp = rate.get("calculationTimestamp")
                timestamp_int = int(calculationTimestamp)
                rate_date = datetime.datetime.utcfromtimestamp(timestamp_int).date()
                exist_rate_date = self.env['res.currency.rate'].search(
                    [('currency_id', '=', currency.id), ('name', '=', rate_date)])
                if not exist_rate_date:
                    self.env['res.currency.rate'].create(
                        {
                            'currency_id': currency.id,
                            'company_rate': rate_val,
                            'name': rate_date,
                        }
                    )
                else:
                    exist_rate_date.write({'company_rate': rate_val})

    def sync_wallets(self):
        for provider in self:
            blockchains = self.env['crypto.blockchain'].search([])

            for blockchain in blockchains:
                networks = self.env['crypto.network'].search([('blockchain_id','=',blockchain.id)])
                for network in networks:
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
                        url += "?context=list_hd_wallet_to_odoo&limit=50&offset=" + str(offset)

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
                                    'name': network.blockchain_id.name + ' - ' + network.name,
                                    'xpub': extendedPublicKey,
                                    'network_id': network.id,
                                    # 'blockchain_id': symbol,
                                    'payment_provider_id': provider.id,
                                    'active': True,
                                })
                            if wallet_by_name:
                                wallet_by_name.write({'xpub': extendedPublicKey})
                        times = times + 1
