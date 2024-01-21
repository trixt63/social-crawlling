import click

from databases.social_users_db import SocialUsersDB
from socials.questn_users_crawler import QuestNUserCrawler
from socials.crew3_users_crawler import ZealyUserCrawler
from socials.crew3_users_crawler_old import Crew3UserCrawler_old
from utils.logger_utils import get_logger

logger = get_logger('Crawl social account')


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.option('-o', '--output', type=str, default=None, help='User social DB')
@click.option('-od', '--output-database', type=str, default=None, help='DB Database name')
@click.option('-f', '--file', type=str, default='data/zealy_communities.json', show_default=True,
              help='File path')
@click.option('-b', '--batch-size', default=50, show_default=True, type=int, help='Batch size')
def crawl_zealy(output, output_database, file, batch_size):
    db = SocialUsersDB(connection_url=output, database=output_database)
    crawler = ZealyUserCrawler(batch_size=batch_size,
                               communities_file=file,
                               database=db)
    # crawler_old = Crew3UserCrawler_old()

    # crawler.get_top_communities()
    crawler.get_users()
    # crawler_old.get_users()
