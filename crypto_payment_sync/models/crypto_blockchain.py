from odoo import models, fields, api


class CryptoBlockchain(models.Model):
    _name = 'crypto.blockchain'
    _description = 'Blockchain'

    name = fields.Char(string="Name", required=True)
    technical_name = fields.Char(string="Technical Name", required=True)
    cryptoapis_slug = fields.Char(string="Crypto APIs Slug")
    symbol = fields.Char(string="Symbol", required=True)
    native_asset_symbol = fields.Char(string="Native Asset Symbol")
    network_type = fields.Char(string="Network Type", required=True)
    explorer_url = fields.Char(string="Explorer URL", required=True)
    is_evm_compatible = fields.Boolean(string="EVM Compatible")
    active = fields.Boolean(default=True)
