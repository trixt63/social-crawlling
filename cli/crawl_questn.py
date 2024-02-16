import os
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
@click.option('--min-sub', default=10, show_default=True, type=int,
              help='Minimal submissions for quest')
@click.option('--max-sub', default=None, show_default=True, type=int,
              help='Max submissions for quest')
def crawl_questn(refresh, file, start_idx, min_sub, max_sub):
    db = SocialUsersDB()
    crawler = QuestNUserCrawler(quests_file=file)

    if refresh:
        if os.path.isfile(file):
            os.remove(file)
        else:
            raise FileNotFoundError(f"Not found QuestN quests file at {file}")

    crawler.get_users(start_idx=start_idx, exporter=db, min_submissions=min_sub, max_submissions=max_sub)
