"""
bitcoin_rpc.py

Low-level wrapper around AuthServiceProxy, 
responsible for creating RPC connections for both general (node-level) 
and wallet-scoped (wallet-level).
"""

from bitcoinrpc.authproxy import AuthServiceProxy


class BitcoinRPC:
    """
    Thin wrapper around AuthServiceProxy that manages RPC connections
    to a Bitcoin Core node.

    Separated so that:
    - The base URL and credentials live in one place.
    - It is easy to swap to a different transport (e.g. a test stub)
    - Wallet-scoped vs node-scoped URLs are explicit.
    """

    def __init__(self, base_url: str):
        """
        Store the base RPC URL and create the general node-level client.

        Args:
            base_url (str): e.g. "http://alice:password@127.0.0.1:18443"
        """
        self.base_url = base_url
        self._client = AuthServiceProxy(self.base_url)

    def get_client(self) -> AuthServiceProxy:
        """
        Return the general, wallet-agnostic RPC client.
        Used for commands that don't belong to a specific wallet,
        e.g. getblockchaininfo, getblock, getrawtransaction, etc.

        Returns:
            AuthServiceProxy: The general RPC client.
        """
        return self._client

    def get_wallet_client(self, wallet_name: str) -> AuthServiceProxy:
        """
        Return an RPC client scoped to the given wallet which looks like:

            http://<user>:<pass>@<host>:<port>/wallet/<wallet_name>

        Args:
            wallet_name (str): The exact wallet name, e.g. "Miner" or "Trader"

        Returns:
            AuthServiceProxy: An AuthServiceProxy pointed at that wallet endpoint
        """
        wallet_url = f"{self.base_url}/wallet/{wallet_name}"
        return AuthServiceProxy(wallet_url)

    def get_blockchain_info(self) -> dict:
        """
        Call getblockchaininfo and return the result dict.

        Returns:
            dict: The result of getblockchaininfo.
        """
        return self._client.getblockchaininfo()
