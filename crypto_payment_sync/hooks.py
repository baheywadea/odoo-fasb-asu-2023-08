from odoo import api, SUPERUSER_ID


CRYPTO_ASSETS = [
    {
        "xmlid": "crypto_asset_btc",
        "name": "BTC",
        "full_name": "Bitcoin",
        "symbol": "BTC",
        "currency_unit_label": "BTC",
        "currency_subunit_label": "satoshi",
        "rounding": 0.00000001,
    },
    {
        "xmlid": "crypto_asset_eth",
        "name": "ETH",
        "full_name": "Ether",
        "symbol": "ETH",
        "currency_unit_label": "ETH",
        "currency_subunit_label": "wei",
        "rounding": 0.00000001,
    },
    {
        "xmlid": "crypto_asset_usdt",
        "name": "USDT",
        "full_name": "Tether USD",
        "symbol": "USDT",
        "currency_unit_label": "USDT",
        "currency_subunit_label": "USDT",
        "rounding": 0.000001,
    },
    {
        "xmlid": "crypto_asset_usdc",
        "name": "USDC",
        "full_name": "USD Coin",
        "symbol": "USDC",
        "currency_unit_label": "USDC",
        "currency_subunit_label": "USDC",
        "rounding": 0.000001,
    },
    {
        "xmlid": "crypto_asset_bnb",
        "name": "BNB",
        "full_name": "BNB",
        "symbol": "BNB",
        "currency_unit_label": "BNB",
        "currency_subunit_label": "BNB",
        "rounding": 0.00000001,
    },
    {
        "xmlid": "crypto_asset_sol",
        "name": "SOL",
        "full_name": "Solana",
        "symbol": "SOL",
        "currency_unit_label": "SOL",
        "currency_subunit_label": "lamport",
        "rounding": 0.000000001,
    },
    {
        "xmlid": "crypto_asset_matic",
        "name": "MATIC",
        "full_name": "Polygon",
        "symbol": "MATIC",
        "currency_unit_label": "MATIC",
        "currency_subunit_label": "MATIC",
        "rounding": 0.00000001,
    },
    {
        "xmlid": "crypto_asset_avax",
        "name": "AVAX",
        "full_name": "Avalanche",
        "symbol": "AVAX",
        "currency_unit_label": "AVAX",
        "currency_subunit_label": "AVAX",
        "rounding": 0.00000001,
    },
]


def post_init_hook(env_or_cr, registry=None):
    if registry is None:
        env = env_or_cr
    else:
        env = api.Environment(env_or_cr, SUPERUSER_ID, {})
    _upsert_crypto_assets(env)


def _upsert_crypto_assets(env):
    Currency = env["res.currency"].with_context(active_test=False).sudo()
    ModelData = env["ir.model.data"].sudo()
    module = "crypto_payment_sync"

    for asset in CRYPTO_ASSETS:
        xmlid = asset["xmlid"]
        values = {
            "name": asset["name"],
            "full_name": asset["full_name"],
            "symbol": asset["symbol"],
            "currency_unit_label": asset["currency_unit_label"],
            "currency_subunit_label": asset["currency_subunit_label"],
            "rounding": asset["rounding"],
            "type": "crypto",
            "active": True,
        }
        currency = Currency.search([("name", "=", asset["name"])], limit=1)
        if currency:
            currency.write(values)
        else:
            currency = Currency.create(values)

        existing_xmlid = ModelData.search([
            ("module", "=", module),
            ("name", "=", xmlid),
            ("model", "=", "res.currency"),
        ], limit=1)
        if existing_xmlid:
            if existing_xmlid.res_id != currency.id:
                existing_xmlid.write({"res_id": currency.id})
        else:
            ModelData.create({
                "module": module,
                "name": xmlid,
                "model": "res.currency",
                "res_id": currency.id,
                "noupdate": True,
            })
