from odoo import models, fields, api, _
import logging
import time
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
        skipped = []
        synced_wallets = 0
        for network in self:
            provider = self.env['payment.provider'].search([('code', '=', 'crypto')], limit=1)
            if provider:
                if not provider.cryptoapis_api_key:
                    raise UserError(_("Set a Crypto APIs API key before syncing wallets."))
                total_items = 100000
                count = 0
                page = 0
                limit = provider._cryptoapis_page_size()
                while count < total_items and page < provider._cryptoapis_max_pages():
                    time.sleep(provider._cryptoapis_request_delay())
                    offset = page * limit
                    blockchain_slug = network.blockchain_id.cryptoapis_slug or network.blockchain_id.technical_name
                    network_slug = network.cryptoapis_network or network.technical_name
                    try:
                        data = provider._cryptoapis_get(
                            f"hd-wallets/manage/{blockchain_slug}/{network_slug}",
                            params={
                                "context": "list_hd_wallet_to_odoo",
                                "limit": limit,
                                "offset": offset,
                            },
                        ).get("data") or {}
                    except UserError as exc:
                        skipped.append(f"{network.blockchain_id.name} / {network.name}")
                        _logger.warning(
                            "Skipping Crypto APIs wallet sync for %s / %s: %s",
                            network.blockchain_id.name,
                            network.name,
                            exc,
                        )
                        break
                    total_items = data.get("total") or 0
                    assets = data.get("items", [])
                    if not assets:
                        break
                    for asset in assets:
                        count = count + 1
                        extendedPublicKey = asset.get("extendedPublicKey")
                        if not extendedPublicKey:
                            continue
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
                            synced_wallets += 1
                        if wallet_by_name:
                            wallet_by_name.write({'xpub': extendedPublicKey})
                    page = page + 1
        message = _("Wallet sync completed. Created %s wallet(s).") % synced_wallets
        if skipped:
            message += _(" Skipped %s unsupported or unavailable network(s).") % len(skipped)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Crypto APIs Wallet Sync"),
                "message": message,
                "type": "warning" if skipped else "success",
                "sticky": bool(skipped),
            },
        }
