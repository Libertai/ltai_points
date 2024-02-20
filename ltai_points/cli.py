"""Console script for ltai_points."""
import sys
import click
import asyncio
from .settings import get_settings
from .ethereum import get_account
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

@click.command()
@click.option('-v', '--verbose', count=True)
@click.version_option(version=__version__)
def main(verbose, args=None):
    """Console script for ltai_points."""
    setup_logging(verbose)
    settings = get_settings()
    print(settings)
    account = get_account(settings)
    LOGGER.info(f"Starting as address {account.get_address()}")
    asyncio.run(compute_points(settings))
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
