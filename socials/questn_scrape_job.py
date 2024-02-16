import os
from cli_scheduler.scheduler_job import SchedulerJob

from socials.questn_users_crawler import QuestNUserCrawler
from databases.social_users_db import SocialUsersDB
from constants.time_constants import TimeConstants
from utils.file_utils import delete_file
from utils.logger_utils import get_logger

logger = get_logger('QuestN Scrape Job')


class CrawlQuestNJob(SchedulerJob):
    def __init__(self,
                 quests_file: str,
                 db: SocialUsersDB,
                 interval: int = TimeConstants.DAYS_7,
                 retry: bool = True):
        super().__init__(scheduler=f'^true@{interval}#{retry}')
        self.file = quests_file
        self._scraper = QuestNUserCrawler(quests_file=self.file)
        self.db = db

    def _execute(self):
        if os.path.isfile(self.file):
            delete_file(self.file)
        self._scraper.get_users(exporter=self.db)
