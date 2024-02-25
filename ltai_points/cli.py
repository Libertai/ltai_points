"""Console script for ltai_points."""
import sys
import click
import asyncio
from .settings import get_settings
from .ethereum import get_account
from .poster import post_state
from .ltai_points import compute_points
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
    
async def process(settings, publish=False):
    account = get_account(settings)
    LOGGER.info(f"Starting as address {account.get_address()}")
    points, boosted_addresses = await compute_points(settings)
    if publish:
        await post_state(settings, points, boosted_addresses)
    return points

@click.command()
@click.option('-v', '--verbose', count=True)
@click.option('-p', '--publish', is_flag=True, help='Publish the results to the aleph network')
@click.version_option(version=__version__)
def main(verbose, publish=False, args=None):
    """Console script for ltai_points."""
    setup_logging(verbose)
    settings = get_settings()
    asyncio.run(process(settings, publish))
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
