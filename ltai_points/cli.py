"""Console script for ltai_points."""
import sys
import click
import asyncio
import math
from .settings import get_settings
from .ethereum import get_account, mint_tokens, get_all_previous_mints, get_web3
from .poster import post_state
from .ltai_points import compute_points
from .storage import get_dbs, close_dbs
from . import __version__
import logging


LOGGER = logging.getLogger(__name__)


def setup_logging(verbose):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    loglevel = [logging.WARNING, logging.INFO, logging.DEBUG][verbose]
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(
        level=loglevel, stream=sys.stdout, format=logformat, datefmt="%Y-%m-%d %H:%M:%S"
    )
    
async def process(settings, dbs, publish=False, mint=False):
    account = get_account(settings)
    LOGGER.info(f"Starting as address {account.get_address()}")
    points, pending_points, info = await compute_points(settings, dbs)
    if publish:
        await post_state(settings, points, pending_points, info)
    if mint:
        web3 = get_web3(settings)
        previous_mints = await get_all_previous_mints(settings, web3)
        print(previous_mints)
        to_send = {}
        for address, amount in points.items():
            if amount - previous_mints.get(address, 0) > 1:
                to_send[address] = amount - previous_mints.get(address, 0)
        print(to_send)

        max_items = settings['ethereum_batch_size']

        distribution_list = list(to_send.items())

        last_nonce = None

        for i in range(math.ceil(len(distribution_list) / max_items)):
            step_items = distribution_list[max_items * i : max_items * (i + 1)]
            print(f"doing batch {i} of {len(step_items)} items")
            tx_hash, last_nonce = await mint_tokens(settings, web3, dict(step_items), nonce=last_nonce)
            print(tx_hash, last_nonce)
            last_nonce += 1

    return points

@click.command()
@click.option('-v', '--verbose', count=True)
@click.option('-p', '--publish', is_flag=True, help='Publish the results to the aleph network')
@click.option('-m', '--mint', is_flag=True, help='Mint outstanding tokens')
@click.version_option(version=__version__)
def main(verbose, publish=False, mint=False, args=None):
    """Console script for ltai_points."""
    setup_logging(verbose)
    settings = get_settings()
    dbs = get_dbs(settings)
    asyncio.run(process(settings, dbs, publish, mint))
    close_dbs(dbs)
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
