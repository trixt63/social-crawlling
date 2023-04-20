import click

from databases.social_users_db import SocialUsersDB
from socials.questn_users_crawler import QuestNUserCrawler
from socials.crew3_users_crawler import Crew3UserCrawler
from utils.logger_utils import get_logger

logger = get_logger('Crawl social account')


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.option('-o', '--output', type=str, help='User social DB')
@click.option('-f', '--file', type=str, help='File path')

@click.option('-b', '--batch-size', default=10000, show_default=True, type=int, help='Batch size')
@click.option('--min-submissions', default=0, show_default=True, type=int, help='Min submissions')
@click.option('--max-submissions', default=None, show_default=True, type=int, help='Max submissions')
def crawl_social_account(output, file,batch_size, min_submissions, max_submissions):
    """Crawl social account"""

    db = SocialUsersDB(output)

    crawler = Crew3UserCrawler()
    crawler.get_users(file =file,exporter= db)
    # crawler.get_users(user_batch_size=batch_size, min_submissions=min_submissions, max_submissions=max_submissions, exporter=db)
