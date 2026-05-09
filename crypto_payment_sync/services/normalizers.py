import hashlib
import json
from datetime import datetime, timezone


def canonical_json(data):
    return json.dumps(data or {}, sort_keys=True, separators=(",", ":"), default=str)


def compute_payload_hash(payload):
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _safe_float(value):
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _timestamp_to_iso(value):
    if value in (None, ""):
        return None
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return str(value)
    return datetime.fromtimestamp(numeric, tz=timezone.utc).isoformat()


def build_duplicate_key(*, source_provider, network, account_reference, transaction_hash=None, source_transaction_id=None):
    parts = [
        source_provider or "unknown_provider",
        network or "unknown_network",
        account_reference or "unknown_account",
        transaction_hash or source_transaction_id or "unknown_transaction",
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def normalize_evm_transaction_payload(payload, *, source_provider="cryptoapis", network=None, account_reference=None):
    """Normalize a Crypto APIs-like EVM transaction payload for ledger ingestion.

    The function is intentionally tolerant because fixture and live response
    shapes may differ by chain and API category. Ambiguous classifications are
    marked as `needs_review`.
    """
    payload = payload or {}
    fee = payload.get("fee") or {}
    value = payload.get("value") or {}
    mined_block = payload.get("minedInBlock") or {}
    tx_hash = payload.get("hash") or payload.get("txHash") or payload.get("transactionHash")
    source_id = payload.get("transactionId") or payload.get("referenceId") or tx_hash
    sender = payload.get("sender") or payload.get("from")
    recipient = payload.get("recipient") or payload.get("to")
    value_amount = _safe_float(value.get("amount") if isinstance(value, dict) else payload.get("amount"))
    value_unit = value.get("unit") if isinstance(value, dict) else payload.get("assetSymbol")
    fee_amount = _safe_float(fee.get("amount") if isinstance(fee, dict) else payload.get("feeAmount"))
    fee_unit = fee.get("unit") if isinstance(fee, dict) else payload.get("feeAssetSymbol")

    normalized = {
        "source_provider": source_provider,
        "source_transaction_id": source_id,
        "transaction_hash": tx_hash,
        "timestamp": _timestamp_to_iso(payload.get("timestamp")),
        "asset_symbol": value_unit or "",
        "quantity": value_amount,
        "fee_quantity": fee_amount,
        "fee_asset_symbol": fee_unit or "",
        "counterparty": recipient or sender or "",
        "network": network or payload.get("network") or "",
        "block_hash": mined_block.get("hash") if isinstance(mined_block, dict) else "",
        "block_height": mined_block.get("height") if isinstance(mined_block, dict) else "",
        "processing_status": "needs_review",
        "transaction_type": "unknown",
        "reviewer_notes": "Classification requires professional review.",
        "payload_hash": compute_payload_hash(payload),
    }
    normalized["duplicate_key"] = build_duplicate_key(
        source_provider=source_provider,
        network=normalized["network"],
        account_reference=account_reference or sender or recipient,
        transaction_hash=tx_hash,
        source_transaction_id=source_id,
    )
    return normalized


def normalize_exchange_rate_payload(payload, *, source_provider="cryptoapis"):
    payload = payload or {}
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    item = data.get("item") if isinstance(data.get("item"), dict) else data
    return {
        "source_provider": source_provider,
        "asset_symbol": item.get("fromAssetSymbol") or item.get("baseAssetSymbol") or "",
        "reporting_currency": item.get("toAssetSymbol") or item.get("quoteAssetSymbol") or "",
        "exchange_rate": _safe_float(item.get("rate")),
        "source_timestamp": _timestamp_to_iso(item.get("calculationTimestamp") or item.get("timestamp")),
        "payload_hash": compute_payload_hash(payload),
    }
