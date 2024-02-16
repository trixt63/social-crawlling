import click

from socials.questn_users_crawler import QuestNUserCrawler
from databases.social_users_db import SocialUsersDB
from utils.logger_utils import get_logger

logger = get_logger('Crawl QuestN')


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.option( '-r', '--refresh', is_flag=True,
               help='Refresh (Get new) quests file')
@click.option('-f', '--file', type=str, default='data/questn_quests.json', show_default=True,
              help='Quests file path')
@click.option('-s', '--start-idx', default=0, show_default=True, type=int,
              help='Start index in quests file')
# @click.option('-b', '--batch-size', default=50, show_default=True, type=int,
#               help='Batch size for crawling new quests')
# @click.option('--min-sub', default=0, show_default=True, type=int,
#               help='Minimal submissions for quest')
# @click.option('--max-sub', default=0, show_default=True, type=int,
#               help='Max submissions for quest')
def crawl_questn(refresh, file, start_idx):
    db = SocialUsersDB()
    crawler = QuestNUserCrawler(quests_file=file)

    if refresh:
        crawler.get_quests(quest_batch_size=100)
    crawler.get_users(start_idx=start_idx, exporter=db)
