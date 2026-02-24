from odoo import models, fields, api


class CryptoBlockchain(models.Model):
    _name = 'crypto.blockchain'
    _description = 'Blockchain'

    name = fields.Char(string="Name", required=True)
    technical_name = fields.Char(string="Technical Name", required=True)
    symbol = fields.Char(string="Symbol", required=True)
    network_type = fields.Char(string="Network Type", required=True)
    explorer_url = fields.Char(string="Explorer URL", required=True)
    active = fields.Boolean(default=True)
