from odoo import models, fields, api, _
from odoo.exceptions import UserError

from datetime import datetime

from eth_utils import to_checksum_address
from eth_account import Account

Account.enable_unaudited_hdwallet_features()

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

    def _cryptoapis_provider(self):
        self.ensure_one()
        provider = self.wallet_id.payment_provider_id or self.env['payment.provider'].search([('code', '=', 'crypto')], limit=1)
        if not provider:
            raise UserError(_("Configure the Crypto payment provider before calling Crypto APIs."))
        provider._cryptoapis_headers()
        return provider

    def _cryptoapis_path_parts(self):
        self.ensure_one()
        if self.wallet_id:
            return self.wallet_id._cryptoapis_path_parts()
        blockchain = self.blockchain_id.cryptoapis_slug or self.blockchain_id.technical_name or self.blockchain_id.name
        network = self.network_id.cryptoapis_network or self.network_id.technical_name or self.network_id.name
        blockchain = (blockchain or "").lower().strip()
        network = (network or "").lower().strip()
        if not blockchain or not network:
            raise UserError(_("Set Crypto APIs blockchain and network codes before calling Crypto APIs."))
        if self.network_id.is_evm_compatible or "ether" in blockchain or blockchain in ("ethereum", "polygon", "base"):
            family = "evm"
        elif "bitcoin" in blockchain:
            family = "utxo"
        else:
            family = None
        return family, blockchain, network

    def _cryptoapis_family_path(self, prefix, suffix):
        self.ensure_one()
        family, blockchain, network = self._cryptoapis_path_parts()
        family_prefix = "%s/" % family if family else ""
        return f"{prefix}/{family_prefix}{blockchain}/{network}/{suffix.lstrip('/')}"

    @api.model
    def create_from_json(self, data):
        """Create a TRX transaction record from a JSON response"""
        fee = data.get('fee') or {}
        value = data.get('value') or {}
        gas_price = data.get('gasPrice') or {}
        mined = data.get('minedInBlock') or {}
        blockchain_specific = data.get('blockchainSpecific') or {}
        return self.create({
            'contract': data.get('contract'),
            'tx_hash': data.get('hash'),
            'input_data': data.get('inputData'),
            'position_in_block': data.get('positionInBlock'),
            'recipient': data.get('recipient'),
            'sender': data.get('sender'),
            'status': data.get('status'),
            'timestamp': datetime.utcfromtimestamp(data.get('timestamp')) if data.get('timestamp') else False,
            'fee_amount': float(fee.get('amount') or 0),
            'fee_unit': fee.get('unit') or '',
            'value_amount': float(value.get('amount') or 0),
            'value_unit': value.get('unit') or '',
            'gas_limit': data.get('gasLimit'),
            'gas_used': data.get('gasUsed'),
            'gas_price_amount': gas_price.get('amount') or '',
            'gas_price_unit': gas_price.get('unit') or '',
            'block_hash': mined.get('hash') or '',
            'block_height': mined.get('height') or 0,
            'bandwidth_used': blockchain_specific.get('bandwidthUsed') or 0,
            'energy_used': float(blockchain_specific.get('energyUsed') or 0),
        })

    @api.model
    def create_from_wallet_json(self, data):
        """Create a TRX transaction record from a JSON response"""
        recipients = data.get('recipient') or []
        senders = data.get('sender') or []
        first_recipient = recipients[0] if recipients else {}
        first_sender = senders[0] if senders else {}
        fee = data.get('fee') or {}
        mined = data.get('minedInBlock') or {}
        return self.create({
            'tx_hash': data.get('hash'),
            'input_data': data.get('inputData'),
            'position_in_block': data.get('positionInBlock'),
            'recipient': first_recipient.get('address') or '',
            'sender': first_sender.get('address') or '',
            'timestamp': datetime.utcfromtimestamp(data.get('timestamp')) if data.get('timestamp') else False,
            'fee_amount': float(fee.get('amount') or 0),
            'value_amount': float(first_recipient.get('amount') or 0),
            'block_hash': mined.get('hash') or '',
            'block_height': mined.get('height') or 0,
        })

    @api.model
    def return_from_json(self, data):
        """Create a TRX transaction record from a JSON response"""
        fee = data.get('fee') or {}
        value = data.get('value') or {}
        gas_price = data.get('gasPrice') or {}
        mined = data.get('minedInBlock') or {}
        return {
            'contract': data.get('contract'),
            'tx_hash': data.get('hash'),
            'input_data': data.get('inputData'),
            'position_in_block': data.get('positionInBlock'),
            'recipient': data.get('recipient'),
            'sender': data.get('sender'),
            'status': data.get('status'),
            'timestamp': datetime.utcfromtimestamp(data.get('timestamp')) if data.get('timestamp') else False,
            'fee_amount': float(fee.get('amount') or 0),
            'fee_unit': fee.get('unit') or '',
            'value_amount': float(value.get('amount') or 0),
            'value_unit': value.get('unit') or '',
            'gas_limit': data.get('gasLimit'),
            'gas_used': data.get('gasUsed'),
            'gas_price_amount': gas_price.get('amount') or '',
            'gas_price_unit': gas_price.get('unit') or '',
            'block_hash': mined.get('hash') or '',
            'block_height': mined.get('height') or 0,
        }



    def get_transaction_details(self):
        for record in self:

            # Check if more than one minute
            if record.tx_hash:
                transactionHash = record.tx_hash
                provider = record._cryptoapis_provider()
                data = provider._cryptoapis_get(
                    record._cryptoapis_family_path("transactions", transactionHash),
                    params={"context": "OdooGetTransactionDetails"},
                ).get("data") or {}
                item = data.get("item") or {}
                updated_data = self.return_from_json(item)
                record.write(updated_data)

    def prepare_native_tx(self):
        for record in self:
            provider = record._cryptoapis_provider()
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

            return provider._cryptoapis_post(
                record.wallet_id._cryptoapis_hd_wallet_path("transactions/prepare"),
                payload=payload,
            )["data"]["item"]

    def broadcast_signed_tx(self,signed_tx_hex):
        for record in self:
            provider = record._cryptoapis_provider()
            _family, blockchain, network = record._cryptoapis_path_parts()
            payload = {
                "context": "odoo_broadcast",
                "data": {"item": {"signedTransactionHex": signed_tx_hex}}
            }
            response_data = provider._cryptoapis_post(
                f"broadcast-transactions/{blockchain}/{network}",
                payload=payload,
            )
            tx_id = response_data["data"]["item"]["transactionId"]
            record.write({'tx_hash':tx_id})
            return tx_id

    def sign_transaction(self, tx, private_key):
        # private_key bytes -> hex
        if isinstance(private_key, bytes):
            private_key = private_key.hex()

        # Normalize recipient address format.
        if tx.get("to"):
            # tx["to"] = Web3.to_checksum_address(tx["to"])
            tx["to"] = to_checksum_address(tx["to"])

        # Normalize required field types.
        if "value" in tx:
            tx["value"] = int(tx["value"])
        if "chainId" in tx:
            tx["chainId"] = int(tx["chainId"])
        if "nonce" in tx:
            tx["nonce"] = int(tx["nonce"])
        if "gas" in tx:
            tx["gas"] = int(tx["gas"])

        # Data must be a hex string.
        if not tx.get("data"):
            tx["data"] = "0x"
        elif isinstance(tx["data"], str) and not tx["data"].startswith("0x"):
            tx["data"] = "0x" + tx["data"]

        # Fees must be integers.
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
        # Prepare and sign only when the caller has explicitly enabled broadcast.
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
