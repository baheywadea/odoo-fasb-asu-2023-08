# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import json
import requests
import secrets
from odoo import _, fields, models
from werkzeug.urls import url_encode
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
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

        address = None
        # 3) Ensure deposit address exists (replace this with your real address generator)
        for order in self.sale_order_ids:
            wallet_id = self.env["crypto.wallet"].search(
                [('company_id', '=', order.company_id.id), ('currency_id', '=', order.pricelist_id.currency_id.id)])
            if len(wallet_id) > 0:
                wallet_id = wallet_id[0]
                address = self.env["crypto.wallet.address"].search([('payment_transaction_id', '=', self.id)])
                if not address:
                    address = self.env["crypto.wallet.address"].search(
                        [('payment_transaction_id', '=', None), ('wallet_id', '=', wallet_id.id),
                         ('event_ids', '=', None)])
                    if len(address) > 0:
                        address = address[0]
                        address.write({'payment_transaction_id': self.id})
                        self.write({'crypto_address': address.id})
                    else:
                        wallet_id.derive_new_addresses()
                        address = self.env["crypto.wallet.address"].search(
                            [('payment_transaction_id', '=', None), ('wallet_id', '=', wallet_id.id),
                             ('event_ids', '=', None)])
                        if len(address) > 0:
                            address = address[0]
                            address.write({'payment_transaction_id': self.id})
                            self.write({'crypto_address': address.id})
            else:
                raise UserError(
                    _("Crypto API Key No Wallet configured."))

        if not address:
            wallet_id = self.env["crypto.wallet"].search(
                [('company_id', '=', self.company_id.id), ('currency_id', '=', self.currency_id.id)])
            if len(wallet_id) > 0:
                wallet_id = wallet_id[0]
                address = self.env["crypto.wallet.address"].search([('payment_transaction_id', '=', self.id)])
                if not address:
                    address = self.env["crypto.wallet.address"].search(
                        [('payment_transaction_id', '=', None), ('wallet_id', '=', wallet_id.id),
                         ('event_ids', '=', None)])
                    if len(address) > 0:
                        address = address[0]
                        address.write({'payment_transaction_id': self.id})
                        self.write({'crypto_address': address.id})
                    else:
                        wallet_id.derive_new_addresses()
                        address = self.env["crypto.wallet.address"].search(
                            [('payment_transaction_id', '=', None), ('wallet_id', '=', wallet_id.id),
                             ('event_ids', '=', None)])
                        if len(address) > 0:
                            address = address[0]
                            address.write({'payment_transaction_id': self.id})
                            self.write({'crypto_address': address.id})
            else:
                raise UserError(
                    _("Crypto API Key No Wallet configured."))

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

        _logger.info("Rendering Values : \n%s", str(processing_values))

        # Return processing_values (same behavior as your existing code)
        return processing_values

    def _process(self, provider_code, notification_data):
        _logger.info("crypto Payment _process_notification_data : \n%s", str(notification_data))
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
        api_key = "SK_KWT_vVZlnnAqu8jRByOWaRPNId4ShzEDNt256dvnjebuyzo52dXjAfRx2ixW5umjWSUx"
        api_url = "{}/v2/SendPayment".format("https://apitest.myfatoorah.com")
        payload = self._prepare_crypto_invoice_link_payload(processing_values)
        # Log MyFatoorah Payload
        _logger.info("crypto Payload is :\n%s", payload)
        headers = {"Content-Type": "application/json", "Authorization": "Bearer " + api_key}
        response = requests.post(api_url, data=json.dumps(payload), headers=headers)
        _logger.info("crypto Response is :\n%s", response)
        url = "https://portal.myfatoorah.com/Files/API/mf-config.json"
        mf_countries = requests.get(url).json()
        _logger.info("mf_countries: \n%s", mf_countries)
        invoice_id = ''
        invoice_url = '#'
        if response.status_code != 200:
            _logger.info("Failed on generating invoice with error:\n%s", response.json())
        if response.status_code == 200:
            response_data = response.json()
            self.provider_reference = response_data["Data"]["InvoiceId"]
            # self._set_pending("myfatoorah transaction pending invoice payment.")
            invoice_url = response_data["Data"]["InvoiceURL"]
        processing_values.update({
            'api_url': invoice_url
        })
        return processing_values
