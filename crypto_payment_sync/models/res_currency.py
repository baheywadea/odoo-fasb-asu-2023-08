from odoo import models, fields, api
import logging
# from odoo.addons.crypto_payment_sync.const import SUPPORTED_CURRENCIES
import requests
import time
import datetime

_logger = logging.getLogger(__name__)

class ResCurrency(models.Model):
    _inherit = "res.currency"

    name = fields.Char(string='Currency', size=50, required=True, help="Currency Code (ISO 4217)")
    type = fields.Selection([('crypto', 'crypto'), ('fiat', 'fiat')], string="Type", default="fiat",
                            help="Type Crypto or Fiat")
    cryptoapis_referenceId = fields.Char(string="Cryptoapis Reference", help="Cryptoapis Reference", ondelete="cascade")
    is_crypto = fields.Boolean(compute="_compute_is_crypto", store=True)
    rounding = fields.Float(string='Rounding Factor', digits=(12, 12), default=0.00000001,
                            help='Amounts in this currency are rounded off to the nearest multiple of the rounding factor.')

    @api.depends('type')
    def _compute_is_crypto(self):
        for rec in self:
            rec.is_crypto = rec.type == 'crypto'

    def get_crypto_referenceid(self):
        for rec in self:
            if not rec.cryptoapis_referenceId:
                provider = self.env['payment.provider'].search([('code', '=', 'crypto')])
                if provider and provider[0].cryptoapis_api_key:
                    url = "https://rest.cryptoapis.io/market-data/assets/by-symbol/" + rec.symbol + "?context=OdooSyncCurrency"
                    headers = {
                        "X-API-Key": provider[0].cryptoapis_api_key
                    }
                    response = requests.get(url, headers=headers)
                    if response.status_code != 200:
                        raise Exception(f"Failed to fetch crypto currencies: {response.text}")
                    _logger.info('response' + str(response))
                    data = response.json().get("data", [])
                    _logger.info('response Json Data' + str(data))
                    currency_data = data.get("item", [])
                    referenceId = currency_data.get("referenceId")
                    rec.write({'cryptoapis_referenceId': referenceId})

    def get_rate(self):
        calculation_timestamp = int(time.time())
        current_company = self.env.company
        for currency in self:
            provider = self.env['payment.provider'].search([('code', '=', 'crypto')])
            # / market - data / exchange - rates / by - symbol / {fromAssetSymbol} / {toAssetSymbol}
            if provider and provider[0].cryptoapis_api_key:
                url = "https://rest.cryptoapis.io/market-data/exchange-rates/by-id/" + current_company.currency_id.cryptoapis_referenceId + "/" + currency.cryptoapis_referenceId + "?context=OdooRates&calculationTimestamp=" + str(
                    calculation_timestamp)
                headers = {
                    "X-API-Key": provider[0].cryptoapis_api_key
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
