"""Console script for ltai_points."""
import sys
import click
from .settings import Settings

@click.command()
def main(args=None):
    """Console script for ltai_points."""
    settings = Settings()
    click.echo(settings.api_endpoint)
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
