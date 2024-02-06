import click

from socials.zealy_users_crawler import ZealyUserCrawler
from databases.social_users_db import SocialUsersDB
from utils.logger_utils import get_logger

logger = get_logger('Crawl Zealy')


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.option('-r', '--refresh', is_flag=True, help='Get new community file')
@click.option('-f', '--file', type=str, default='data/zealy_communities.json', show_default=True,
              help='Communities file path')
@click.option('-s', '--start-idx', default=0, show_default=True, type=int,
              help='Start index in communities file')
@click.option('-b', '--batch-size', default=50, show_default=True, type=int,
              help='Batch size for crawling new communities')
def crawl_zealy(refresh, file, start_idx ,batch_size):
    db = SocialUsersDB()
    crawler = ZealyUserCrawler(batch_size=batch_size,
                               communities_file=file,
                               database=db)

    if refresh:
        crawler.get_top_communities()
    crawler.get_users(start_community_idx=start_idx)
