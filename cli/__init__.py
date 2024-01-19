import click

from cli.crawl_social_account import crawl_social_account
from cli.crawl_zealy import crawl_zealy


@click.group()
@click.version_option(version='1.0.0')
@click.pass_context
def cli(ctx):
    # Command line
    pass


cli.add_command(crawl_zealy, 'crawl_zealy')
