import logging
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
    payment_provider_id_crypto_wallet_count = fields.Integer(compute="_compute_crypto_wallet_count")
    provider_id_payment_transaction_count = fields.Integer(compute="_compute_crypto_transaction_count")
    cryptoapis_page_size = fields.Integer(
        string="Crypto APIs Page Size",
        compute="_compute_cryptoapis_usage_config",
        inverse="_inverse_cryptoapis_usage_config",
        readonly=False,
        help="Maximum records requested per API page. Keep this modest for paid accounts.",
    )
    cryptoapis_max_pages = fields.Integer(
        string="Crypto APIs Max Pages",
        compute="_compute_cryptoapis_usage_config",
        inverse="_inverse_cryptoapis_usage_config",
        readonly=False,
        help="Maximum pages requested by a manual sync action.",
    )
    cryptoapis_request_delay = fields.Float(
        string="Crypto APIs Request Delay",
        compute="_compute_cryptoapis_usage_config",
        inverse="_inverse_cryptoapis_usage_config",
        readonly=False,
        help="Delay in seconds between paginated API requests.",
    )
    cryptoapis_wallet_network_xmlids = fields.Char(
        string="Wallet Sync Network XML IDs",
        compute="_compute_cryptoapis_usage_config",
        inverse="_inverse_cryptoapis_usage_config",
        readonly=False,
        help="Comma-separated network XML IDs queried by List HD Wallets. Leave empty to prevent accidental broad paid API usage.",
    )
    cryptoapis_wallet_network_ids = fields.Many2many(
        "crypto.network",
        string="Wallet Sync Networks",
        compute="_compute_cryptoapis_usage_config",
        inverse="_inverse_cryptoapis_usage_config",
        readonly=False,
        help="Existing network records queried by List HD Wallets. Select only the networks you want to sync.",
    )

    def _compute_cryptoapis_api_key_masked(self):
        for record in self:
            api_key = record.cryptoapis_api_key or ""
            if not api_key:
                record.cryptoapis_api_key_masked = ""
            elif len(api_key) <= 8:
                record.cryptoapis_api_key_masked = "****"
            else:
                record.cryptoapis_api_key_masked = f"{api_key[:4]}...{api_key[-4:]}"

    def _cryptoapis_config_key(self, suffix):
        self.ensure_one()
        return "crypto_payment_sync.provider_%s.%s" % (self.id or "new", suffix)

    def _compute_cryptoapis_usage_config(self):
        params = self.env["ir.config_parameter"].sudo()
        for record in self:
            record.cryptoapis_page_size = int(params.get_param(record._cryptoapis_config_key("page_size"), "25"))
            record.cryptoapis_max_pages = int(params.get_param(record._cryptoapis_config_key("max_pages"), "2"))
            record.cryptoapis_request_delay = float(params.get_param(record._cryptoapis_config_key("request_delay"), "0.25"))
            record.cryptoapis_wallet_network_xmlids = params.get_param(
                record._cryptoapis_config_key("wallet_network_xmlids"),
                "",
            )
            network_ids = params.get_param(record._cryptoapis_config_key("wallet_network_ids"), "")
            ids = [int(item) for item in network_ids.split(",") if item.strip().isdigit()]
            record.cryptoapis_wallet_network_ids = [(6, 0, ids)]

    def _inverse_cryptoapis_usage_config(self):
        params = self.env["ir.config_parameter"].sudo()
        for record in self:
            params.set_param(record._cryptoapis_config_key("page_size"), record.cryptoapis_page_size or 25)
            params.set_param(record._cryptoapis_config_key("max_pages"), record.cryptoapis_max_pages or 2)
            params.set_param(record._cryptoapis_config_key("request_delay"), record.cryptoapis_request_delay or 0.25)
            params.set_param(
                record._cryptoapis_config_key("wallet_network_xmlids"),
                record.cryptoapis_wallet_network_xmlids or "",
            )
            params.set_param(
                record._cryptoapis_config_key("wallet_network_ids"),
                ",".join(str(network_id) for network_id in record.cryptoapis_wallet_network_ids.ids),
            )

    def _compute_crypto_wallet_count(self):
        counts = {
            item['payment_provider_id'][0]: item['payment_provider_id_count']
            for item in self.env['crypto.wallet'].read_group(
                [('payment_provider_id', 'in', self.ids)],
                ['payment_provider_id'],
                ['payment_provider_id'],
            )
            if item.get('payment_provider_id')
        }
        for record in self:
            record.payment_provider_id_crypto_wallet_count = counts.get(record.id, 0)

    def _compute_crypto_transaction_count(self):
        counts = {
            item['provider_id'][0]: item['provider_id_count']
            for item in self.env['payment.transaction'].read_group(
                [('provider_id', 'in', self.ids)],
                ['provider_id'],
                ['provider_id'],
            )
            if item.get('provider_id')
        }
        for record in self:
            record.provider_id_payment_transaction_count = counts.get(record.id, 0)

    @api.constrains("cryptoapis_page_size", "cryptoapis_max_pages", "cryptoapis_request_delay")
    def _check_cryptoapis_usage_limits(self):
        for record in self:
            if record.cryptoapis_page_size < 1 or record.cryptoapis_page_size > 50:
                raise UserError(_("Crypto APIs page size must be between 1 and 50."))
            if record.cryptoapis_max_pages < 1 or record.cryptoapis_max_pages > 20:
                raise UserError(_("Crypto APIs max pages must be between 1 and 20."))
            if record.cryptoapis_request_delay < 0 or record.cryptoapis_request_delay > 5:
                raise UserError(_("Crypto APIs request delay must be between 0 and 5 seconds."))

    def _cryptoapis_wallet_networks(self):
        self.ensure_one()
        networks = self.cryptoapis_wallet_network_ids
        if networks:
            return networks
        networks = self.env["crypto.network"]
        for xmlid in (self.cryptoapis_wallet_network_xmlids or "").split(","):
            xmlid = xmlid.strip()
            if not xmlid:
                continue
            try:
                record = self.env.ref(xmlid)
            except ValueError:
                raise UserError(_("Unknown wallet sync network XML ID: %s") % xmlid)
            if record._name != "crypto.network":
                raise UserError(_("Wallet sync XML ID is not a crypto network: %s") % xmlid)
            networks |= record
        return networks

    def _get_default_payment_method_id(self, code):
        self.ensure_one()
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'crypto':
            return default_codes
        return self.env.ref('crypto_payment_sync.account_payment_method_crypto').id

    def _crypto_get_api_url(self):
        """ Return the API URL according to the state """
        self.ensure_one()
        return 'https://rest.cryptoapis.io/'

    def _cryptoapis_headers(self):
        self.ensure_one()
        if not self.cryptoapis_api_key:
            raise UserError(_("Set a Crypto APIs API key before running this sync."))
        return {
            "Accept": "application/json",
            "X-API-Key": self.cryptoapis_api_key,
        }

    def _cryptoapis_request(self, method, path, params=None, payload=None, expected_statuses=None):
        self.ensure_one()
        url = self._crypto_get_api_url().rstrip("/") + "/" + path.lstrip("/")
        expected_statuses = expected_statuses or (200,)
        headers = self._cryptoapis_headers()
        if method.upper() in ("POST", "PUT", "PATCH"):
            headers = dict(headers, **{"Content-Type": "application/json"})
        try:
            response = requests.request(
                method.upper(),
                url,
                headers=headers,
                params=params or {},
                json=payload,
                timeout=30,
            )
        except requests.RequestException as exc:
            raise UserError(_("Crypto APIs request failed: %s") % exc) from exc
        if response.status_code not in expected_statuses:
            _logger.warning(
                "Crypto APIs %s failed path=%s status=%s body=%s",
                method.upper(),
                path,
                response.status_code,
                (response.text or "")[:500],
            )
            raise UserError(_("Crypto APIs request failed with HTTP %s.") % response.status_code)
        try:
            return response.json()
        except ValueError as exc:
            raise UserError(_("Crypto APIs returned an invalid JSON response.")) from exc

    def _cryptoapis_get(self, path, params=None):
        return self._cryptoapis_request("GET", path, params=params)

    def _cryptoapis_post(self, path, payload=None, params=None, expected_statuses=None):
        return self._cryptoapis_request(
            "POST",
            path,
            params=params,
            payload=payload or {},
            expected_statuses=expected_statuses or (200, 201),
        )

    def _cryptoapis_page_size(self):
        self.ensure_one()
        return max(1, min(self.cryptoapis_page_size or 25, 50))

    def _cryptoapis_max_pages(self):
        self.ensure_one()
        return max(1, min(self.cryptoapis_max_pages or 1, 20))

    def _cryptoapis_request_delay(self):
        self.ensure_one()
        return max(0.0, min(self.cryptoapis_request_delay or 0.0, 5.0))

    def _cryptoapis_notification(self, title, message, notification_type="success", sticky=False):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": notification_type,
                "sticky": sticky,
            },
        }

    def _sync_currency_assets(self, asset_type):
        self.ensure_one()
        created = 0
        updated = 0
        processed = 0
        offset = 0
        limit = self._cryptoapis_page_size()
        max_items = limit * self._cryptoapis_max_pages()
        total_items = max_items

        while processed < total_items and processed < max_items:
            data = self._cryptoapis_get(
                "market-data/metadata/assets",
                params={
                    "context": f"OdooSync{asset_type.title()}Assets",
                    "limit": limit,
                    "offset": offset,
                    "type": asset_type,
                },
            ).get("data") or {}
            total_items = min(data.get("total") or 0, max_items)
            assets = data.get("items") or []
            if not assets:
                break

            for asset in assets:
                symbol = (asset.get("symbol") or "").upper()
                full_name = asset.get("name") or symbol
                reference_id = asset.get("referenceId")
                if not symbol:
                    continue
                currency = self.env['res.currency'].search([('name', '=', symbol)], limit=1)
                values = {
                    'full_name': full_name,
                    'symbol': symbol,
                    'currency_unit_label': symbol,
                    'currency_subunit_label': symbol,
                    'rounding': 0.00000001 if asset_type == 'crypto' else 0.01,
                    'active': True,
                    'type': asset_type,
                    'cryptoapis_referenceId': reference_id,
                }
                if currency:
                    currency.write(values)
                    updated += 1
                else:
                    values['name'] = symbol
                    self.env['res.currency'].create(values)
                    created += 1
                processed += 1
                if processed >= max_items:
                    break

            offset += limit
            if len(assets) < limit:
                break
            time.sleep(self._cryptoapis_request_delay())

        return created, updated, processed

    def sync_crypto_currencies(self):
        total_created = 0
        total_updated = 0
        total_processed = 0
        for rec in self:
            created, updated, processed = rec._sync_currency_assets('crypto')
            total_created += created
            total_updated += updated
            total_processed += processed
        return self._cryptoapis_notification(
            _("Crypto Asset Sync"),
            _("Processed %s crypto asset(s): %s created, %s updated.") % (
                total_processed,
                total_created,
                total_updated,
            ),
        )

    def sync_fiat_currencies(self):
        total_created = 0
        total_updated = 0
        total_processed = 0
        for rec in self:
            created, updated, processed = rec._sync_currency_assets('fiat')
            total_created += created
            total_updated += updated
            total_processed += processed
        return self._cryptoapis_notification(
            _("Fiat Asset Sync"),
            _("Processed %s fiat asset(s): %s created, %s updated.") % (
                total_processed,
                total_created,
                total_updated,
            ),
        )

    def sync_currencies_rate(self):
        calculation_timestamp = int(time.time())
        created = 0
        updated = 0
        skipped = 0
        for rec in self:
            rec._cryptoapis_headers()
            if not rec.company_id.currency_id.cryptoapis_referenceId:
                raise UserError(_("Set a Crypto APIs reference ID on the company currency before syncing rates."))
            rate_limit = rec._cryptoapis_page_size() * rec._cryptoapis_max_pages()
            currencies = self.env['res.currency'].search(
                [('id', '!=', rec.company_id.currency_id.id), ('cryptoapis_referenceId', '!=', '')],
                limit=rate_limit,
            )
            for currency in currencies:
                data = rec._cryptoapis_get(
                    "market-data/exchange-rates/by-id/%s/%s" % (
                        rec.company_id.currency_id.cryptoapis_referenceId,
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
                    skipped += 1
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
                    created += 1
                else:
                    exist_rate_date.write({'company_rate': rate_val})
                    updated += 1
                time.sleep(rec._cryptoapis_request_delay())
        return self._cryptoapis_notification(
            _("Currency Rate Sync"),
            _("Rates synced: %s created, %s updated, %s skipped.") % (created, updated, skipped),
            notification_type="warning" if skipped else "success",
            sticky=bool(skipped),
        )

    def sync_wallets(self):
        skipped = []
        synced_wallets = 0
        for provider in self:
            if not provider.cryptoapis_api_key:
                raise UserError(_("Set a Crypto APIs API key before syncing wallets."))
            wallet_networks = provider._cryptoapis_wallet_networks()
            if not wallet_networks:
                return provider._cryptoapis_notification(
                    _("Crypto APIs Wallet Sync"),
                    _("Select one or more Wallet Sync Networks on this provider before running this action. This prevents accidental broad paid API usage."),
                    notification_type="warning",
                    sticky=True,
                )
            for network in wallet_networks:
                blockchain = network.blockchain_id
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
                        skipped.append(f"{blockchain.name} / {network.name}")
                        _logger.warning(
                            "Skipping Crypto APIs wallet sync for %s / %s: %s",
                            blockchain.name,
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
                        wallet_by_name = self.env['crypto.wallet'].search([('xpub', '=', extendedPublicKey)])
                        if len(wallet_by_name) <= 0:
                            self.env['crypto.wallet'].create({
                                'name': network.blockchain_id.name + ' - ' + network.name,
                                'xpub': extendedPublicKey,
                                'network_id': network.id,
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
