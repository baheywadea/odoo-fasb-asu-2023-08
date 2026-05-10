# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import json
import requests
import secrets
from odoo import _, fields, models
from werkzeug.urls import url_encode
from odoo.http import request
from odoo.exceptions import UserError
from werkzeug.urls import url_decode, url_parse

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    capture_manually = fields.Boolean(related='provider_id.capture_manually')

    # Fields needed by the QR payment page
    crypto_address = fields.Many2one('crypto.wallet.address', string="Address", copy=False)

    crypto_amount_eth = fields.Float(copy=False)
    crypto_public_token = fields.Char(copy=False, index=True)

    crypto_tx_hash = fields.Char(copy=False,string="TX Hash")

    def _get_crypto_checkout_company(self):
        self.ensure_one()
        order = self.sale_order_ids[:1]
        return order.company_id or self.company_id

    def _get_crypto_checkout_currency(self):
        self.ensure_one()
        order = self.sale_order_ids[:1]
        currency = order.pricelist_id.currency_id or self.currency_id
        return currency if currency and currency.type == 'crypto' else self.env['res.currency']

    def _get_crypto_checkout_wallet(self):
        self.ensure_one()
        company = self._get_crypto_checkout_company()
        domain = [
            ('payment_provider_id', '=', self.provider_id.id),
            ('active', '=', True),
        ]
        if company:
            domain += ['|', ('company_id', '=', company.id), ('company_id', '=', False)]
        wallets = self.env["crypto.wallet"].search(domain)
        if not wallets:
            raise UserError(_(
                "No active crypto wallet is configured for this payment provider and company. "
                "Create or sync a wallet, assign it to this provider, and add wallet addresses."
            ))

        if self.provider_id.state == 'test':
            wallets = wallets.filtered(lambda wallet: wallet.network_id.is_testnet)
        elif self.provider_id.state == 'enabled':
            wallets = wallets.filtered(lambda wallet: not wallet.network_id.is_testnet)
        if not wallets:
            raise UserError(_(
                "No crypto wallet is configured for the provider state. Use a testnet wallet when the provider is "
                "in Test Mode, or a mainnet wallet when the provider is Enabled."
            ))

        checkout_currency = self._get_crypto_checkout_currency()
        currency_wallets = wallets.filtered(lambda wallet: wallet.currency_id == checkout_currency) if checkout_currency else wallets
        for candidates in (
            currency_wallets.filtered('is_default'),
            currency_wallets,
            wallets.filtered('is_default'),
            wallets,
        ):
            if candidates:
                return candidates[0]
        raise UserError(_("No usable crypto wallet is configured for this payment."))

    def _reserve_crypto_checkout_address(self, wallet):
        self.ensure_one()
        if wallet.checkout_address_mode == 'default_wallet_address':
            address = wallet._get_default_checkout_address()
            self.write({'crypto_address': address.id})
            return address

        address_obj = self.env["crypto.wallet.address"]
        address = address_obj.search([('payment_transaction_id', '=', self.id)], limit=1)
        if not address:
            address = address_obj.search([
                ('payment_transaction_id', '=', False),
                ('wallet_id', '=', wallet.id),
                ('event_ids', '=', False),
            ], limit=1)
        if not address:
            wallet.derive_new_addresses()
            address = address_obj.search([
                ('payment_transaction_id', '=', False),
                ('wallet_id', '=', wallet.id),
                ('event_ids', '=', False),
            ], limit=1)
        if not address:
            raise UserError(_(
                "No available wallet address was found for %(wallet)s. "
                "Sync or derive wallet addresses before accepting this payment.",
                wallet=wallet.display_name,
            ))
        address.write({'payment_transaction_id': self.id})
        self.write({'crypto_address': address.id})
        return address

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)

        # Only apply to your crypto provider
        if self.provider_code != 'crypto':
            return res

        self.ensure_one()

        # 1) Ensure a public token exists (used to protect QR page / status endpoint)
        if not self.crypto_public_token:
            self.crypto_public_token = secrets.token_urlsafe(24)

        # 2) Amount to be paid in ETH (adjust if you do currency conversion)
        # Here I assume your transaction amount is already in ETH.
        # If your tx currency is KWD/USD, you MUST convert before setting crypto_amount_eth.
        if not self.crypto_amount_eth:
            self.crypto_amount_eth = float(self.amount)

        wallet = self._get_crypto_checkout_wallet()
        address = self._reserve_crypto_checkout_address(wallet)

        # 4) Build redirect URL to our QR page

        address.action_generate_event(self.id, self.crypto_public_token)
        base_url = self.get_base_url()
        pay_url = f"{base_url}/crypto/pay/{self.id}?{url_encode({'token': self.crypto_public_token})}"

        # 5) IMPORTANT: Odoo will redirect using "api_url" (as you requested)
        # Keep 'api_url' key for compatibility with your templates
        parsed_url = url_parse(pay_url)
        url_params = url_decode(parsed_url.query)
        wei_amount = int(self.crypto_amount_eth * 10 ** 18)
        expected_blockchain = (self.crypto_address.wallet_id.blockchain_id.name or "").lower().strip()
        expected_network = (self.crypto_address.wallet_id.network_id.name or "").lower().strip()
        qr_uri = (
            f"{expected_blockchain}:{self.crypto_address.name}"
            f"?value={wei_amount}"
            f"&chainId={self.crypto_address.wallet_id.network_id.chain_id}"
        )
        processing_values.update({
            'crypto_qr_uri':qr_uri,
            'url_params': url_params,
            'api_url': pay_url,
            # Optional extra values if you want to show them in your template
            'crypto_address': self.crypto_address,
            'crypto_amount_eth': self.crypto_amount_eth,
            'crypto_network': self.crypto_address.wallet_id.network_id.name,
        })

        _logger.debug("Prepared crypto rendering values for transaction %s", self.reference)

        # Return processing_values (same behavior as your existing code)
        return processing_values

    def _process(self, provider_code, notification_data):
        _logger.info("Processing crypto payment notification for transaction %s", self.reference)
        # super()._process(provider_code,notification_data)
        if provider_code != 'crypto':
            return super()._process(provider_code, notification_data)
        else:
            if self.state == 'done':
                self._set_done()
            else:
                self._set_pending()

    def _prepare_crypto_invoice_link_payload(self, processing_values):
        odoo_base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        website = request.env['website'].get_current_website()
        odoo_base_url = website.domain or request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        language = 'ar' if self.partner_lang == 'ar_001' or self.partner_lang == 'ar_SY' else 'en'
        payload = {
            # required fields
            "CustomerName": self.partner_name,
            "InvoiceValue": processing_values['amount'],
            "NotificationOption": "LNK",
            # optional fields
            "CustomerEmail": self.partner_email,  # Mandatory if the NotificationOption = EML or ALL
            "CustomerAddress": {
                "Block": "string",
                "Street": "string",
                "HouseBuildingNo": "string",
                "Address": self.partner_address,
                "AddressInstructions": self.partner_city
            },
            "CustomerReference": processing_values['reference'],
            "CallBackUrl": f"{odoo_base_url}/invoice_link/crypto/callback/company/" + str(self.company_id.id),
            "ErrorUrl": f"{odoo_base_url}/invoice_link/crypto/callback/company/" + str(self.company_id.id),
            "DisplayCurrencyIso": self.currency_id.name if self.currency_id.name else 'KWD',
            "Language": language
        }

        return payload

        # === ACTION METHODS ===#

    def myfatoorah_get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'crypto':
            return res
        api_key = self.env['ir.config_parameter'].sudo().get_param('crypto_payment_sync.myfatoorah_api_key')
        if not api_key:
            raise UserError(_("Configure crypto_payment_sync.myfatoorah_api_key before using MyFatoorah rendering."))
        api_url = "{}/v2/SendPayment".format("https://apitest.myfatoorah.com")
        payload = self._prepare_crypto_invoice_link_payload(processing_values)
        headers = {"Content-Type": "application/json", "Authorization": "Bearer " + api_key}
        response = requests.post(api_url, data=json.dumps(payload), headers=headers, timeout=30)
        invoice_url = '#'
        if response.status_code != 200:
            _logger.warning("MyFatoorah invoice generation failed with HTTP %s", response.status_code)
        if response.status_code == 200:
            response_data = response.json()
            self.provider_reference = response_data["Data"]["InvoiceId"]
            # self._set_pending("myfatoorah transaction pending invoice payment.")
            invoice_url = response_data["Data"]["InvoiceURL"]
        processing_values.update({
            'api_url': invoice_url
        })
        return processing_values
