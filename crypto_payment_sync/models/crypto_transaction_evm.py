import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

from datetime import datetime, timedelta

from eth_utils import to_checksum_address
from eth_account import Account

Account.enable_unaudited_hdwallet_features()

_logger = logging.getLogger(__name__)

class CryptoTransactionEVM(models.Model):
    _name = "crypto.transaction.evm"
    _description = "EVM Transactions"

    contract = fields.Char(string="Contract")
    tx_hash = fields.Char(string="Transaction Hash")
    name = fields.Char(related="tx_hash")
    input_data = fields.Char(string="Input Data")
    position_in_block = fields.Integer(string="Position In Block")
    recipient = fields.Char(string="Recipient Address")
    sender = fields.Char(string="Send Address")
    status = fields.Char(string="Status")
    timestamp = fields.Datetime(string="Time Stamp")

    # Fee
    fee_amount = fields.Float(string="Fee Amount")
    fee_unit = fields.Char(string="Fee Unit")

    # Value
    value_amount = fields.Float(string="Value Amount")
    value_unit = fields.Char(string="Value Unit")

    # Gas
    gas_limit = fields.Integer(string="Gas Limit")
    gas_used = fields.Integer(string="Gas Used")
    gas_price_amount = fields.Char(string="Gas Price Amount")
    gas_price_unit = fields.Char(string="Gas Price Unit")

    # Block info
    block_hash = fields.Char(string="Block Hash")
    block_height = fields.Integer(string="Block Height")

    # Blockchain specific
    bandwidth_used = fields.Integer(string="Bandwidth Used")
    energy_used = fields.Float(string="Energy Used")

    wallet_address_id = fields.Many2one("crypto.wallet.address", string="Wallet Address")

    wallet_id = fields.Many2one('crypto.wallet', related="wallet_address_id.wallet_id", string="Crypto Wallet")

    network_id = fields.Many2one('crypto.network', related="wallet_id.network_id", string="Network")

    blockchain_id = fields.Many2one('crypto.blockchain', related="network_id.blockchain_id", string="Blockchain")

    @api.model
    def create_from_json(self, data):
        """Create a TRX transaction record from a JSON response"""
        return self.create({
            'contract': data.get('contract'),
            'tx_hash': data.get('hash'),
            'input_data': data.get('inputData'),
            'position_in_block': data.get('positionInBlock'),
            'recipient': data.get('recipient'),
            'sender': data.get('sender'),
            'status': data.get('status'),
            'timestamp': datetime.utcfromtimestamp(data.get('timestamp')) if data.get('timestamp') else False,

            'fee_amount': float(data['fee']['amount']) if data.get('fee') else 0.0,
            'fee_unit': data['fee']['unit'] if data.get('fee') else '',

            'value_amount': float(data['value']['amount']) if data.get('value') else 0.0,
            'value_unit': data['value']['unit'] if data.get('value') else '',

            'gas_limit': data.get('gasLimit'),
            'gas_used': data.get('gasUsed'),

            'gas_price_amount': data['gasPrice']['amount'] if data.get('gasPrice') else '',
            'gas_price_unit': data['gasPrice']['unit'] if data.get('gasPrice') else '',

            'block_hash': data['minedInBlock']['hash'] if data.get('minedInBlock') else '',
            'block_height': data['minedInBlock']['height'] if data.get('minedInBlock') else '',

            'bandwidth_used': data['blockchainSpecific']['bandwidthUsed'] if data.get('blockchainSpecific') else 0,
            'energy_used': float(data['blockchainSpecific']['energyUsed']) if data.get(
                'blockchainSpecific') else 0.0,
        })

    @api.model
    def create_from_wallet_json(self, data):
        """Create a TRX transaction record from a JSON response"""
        return self.create({
            # 'contract': data.get('contract'),
            'tx_hash': data.get('hash'),
            'input_data': data.get('inputData'),
            'position_in_block': data.get('positionInBlock'),
            'recipient': data['recipient'][0]['address'],
            'sender': data['sender'][0]['address'],
            # 'status': data.get('status'),
            'timestamp': datetime.utcfromtimestamp(data.get('timestamp')) if data.get('timestamp') else False,

            'fee_amount': float(data['fee']['amount']) if data.get('fee') else 0.0,
            # 'fee_unit': data['fee']['unit'] if data.get('fee') else '',

            'value_amount': float(data['recipient'][0]['amount']) if data.get('recipient') else 0.0,
            # 'value_unit': data['value']['unit'] if data.get('value') else '',

            # 'gas_limit': data.get('gasLimit'),
            # 'gas_used': data.get('gasUsed'),

            # 'gas_price_amount': data['gasPrice']['amount'] if data.get('gasPrice') else '',
            # 'gas_price_unit': data['gasPrice']['unit'] if data.get('gasPrice') else '',

            'block_hash': data['minedInBlock']['hash'] if data.get('minedInBlock') else '',
            'block_height': data['minedInBlock']['height'] if data.get('minedInBlock') else '',

            # 'bandwidth_used': data['blockchainSpecific']['bandwidthUsed'] if data.get('blockchainSpecific') else 0,
            # 'energy_used': float(data['blockchainSpecific']['energyUsed']) if data.get(
            #     'blockchainSpecific') else 0.0,
        })

    @api.model
    def return_from_json(self, data):
        """Create a TRX transaction record from a JSON response"""
        return {
            'contract': data.get('contract'),
            'tx_hash': data.get('hash'),
            'input_data': data.get('inputData'),
            'position_in_block': data.get('positionInBlock'),
            'recipient': data.get('recipient'),
            'sender': data.get('sender'),
            'status': data.get('status'),
            'timestamp': datetime.utcfromtimestamp(data.get('timestamp')) if data.get('timestamp') else False,

            'fee_amount': float(data['fee']['amount']) if data.get('fee') else 0.0,
            'fee_unit': data['fee']['unit'] if data.get('fee') else '',

            'value_amount': float(data['value']['amount']) if data.get('value') else 0.0,
            'value_unit': data['value']['unit'] if data.get('value') else '',

            'gas_limit': data.get('gasLimit'),
            'gas_used': data.get('gasUsed'),

            'gas_price_amount': data['gasPrice']['amount'] if data.get('gasPrice') else '',
            'gas_price_unit': data['gasPrice']['unit'] if data.get('gasPrice') else '',

            'block_hash': data['minedInBlock']['hash'] if data.get('minedInBlock') else '',
            'block_height': data['minedInBlock']['height'] if data.get('minedInBlock') else '',

            # 'bandwidth_used': data['blockchainSpecific']['bandwidthUsed'] if data.get('blockchainSpecific') else 0,
            # 'energy_used': float(data['blockchainSpecific']['energyUsed']) if data.get(
            #     'blockchainSpecific') else 0.0,
        }



    def get_transaction_details(self):
        for record in self:

            # Check if more than one minute
            if record.tx_hash:
                blockchain = record.blockchain_id.name.lower()
                network = record.network_id.name.lower().replace('testnet', "").replace(blockchain, "").replace(" ",
                                                                                                                "")
                transactionHash = record.tx_hash
                if 'ether' in blockchain:
                    url = f"https://rest.cryptoapis.io/transactions/evm/{blockchain}/{network}/{transactionHash}?context=OdooGetTransactionDetails"
                if 'bitcoin' in blockchain:
                    url = f"https://rest.cryptoapis.io/transactions/utxo/{blockchain}/{network}/{transactionHash}?context=OdooGetTransactionDetails"
                if 'xrp' in blockchain:
                    url = f"https://rest.cryptoapis.io/transactions/{blockchain}/{network}/{transactionHash}?context=OdooGetTransactionDetails"
                provider = self.env['payment.provider'].search([('code', '=', 'crypto')])[0]
                headers = {
                    "X-API-Key": provider.cryptoapis_api_key
                }
                response = requests.get(url, headers=headers)
                if response.status_code != 200:
                    raise UserError((f"Failed to fetch crypto currencies: {response.text}"))
                _logger.info('response' + str(response))
                data = response.json().get("data", [])
                _logger.info('response Json Data' + str(data))
                item = data.get("item", [])
                _logger.info('response Json Item' + str(item))
                updated_data = self.return_from_json(item)
                record.write(updated_data)

    def prepare_native_tx(self):
        for record in self:
            blockchain = record.blockchain_id.name.lower()
            network = record.network_id.name.lower().replace('testnet', "").replace(blockchain, "").replace(" ","")
            extendedPublicKey =record.wallet_id.xpub
            if 'ether' in blockchain:
                # url = f"https://rest.cryptoapis.io/prepare-transactions/evm/{blockchain}/{network}/native-coins"
                url = f"https://rest.cryptoapis.io/hd-wallets/evm/{blockchain}/{network}/{extendedPublicKey}/transactions/prepare"
            if 'bitcoin' in blockchain:
                # url = f"https://rest.cryptoapis.io/prepare-transactions/utxo/{blockchain}/{network}/native-coins"
                url = f"https://rest.cryptoapis.io/hd-wallets/utxo/{blockchain}/{network}/{extendedPublicKey}/transactions/prepare"
            if 'xrp' in blockchain:
                # url = f"https://rest.cryptoapis.io/prepare-transactions/{blockchain}/{network}/native-coins"
                url = f"https://rest.cryptoapis.io/hd-wallets/{blockchain}/{network}/{extendedPublicKey}/transactions/prepare"
            provider = self.env['payment.provider'].search([('code', '=', 'crypto')])[0]
            headers = {
                "X-API-Key": provider.cryptoapis_api_key
            }
            from decimal import Decimal

            amount_eth = Decimal(str(record.value_amount))
            payload = {
                "context": "odoo_prepare_native",
                "data": {
                    "item": {
                        "additionalData": "Tansfer",
                        "sender": record.sender,
                        "recipient": record.recipient,
                        # "amount": str(int(record.value_amount*1000000000000000000)),
                        "amount": format(amount_eth, "f"),
                        "fee": {"priority": "standard"},
                        "transactionType": "legacy-transaction",
                    }
                }
            }
            if record.input_data is not None:
                payload["data"]["item"]["nonce"] = str(0)

            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code != 200:
                raise UserError(f"Failed to fetch crypto currencies: {response.text}")
            # response.raise_for_status()
            return response.json()["data"]["item"]

    def broadcast_signed_tx(self,signed_tx_hex):
        for record in self:
            blockchain = record.blockchain_id.name.lower()

            network = record.network_id.name.lower().replace('testnet', "").replace(blockchain, "").replace(" ","")
            if 'ether' in blockchain:
                url = f"https://rest.cryptoapis.io/broadcast-transactions/{blockchain}/{network}"
            if 'bitcoin' in blockchain:
                url = f"https://rest.cryptoapis.io/broadcast-transactions/{blockchain}/{network}"
            if 'xrp' in blockchain:
                url = f"https://rest.cryptoapis.io/broadcast-transactions/{blockchain}/{network}"
            provider = self.env['payment.provider'].search([('code', '=', 'crypto')])[0]
            headers = {
                "X-API-Key": provider.cryptoapis_api_key
            }
            payload = {
                "context": "odoo_broadcast",
                "data": {"item": {"signedTransactionHex": signed_tx_hex}}
            }
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code != 200:
                raise UserError(f"Failed to fetch crypto currencies: {response.text}")
            response.raise_for_status()
            tx_id = response.json()["data"]["item"]["transactionId"]
            record.write({'tx_hash':tx_id})
            return response.json()["data"]["item"]["transactionId"]

    def sign_transaction(self, tx, private_key):
        # private_key bytes -> hex
        if isinstance(private_key, bytes):
            private_key = private_key.hex()

        # ✅ checksum address
        if tx.get("to"):
            # tx["to"] = Web3.to_checksum_address(tx["to"])
            tx["to"] = to_checksum_address(tx["to"])

        # ✅ normalize required fields types
        if "value" in tx:
            tx["value"] = int(tx["value"])
        if "chainId" in tx:
            tx["chainId"] = int(tx["chainId"])
        if "nonce" in tx:
            tx["nonce"] = int(tx["nonce"])
        if "gas" in tx:
            tx["gas"] = int(tx["gas"])

        # ✅ data must be hex string
        if not tx.get("data"):
            tx["data"] = "0x"
        elif isinstance(tx["data"], str) and not tx["data"].startswith("0x"):
            tx["data"] = "0x" + tx["data"]

        # ✅ fees must be int
        if tx.get("gasPrice") is not None:
            tx["gasPrice"] = int(tx["gasPrice"])
        if tx.get("maxFeePerGas") is not None:
            tx["maxFeePerGas"] = int(tx["maxFeePerGas"])
        if tx.get("maxPriorityFeePerGas") is not None:
            tx["maxPriorityFeePerGas"] = int(tx["maxPriorityFeePerGas"])

        try:
            return Account.sign_transaction(tx, private_key)
        except Exception as e:
            raise UserError(f"Transaction signing failed: {str(e)}")

    def send_native_from_odoo(self):
        # 1) nonce (اختياري لكن مفيد)
        for record in self:

            # 2) prepare
            prepared = record.prepare_native_tx()
            i, privkey = record._find_privkey_for_address()
            if privkey is None:
                raise UserError(
                    "Could not derive private key for sender address from stored mnemonic. Check derivation path/index.")

            # 3) build tx object for local signing

            tx = {
                "nonce": int(prepared["nonce"]),
                "to": prepared["recipient"],
                "value": prepared["value"]["amount"],  # هيتحول int في normalize
                "gas": int(prepared["gasLimit"]),
                "data": prepared.get("inputData") or "0x",
                "chainId": record.network_id.chain_id,
            }

            # fees: لو legacy استخدم gasPrice. لو EIP-1559 استخدم maxFeePerGas/maxPriorityFeePerGas
            fee = prepared["fee"]
            if prepared.get("type") == "legacy-transaction":
                tx["gasPrice"] = int(fee["gasPrice"])
            else:
                tx["maxFeePerGas"] = int(fee["maxFeePerGas"])
                tx["maxPriorityFeePerGas"] = int(fee["maxPriorityFeePerGas"])

            signed = record.sign_transaction(tx, privkey)
            raw = getattr(signed, "rawTransaction", None) or getattr(signed, "raw_transaction", None)
            if raw is None:
                raise UserError(f"SignedTransaction missing raw tx bytes. Available: {dir(signed)}")

            # raw ممكن يكون HexBytes أو bytes أو str
            if isinstance(raw, (bytes, bytearray)):
                signed_hex = "0x" + raw.hex()
            else:
                # HexBytes بيطلع .hex()، وstr غالباً already 0x..
                signed_hex = raw.hex() if hasattr(raw, "hex") else str(raw)

            # 4) broadcast
            txid = record.broadcast_signed_tx(signed_hex)
            # record.write({'tx_hash':str(signed_hex)})
            return txid

    def _find_privkey_for_address(self):
        for record in self:
            if not (record.wallet_id and record.wallet_id.mnemonic):
                return None, None

            target = (record.sender or "").lower().strip()

            # جرّب أشهر paths
            paths = [
                "m/44'/60'/0'/0/{i}",  # standard (MetaMask)
                "m/44'/60'/0'/1/{i}",  # change=1 (أحيانًا)
            ]

            for base in paths:
                for i in range(0, 201):  # وسّع البحث شوية
                    path = base.format(i=i)
                    acct = Account.from_mnemonic(record.wallet_id.mnemonic, account_path=path)
                    if acct.address.lower() == target:
                        return i, acct.key

            return None, None


    def _normalize_evm_tx(self, tx):
        # to checksum
        if tx.get("to"):
            tx["to"] = to_checksum_address(tx["to"])

        # value int
        if "value" in tx:
            tx["value"] = int(tx["value"])

        # chainId int
        if "chainId" in tx:
            tx["chainId"] = int(tx["chainId"])

        # nonce/gas int
        if "nonce" in tx:
            tx["nonce"] = int(tx["nonce"])
        if "gas" in tx:
            tx["gas"] = int(tx["gas"])

        # data must be hex string
        data = tx.get("data")
        if not data:
            tx["data"] = "0x"
        elif isinstance(data, str) and not data.startswith("0x"):
            tx["data"] = "0x" + data

        # fees int
        if "gasPrice" in tx:
            tx["gasPrice"] = int(tx["gasPrice"])
        if "maxFeePerGas" in tx:
            tx["maxFeePerGas"] = int(tx["maxFeePerGas"])
        if "maxPriorityFeePerGas" in tx:
            tx["maxPriorityFeePerGas"] = int(tx["maxPriorityFeePerGas"])

        return tx
