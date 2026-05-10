# -*- coding: utf-8 -*-
import json
import logging
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

        # Build Ethereum payment URI (EIP-681 style: value in WEI)
        wei = _eth_to_wei(tx.crypto_amount_eth or 0.0)
        uri = f"ethereum:{address}?value={wei}"

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

        paid = tx.state in ("done", "authorized")  # adjust to your flow
        return {
            "ok": True,
            "paid": paid,
            "state": tx.state,
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

        data = payload.get("data") or {}
        item = data.get("item") or {}

        # defensive nesting: data.item.item
        if isinstance(item.get("item"), dict):
            item = item["item"]

        _logger.info("Parsed item payload: %s", item)

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

        # mark done
        if hasattr(tx, "crypto_tx_hash"):
            tx.sudo().write({"crypto_tx_hash": tx_hash})

        if tx.state not in ("done", "authorized"):
            try:
                tx._set_done()
            except Exception:
                tx.sudo().write({"state": "done"})

        return _resp("ok", 200)

    @http.route("/crypto/intent/<int:tx_id>", type="jsonrpc", auth="public", csrf=False, methods=["POST"])
    def crypto_intent(self, tx_id, token=None, **kw):
        tx = self._get_tx_or_404(tx_id, token)
        if not tx:
            return {"ok": False, "error": "not_found"}

        address = (tx.crypto_address.name or "").strip()
        if not address:
            return {"ok": False, "error": "missing_address"}

        chain_id = int(tx.crypto_address.wallet_id.network_id.chain_id or 1)

        # IMPORTANT: compute wei safely (no float issues)
        from decimal import Decimal, ROUND_HALF_UP
        amt = Decimal(str(tx.crypto_amount_eth or "0"))
        wei = (amt * Decimal("1000000000000000000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        return {
            "ok": True,
            "chainId": chain_id,
            "to": address,
            "valueWei": str(int(wei)),
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
