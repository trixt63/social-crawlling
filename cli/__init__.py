import click

from cli.crawl_zealy import crawl_zealy
from cli.crawl_questn import crawl_questn


@click.group()
@click.version_option(version='1.0.0')
@click.pass_context
def cli(ctx):
    # Command line
    pass


cli.add_command(crawl_zealy, 'crawl_zealy')
cli.add_command(crawl_questn, 'crawl_questn')
