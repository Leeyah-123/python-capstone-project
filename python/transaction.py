"""
transaction.py

Helpers for inspecting a transaction and assembling the data needed for out.txt.
"""

from bitcoinrpc.authproxy import AuthServiceProxy
from rpc import BitcoinRPC


class Transaction:
    """
    Wraps a single Bitcoin transaction identified by its txid.

    Responsibilities:
    - Fetch the mempool entry (before confirmation).
    - Fetch and decode the raw transaction (after confirmation) so we can
      pull inputs, outputs, fees, block height, and block hash.
    - Expose a formatted string for writing to out.txt.
    """

    def __init__(self, rpc: BitcoinRPC, txid: str):
        """
        Args:
            rpc (BitcoinRPC): A BitcoinRPC instance.
            txid (str): The transaction ID returned by sendtoaddress.
        """
        self.txid = txid

        # Store the node-level client for getrawtransaction, getblock, etc.
        self._client: AuthServiceProxy = rpc.get_client()

        # Internal cache: populated by _load_decoded_tx()
        self._raw_tx: dict = {}

    def get_mempool_entry(self) -> dict:
        """
        Fetch the mempool entry for this transaction.

        Returns the result of `getmempoolentry <txid>`.
        This only works *before* the tx is confirmed (i.e. while it is
        still in the mempool). After a block mines it, this call will
        raise an error, so use get_decoded_tx() instead.

        Returns:
            dict: Keys include 'fees', 'size', 'time', etc.
        """
        return self._client.getmempoolentry(self.txid)

    def _load_decoded_tx(self):
        """
        Private helper: fetch and cache the verbose (decoded) raw transaction.

        We pass verbose=True to getrawtransaction so Bitcoin Core returns
        a dict instead of a hex string. This dict contains:
          - 'vin': list of inputs  (txid + vout index of each input UTXO)
          - 'vout': list of outputs (value + scriptPubKey with address)
          - 'blockhash', 'blockheight' (only present once confirmed)
        """
        if not self._raw_tx:
            self._raw_tx = self._client.getrawtransaction(self.txid, True)

    def get_decoded_tx(self) -> dict:
        """
        Return the full decoded transaction dict (cached after first call).

        Returns:
            dict: The full verbose decoded transaction.
        """
        self._load_decoded_tx()
        return self._raw_tx

    def get_input_details(self) -> dict:
        """
        Resolve the transaction's inputs back to their source addresses
        and amounts.

        Bitcoin transactions store only a reference to the UTXO being spent
        (previous txid + output index) and not the address or value directly.
        To recover those we must:
          1. Look up the previous transaction via getrawtransaction.
          2. Index into its 'vout' list with the stored vout index.
          3. Read the address and value from that output.

        Returns:
            dict: Keys 'address' (str) and 'amount' (float, in BTC).
        """
        decoded = self.get_decoded_tx()

        # Assume a single input
        vin = decoded['vin'][0]
        prev_txid = vin['txid']
        prev_vout_index = vin['vout']

        # Fetch the previous transaction to read the output being spent.
        prev_tx = self._client.getrawtransaction(prev_txid, True)
        prev_out = prev_tx['vout'][prev_vout_index]

        return {
            'address': prev_out['scriptPubKey']['address'],
            'amount': prev_out['value'],
        }

    def get_output_details(self, trader_address: str) -> dict:
        """
        Split vout into Trader's payment output and Miner's change output.

        The outputs are identified by matching their address against the
        known Trader address. The remaining output is treated as change.

        Args:
            trader_address (str): The address we sent BTC to.

        Returns:
            dict: Keys 'trader_address', 'trader_amount', 'change_address',
                'change_amount'.
        """
        decoded = self.get_decoded_tx()

        trader_out = None
        change_out = None

        for vout in decoded['vout']:
            addr = vout['scriptPubKey'].get('address', '')
            if addr == trader_address:
                trader_out = vout
            else:
                # The only other output is the miner's change
                change_out = vout

        return {
            'trader_address': trader_out['scriptPubKey']['address'],
            'trader_amount': trader_out['value'],
            'change_address': change_out['scriptPubKey']['address'],
            'change_amount': change_out['value'],
        }

    def get_fee(self, miner_wallet_client: AuthServiceProxy) -> float:
        """
        Return the transaction fee in BTC.

        We use gettransaction (wallet-level) because it directly reports the
        fee field, avoiding the need to manually subtract inputs from outputs.
        The returned fee is negative as it represents money leaving the wallet.

        Args:
            miner_wallet_client (AuthServiceProxy): Wallet-scoped RPC client for
                the Miner wallet, which knows the fee for its own transactions.

        Returns:
            float: Transaction fee in BTC (negative value, e.g. -0.0000141).
        """
        tx_details = miner_wallet_client.gettransaction(self.txid)
        return tx_details['fee']

    def get_block_info(self) -> dict:
        """
        Return the block height and block hash where this tx was confirmed.

        These fields are present on the decoded raw transaction once it
        has been mined into a block. We then call getblock to get the height.

        Returns:
            dict: Keys 'block_height' (int) and 'block_hash' (str).
        """
        decoded = self.get_decoded_tx()
        blockhash = decoded['blockhash']

        # getblock returns block metadata including the height field
        block = self._client.getblock(blockhash)

        return {
            'block_hash': blockhash,
            'block_height': block['height'],
        }

    def build_output_lines(self, miner_wallet_client: AuthServiceProxy, trader_address: str) -> list:
        """
        Assemble all required fields and return them as a list of strings (one per output line).

        Order:
          1. txid
          2. Miner's Input Address
          3. Miner's Input Amount (BTC)
          4. Trader's Output Address
          5. Trader's Output Amount (BTC)
          6. Miner's Change Address
          7. Miner's Change Amount (BTC)
          8. Transaction Fee (BTC)
          9. Block height
         10. Block hash

        Args:
            miner_wallet_client (AuthServiceProxy): Wallet-scoped client for the Miner,
                passed through to get_fee.
            trader_address (str): The address Trader's payment was sent to.

        Returns:
            list[str]: A list of 10 strings in the specified order, to be joined by newlines.
        """
        input_details = self.get_input_details()
        output_details = self.get_output_details(trader_address)
        block_details = self.get_block_info()
        fee = self.get_fee(miner_wallet_client)

        return [
            self.txid,
            input_details['address'],
            str(input_details['amount']),
            output_details['trader_address'],
            str(output_details['trader_amount']),
            output_details['change_address'],
            str(output_details['change_amount']),
            str(fee),
            str(block_details['block_height']),
            block_details['block_hash'],
        ]
