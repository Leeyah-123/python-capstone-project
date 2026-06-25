"""
wallet.py

Higher-level abstraction for Bitcoin Core wallet operations.
"""

from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from rpc import BitcoinRPC


class Wallet:
    """
    Represents a single named Bitcoin Core wallet (e.g. "Miner" or "Trader").

    Responsibilities:
        - Create the wallet on the node if it doesn't exist yet.
        - Load the wallet if it exists but is not currently loaded.
        - Generate new labelled addresses.
        - Query the wallet balance.
        - Send BTC to another address.
    """

    def __init__(self, rpc: BitcoinRPC, name: str):
        """
        Args:
            rpc (BitcoinRPC): A BitcoinRPC instance that knows how to build clients.
            name (str): The exact wallet name, e.g. "Miner" or "Trader".
        """
        self.name = name

        # Wallet-scoped client: used for getbalance, getnewaddress,
        # sendtoaddress, and any other wallet-level RPC commands.
        self._client: AuthServiceProxy = rpc.get_wallet_client(name)

        # Node-level client: needed for createwallet and loadwallet,
        # which are not wallet-scoped commands.
        self._node_client: AuthServiceProxy = rpc.get_client()

    def create_or_load(self):
        """
        Ensure this wallet is loaded and ready to use.

        Bitcoin Core behaviour:
        - createwallet -> creates AND loads a brand-new wallet.
        - loadwallet   -> loads an existing (but unloaded) wallet.
        - If the wallet is already loaded, loadwallet raises an error.

        Here we:
        1. Try createwallet. If it succeeds, we're done.
        2. If it fails with "already exists" -> try loadwallet.
        3. If loadwallet fails with "already loaded" -> do nothing; it's
           already available.
        4. Any other exception -> re-raise so the caller knows something
           is wrong.
        """
        try:
            self._node_client.createwallet(self.name)
            print(f"Wallet '{self.name}' created.")
        except JSONRPCException as e:
            if "already exists" in str(e):
                # Wallet file is on disk but may or may not be loaded yet.
                try:
                    self._node_client.loadwallet(self.name)
                    print(f"Wallet '{self.name}' loaded.")
                except JSONRPCException as le:
                    if "already loaded" in str(le):
                        # Nothing to do - wallet is already live.
                        print(f"Wallet '{self.name}' was already loaded.")
                    else:
                        raise
            else:
                raise

    def get_new_address(self, label: str) -> str:
        """
        Generate and return a fresh bech32 address associated with *label*.

        Labels are used by Bitcoin Core to tag addresses for human-readable
        accounting (e.g. "Mining Reward", "Received").

        Args:
            label (str): A human-readable tag for the address.

        Returns:
            str: The new bech32 address string.
        """
        return self._client.getnewaddress(label)

    def get_balance(self) -> float:
        """
        Return the confirmed (≥1 confirmation) balance for this wallet in BTC.

        Returns:
            float: Wallet balance in BTC.
        """
        return self._client.getbalance()

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    def send_to_address(self, address: str, amount: float) -> str:
        """
        Broadcast a transaction paying *amount* BTC to *address*.

        Args:
            address (str): Destination bech32 address (e.g. Trader's address).
            amount (float): Amount in BTC (e.g. 20.0).

        Returns:
            str: The txid of the newly broadcast transaction.
        """
        txid = self._client.sendtoaddress(address, amount)
        return txid
