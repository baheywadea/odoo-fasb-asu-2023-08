# -*- coding: utf-8 -*-
import json
import logging
import requests
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

try:
    import qrcode
except Exception:
    qrcode = None


def _resp(text, status=200):
    return request.make_response(
        text,
        headers=[("Content-Type", "text/plain; charset=utf-8")],
        status=status,
    )


def _eth_to_wei(amount_eth):
    """Safe ETH -> WEI conversion (no float rounding issues)."""
    try:
        amt = Decimal(str(amount_eth or "0"))
    except (InvalidOperation, TypeError):
        amt = Decimal("0")
    wei = (amt * Decimal("1000000000000000000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(wei)


def _decimal_or_none(value):
    try:
        if value in (None, ""):
            return None
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None


class CryptoPaymentController(http.Controller):

    def _get_tx_or_404(self, tx_id, token):
        tx = request.env["payment.transaction"].sudo().browse(int(tx_id))
        if not tx.exists():
            return None
        # public token check (protect QR page)
        if not token or token != (tx.crypto_public_token or ""):
            return None
        return tx

    @http.route("/crypto/pay/<int:tx_id>", type="http", auth="public", website=True, methods=["GET"])
    def crypto_pay_page(self, tx_id, token=None, **kw):
        tx = self._get_tx_or_404(tx_id, token)
        if not tx:
            return request.not_found()

        values = {
            "tx": tx,
            "token": token,
            "network_label": (tx.crypto_address.wallet_id.network_id.name or "").upper() or "ETH",
            "walletconnect_project_id": tx.provider_id.walletconnect_project_id
            or request.env["ir.config_parameter"].sudo().get_param("crypto_payment_sync.walletconnect_project_id")
            or "",
        }
        return request.render("crypto_payment_sync.crypto_payment_qr_page", values)

    @http.route("/crypto/qr/<int:tx_id>.png", type="http", auth="public", csrf=False, methods=["GET"])
    def crypto_qr_png(self, tx_id, token=None, **kw):
        tx = self._get_tx_or_404(tx_id, token)
        if not tx:
            return request.not_found()

        if qrcode is None:
            return request.make_response("qrcode library not installed", [("Content-Type", "text/plain")], 500)

        address = (tx.crypto_address.name or "").strip()
        if not address:
            return request.make_response("missing address", [("Content-Type", "text/plain")], 400)

        # Manual fallback QR: encode the address only so scanner apps do not force a MetaMask/EIP-681 deep link.
        uri = address

        qr = qrcode.QRCode(box_size=8, border=2)
        qr.add_data(uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        bio = BytesIO()
        img.save(bio, format="PNG")
        png = bio.getvalue()

        headers = [
            ("Content-Type", "image/png"),
            ("Cache-Control", "no-store"),
        ]
        return request.make_response(png, headers)


    # ✅ FIX: Odoo 19 => type='json' deprecated; use type='jsonrpc'
    @http.route("/crypto/status/<int:tx_id>", type="jsonrpc", auth="public", csrf=False, methods=["POST"])
    def crypto_status(self, tx_id, token=None, **kw):
        tx = self._get_tx_or_404(tx_id, token)
        if not tx:
            return {"ok": False, "error": "not_found"}

        confirmation_status = "waiting"
        message = "Waiting for payment confirmation..."
        if getattr(tx, "crypto_tx_hash", False) and tx.state not in ("done", "authorized"):
            confirmation_status, message = self._confirm_walletconnect_receipt(tx)

        paid = tx.state in ("done", "authorized")  # adjust to your flow
        if paid:
            confirmation_status = "confirmed"
            message = "Payment confirmed. Redirecting..."
        return {
            "ok": True,
            "paid": paid,
            "state": tx.state,
            "tx_hash": getattr(tx, "crypto_tx_hash", None),
            "confirmation_status": confirmation_status,
            "message": message,
            "received": getattr(tx, "crypto_received_amount", None),
        }

    @http.route("/invoice_link/crypto/callback/<int:tx_id>", type="http",
                auth="public", csrf=False, methods=["GET", "POST"])
    def crypto_callback(self, tx_id, **kwargs):

        if request.httprequest.method == "GET":
            return _resp("ok", 200)

        raw = request.httprequest.get_data(as_text=True) or ""
        _logger.info("CryptoAPIs callback tx_id=%s payload=%s", tx_id, raw)

        try:
            payload = json.loads(raw)
        except Exception:
            return _resp("bad json", 400)

        tx = request.env["payment.transaction"].sudo().browse(tx_id)
        if not tx.exists():
            return _resp("tx not found", 404)

        item = self._cryptoapis_callback_item(payload)
        _logger.info("Parsed CryptoAPIs callback tx_id=%s", tx_id)

        incoming_blockchain = (item.get("blockchain") or "").lower().strip()
        incoming_network = (item.get("network") or "").lower().strip()

        expected_blockchain = (tx.crypto_address.wallet_id.blockchain_id.name or "").lower().strip()
        expected_network = (tx.crypto_address.wallet_id.network_id.name or "").lower().strip()
        expected_network = expected_network.replace(" testnet", "").replace("testnet", "").strip()

        if incoming_blockchain and expected_blockchain and incoming_blockchain != expected_blockchain:
            return _resp("blockchain mismatch", 400)

        if incoming_network and expected_network and incoming_network != expected_network:
            return _resp("network mismatch", 400)

        direction = (item.get("direction") or "").lower().strip()
        if direction and direction != "incoming":
            return _resp("not incoming", 200)

        incoming_address = (item.get("address") or "").lower().strip()
        tx_address = (getattr(tx.crypto_address, "name", tx.crypto_address) or "").lower().strip()
        if incoming_address and tx_address and incoming_address != tx_address:
            return _resp("address mismatch", 400)

        tx_hash = (item.get("transactionId") or "").strip()
        if not tx_hash:
            return _resp("missing transactionId", 400)

        # idempotent
        if getattr(tx, "crypto_tx_hash", False) == tx_hash and tx.state in ("done", "authorized"):
            return _resp("ok", 200)

        unit = (item.get("unit") or "").upper().strip()
        if unit and unit != "ETH":
            return _resp("unit mismatch", 400)

        self._mark_crypto_tx_done(tx, tx_hash)

        return _resp("ok", 200)

    @http.route("/invoice_link/crypto/callback/address/<int:address_id>", type="http",
                auth="public", csrf=False, methods=["GET", "POST"])
    def crypto_address_callback(self, address_id, **kwargs):
        if request.httprequest.method == "GET":
            return _resp("ok", 200)

        raw = request.httprequest.get_data(as_text=True) or ""
        _logger.info("CryptoAPIs shared-address callback address_id=%s", address_id)

        try:
            payload = json.loads(raw)
        except Exception:
            return _resp("bad json", 400)

        address = request.env["crypto.wallet.address"].sudo().browse(address_id)
        if not address.exists():
            return _resp("address not found", 404)

        item = self._cryptoapis_callback_item(payload)
        if not self._cryptoapis_callback_matches_address(item, address):
            return _resp("address mismatch", 400)

        tx_hash = (item.get("transactionId") or item.get("hash") or "").strip()
        if not tx_hash:
            return _resp("missing transactionId", 400)

        tx = self._match_shared_address_payment(address, item, tx_hash)
        if not tx:
            _logger.warning(
                "No unambiguous payment transaction matched shared address callback address_id=%s tx_hash=%s",
                address.id,
                tx_hash,
            )
            return _resp("payment needs review", 202)

        self._mark_crypto_tx_done(tx, tx_hash)
        return _resp("ok", 200)

    def _cryptoapis_callback_item(self, payload):
        data = payload.get("data") or {}
        item = data.get("item") or {}
        if isinstance(item.get("item"), dict):
            item = item["item"]
        return item

    def _cryptoapis_callback_matches_address(self, item, address):
        incoming_address = (item.get("address") or "").lower().strip()
        if incoming_address and incoming_address != (address.name or "").lower().strip():
            return False

        incoming_blockchain = (item.get("blockchain") or "").lower().strip()
        incoming_network = (item.get("network") or "").lower().strip()
        expected_blockchain = (address.wallet_id.blockchain_id.name or "").lower().strip()
        expected_network = (address.wallet_id.network_id.name or "").lower().strip()
        expected_network = expected_network.replace(" testnet", "").replace("testnet", "").strip()

        if incoming_blockchain and expected_blockchain and incoming_blockchain != expected_blockchain:
            return False
        if incoming_network and expected_network and incoming_network != expected_network:
            return False

        direction = (item.get("direction") or "").lower().strip()
        if direction and direction != "incoming":
            return False

        return True

    def _callback_amount(self, item):
        for key in ("amount", "value"):
            amount = _decimal_or_none(item.get(key))
            if amount is not None:
                return amount
        amount_data = item.get("amount") if isinstance(item.get("amount"), dict) else {}
        return _decimal_or_none(amount_data.get("amount") or amount_data.get("value"))

    def _match_shared_address_payment(self, address, item, tx_hash):
        Tx = request.env["payment.transaction"].sudo()
        tx = Tx.search([
            ("crypto_address", "=", address.id),
            ("crypto_tx_hash", "=", tx_hash),
            ("state", "in", ("draft", "pending", "authorized")),
        ], limit=1)
        if tx:
            return tx

        incoming_amount = self._callback_amount(item)
        if incoming_amount is None:
            return Tx.browse()

        candidates = Tx.search([
            ("crypto_address", "=", address.id),
            ("state", "in", ("draft", "pending", "authorized")),
        ])
        matched = candidates.filtered(
            lambda record: _decimal_or_none(record.crypto_amount_eth) == incoming_amount
        )
        return matched[:1] if len(matched) == 1 else Tx.browse()

    def _mark_crypto_tx_done(self, tx, tx_hash):
        vals = {}
        if hasattr(tx, "crypto_tx_hash"):
            vals["crypto_tx_hash"] = tx_hash
        if vals:
            tx.sudo().write(vals)

        if tx.state not in ("done", "authorized"):
            try:
                tx._set_done()
            except Exception:
                tx.sudo().write({"state": "done"})

    def _confirm_walletconnect_receipt(self, tx):
        tx_hash = (getattr(tx, "crypto_tx_hash", "") or "").strip()
        if not tx_hash:
            return "waiting", "Waiting for payment confirmation..."

        network = tx.crypto_address.wallet_id.network_id
        rpc_url = self._network_rpc_url(network)
        if not rpc_url:
            return "waiting", "Transaction sent. Waiting for webhook confirmation..."

        receipt = self._evm_rpc(rpc_url, "eth_getTransactionReceipt", [tx_hash])
        if not receipt:
            return "pending", "Transaction sent. Waiting for blockchain confirmation..."

        status = receipt.get("status")
        if status and status.lower() == "0x0":
            return "failed", "The blockchain transaction failed. Please contact support before trying again."
        if not receipt.get("blockNumber"):
            return "pending", "Transaction sent. Waiting for blockchain confirmation..."

        tx_data = self._evm_rpc(rpc_url, "eth_getTransactionByHash", [tx_hash])
        if not tx_data:
            return "pending", "Transaction sent. Waiting for blockchain confirmation..."

        expected_to = (tx.crypto_address.name or "").lower()
        actual_to = (tx_data.get("to") or "").lower()
        if expected_to and actual_to and expected_to != actual_to:
            return "mismatch", "The sent transaction does not match this payment address. Please contact support."

        expected_value = _eth_to_wei(tx.crypto_amount_eth)
        try:
            actual_value = int(tx_data.get("value") or "0x0", 16)
        except (TypeError, ValueError):
            actual_value = 0
        if actual_value < expected_value:
            return "mismatch", "The sent transaction amount is lower than the expected payment amount. Please contact support."

        self._mark_crypto_tx_done(tx, tx_hash)
        return "confirmed", "Payment confirmed. Redirecting..."

    def _network_rpc_url(self, network):
        rpc_url = (network.rpc_url or "").strip()
        if rpc_url and "YOUR_PROJECT_ID" not in rpc_url and rpc_url != "read-only-provider":
            return rpc_url
        defaults = {
            1: "https://ethereum.publicnode.com",
            10: "https://mainnet.optimism.io",
            56: "https://bsc-dataseed.binance.org",
            137: "https://polygon-rpc.com",
            8453: "https://mainnet.base.org",
            42161: "https://arb1.arbitrum.io/rpc",
            43114: "https://api.avax.network/ext/bc/C/rpc",
            11155111: "https://ethereum-sepolia.publicnode.com",
        }
        return defaults.get(int(network.chain_id or 0), "")

    def _evm_rpc(self, rpc_url, method, params):
        try:
            response = requests.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": method,
                    "params": params,
                },
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            _logger.info("Read-only EVM RPC check failed for %s: %s", method, exc)
            return None
        if payload.get("error"):
            _logger.info("Read-only EVM RPC returned an error for %s", method)
            return None
        return payload.get("result")

    @http.route("/crypto/intent/<int:tx_id>", type="jsonrpc", auth="public", csrf=False, methods=["POST"])
    def crypto_intent(self, tx_id, token=None, **kw):
        tx = self._get_tx_or_404(tx_id, token)
        if not tx:
            return {"ok": False, "error": "not_found"}

        address = (tx.crypto_address.name or "").strip()
        if not address:
            return {"ok": False, "error": "missing_address"}

        network = tx.crypto_address.wallet_id.network_id
        chain_id = int(network.chain_id or 1)
        rpc_url = (network.rpc_url or "").strip()

        # IMPORTANT: compute wei safely (no float issues)
        from decimal import Decimal, ROUND_HALF_UP
        amt = Decimal(str(tx.crypto_amount_eth or "0"))
        wei = (amt * Decimal("1000000000000000000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        return {
            "ok": True,
            "chainId": chain_id,
            "to": address,
            "valueWei": str(int(wei)),
            "rpcUrl": rpc_url if rpc_url and "YOUR_PROJECT_ID" not in rpc_url and rpc_url != "read-only-provider" else "",
        }

    @http.route("/crypto/wc_tx/<int:tx_id>", type="jsonrpc", auth="public", csrf=False, methods=["POST"])
    def crypto_store_wc_tx(self, tx_id, token=None, tx_hash=None, from_address=None, **kw):
        tx = self._get_tx_or_404(tx_id, token)
        if not tx:
            return {"ok": False, "error": "not_found"}

        vals = {}
        if tx_hash and hasattr(tx, "crypto_tx_hash"):
            vals["crypto_tx_hash"] = tx_hash
        if from_address and hasattr(tx, "crypto_sender"):
            vals["crypto_sender"] = from_address

        if vals:
            tx.sudo().write(vals)

        return {"ok": True}
