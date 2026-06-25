"""
main.py

Entry point.

High-level flow
---------------
1.  Connect to the node.
2.  Create / load the Miner and Trader wallets.
3.  Mine enough blocks so Miner has a spendable balance.
4.  Generate a labelled receiving address for Trader.
5.  Send 20 BTC from Miner to Trader.
6.  Inspect the unconfirmed transaction in the mempool.
7.  Mine 1 block to confirm the transaction.
8.  Extract all required tx details and write them to ../out.txt.
"""

import os
from rpc import BitcoinRPC
from wallet import Wallet
from transaction import Transaction

# Configuration

RPC_URL = "http://alice:password@127.0.0.1:18443"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "out.txt")

# Number of blocks required before the first coinbase reward matures.
MATURITY_BLOCKS = 101


def mine_blocks(rpc: BitcoinRPC, address: str, count: int):
    """
    Mine *count* blocks, directing all block rewards to *address*.

    Uses the node-level `generatetoaddress` RPC call (only available in regtest mode).

    Args:
        rpc (BitcoinRPC): A BitcoinRPC instance (for the general/node client).
        address (str): The address that will receive the coinbase reward.
        count (int): How many blocks to generate.
    """
    client = rpc.get_client()
    client.generatetoaddress(count, address)
    print(f"Mined {count} block(s) to {address}")


def write_output(lines: list, filepath: str):
    """
    Write *lines* to *filepath*, one item per line, ending with a newline.

    Args:
        lines (list[str]): List of strings (10 items, see README output format).
        filepath (str): Absolute or relative path to out.txt.
    """
    with open(filepath, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print(f"Output written to {filepath}")


def main():
    try:
        # Step 1: Connect to the Bitcoin node
        rpc = BitcoinRPC(RPC_URL)

        # Confirm the node is reachable before starting.
        blockchain_info = rpc.get_blockchain_info()
        print("Blockchain Info:", blockchain_info)

        # Step 2: Create / load the Miner and Trader wallets
        miner = Wallet(rpc, "Miner")
        trader = Wallet(rpc, "Trader")

        miner.create_or_load()
        trader.create_or_load()

        # Step 3: Generate a labelled mining-reward address for Miner
        mining_address = miner.get_new_address("Mining Reward")
        print("Mining address:", mining_address)

        # Step 4: Mine enough blocks to get a spendable Miner balance
        # Note: In Bitcoin, coinbase outputs (block rewards) are
        # unspendable until the block is at least 100 blocks deep (the
        # "coinbase maturity" rule). That means you must mine at least 101
        # blocks before the first reward becomes spendable, which is why
        # the Miner wallet needs ~101 blocks before it shows a positive balance.
        mine_blocks(rpc, mining_address, MATURITY_BLOCKS)

        # Print balance to confirm it is now positive
        miner_balance = miner.get_balance()
        print(
            f"Miner balance after {MATURITY_BLOCKS} blocks: {miner_balance} BTC")

        # Step 5: Generate a labelled receiving address for Trader
        trader_address = trader.get_new_address("Received")
        print("Trader address:", trader_address)

        # Step 6: Send 20 BTC from Miner to Trader
        txid = miner.send_to_address(trader_address, 20.0)
        print(f"Transaction sent. txid: {txid}")

        # Step 7: Inspect the unconfirmed transaction in the mempool
        tx = Transaction(rpc, txid)
        mempool_entry = tx.get_mempool_entry()
        print("Mempool entry:", mempool_entry)

        # Step 8: Mine 1 block to confirm the transaction
        mine_blocks(rpc, mining_address, 1)
        print("Mined 1 block — transaction confirmed.")

        # Step 9: Extract all required transaction details
        output_lines = tx.build_output_lines(miner._client, trader_address)

        # Step 10: Write the data to ../out.txt
        write_output(output_lines, OUTPUT_FILE)

    except Exception as e:
        print("Error occurred: {}".format(e))
        raise  # To fail the test


if __name__ == "__main__":
    main()
