import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NORMALIZERS_PATH = ROOT / "crypto_payment_sync" / "services" / "normalizers.py"
spec = importlib.util.spec_from_file_location("normalizers", NORMALIZERS_PATH)
normalizers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(normalizers)


class NormalizerTests(unittest.TestCase):
    def test_evm_fixture_normalizes_to_reviewable_transaction(self):
        payload = json.loads((ROOT / "sample_data" / "cryptoapis_evm_transactions_sample.json").read_text())
        item = payload["data"]["items"][0]

        result = normalizers.normalize_evm_transaction_payload(
            item,
            source_provider="cryptoapis",
            network="ethereum-mainnet",
            account_reference="demo-account",
        )

        self.assertEqual(result["source_provider"], "cryptoapis")
        self.assertEqual(result["asset_symbol"], "ETH")
        self.assertEqual(result["quantity"], 0.75)
        self.assertEqual(result["processing_status"], "needs_review")
        self.assertEqual(result["transaction_type"], "unknown")
        self.assertTrue(result["payload_hash"])
        self.assertTrue(result["duplicate_key"])

    def test_duplicate_key_is_stable(self):
        first = normalizers.build_duplicate_key(
            source_provider="cryptoapis",
            network="ethereum-mainnet",
            account_reference="demo-account",
            transaction_hash="0xdemo",
        )
        second = normalizers.build_duplicate_key(
            source_provider="cryptoapis",
            network="ethereum-mainnet",
            account_reference="demo-account",
            transaction_hash="0xdemo",
        )
        self.assertEqual(first, second)

    def test_exchange_rate_fixture_normalizes(self):
        payload = json.loads((ROOT / "sample_data" / "cryptoapis_exchange_rates_sample.json").read_text())
        result = normalizers.normalize_exchange_rate_payload(payload)
        self.assertEqual(result["asset_symbol"], "ETH")
        self.assertEqual(result["reporting_currency"], "USD")
        self.assertEqual(result["exchange_rate"], 2500.00)


if __name__ == "__main__":
    unittest.main()
