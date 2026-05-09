from odoo import models, fields, api, _
import time
import datetime
from odoo.exceptions import UserError

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

    def _get_cryptoapis_provider(self):
        provider = self.env['payment.provider'].search([('code', '=', 'crypto')], limit=1)
        if not provider:
            raise UserError(_("Configure the Crypto payment provider before syncing Crypto APIs data."))
        provider._cryptoapis_headers()
        return provider

    def get_crypto_referenceid(self):
        provider = self._get_cryptoapis_provider()
        for rec in self:
            if not rec.cryptoapis_referenceId:
                symbol = rec.symbol or rec.name
                if not symbol:
                    continue
                data = provider._cryptoapis_get(
                    "market-data/assets/by-symbol/%s" % symbol,
                    params={"context": "OdooSyncCurrency"},
                ).get("data") or {}
                currency_data = data.get("item") or {}
                reference_id = currency_data.get("referenceId")
                if reference_id:
                    rec.write({'cryptoapis_referenceId': reference_id})

    def get_rate(self):
        calculation_timestamp = int(time.time())
        current_company = self.env.company
        provider = self._get_cryptoapis_provider()
        if not current_company.currency_id.cryptoapis_referenceId:
            raise UserError(_("Set a Crypto APIs reference ID on the company currency before syncing rates."))
        for currency in self:
            if not currency.cryptoapis_referenceId:
                continue
            data = provider._cryptoapis_get(
                "market-data/exchange-rates/by-id/%s/%s" % (
                    current_company.currency_id.cryptoapis_referenceId,
                    currency.cryptoapis_referenceId,
                ),
                params={
                    "context": "OdooRates",
                    "calculationTimestamp": calculation_timestamp,
                },
            ).get("data") or {}
            rate = data.get("item") or {}
            rate_val = rate.get("rate")
            calculationTimestamp = rate.get("calculationTimestamp")
            if not rate_val or not calculationTimestamp:
                continue
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
