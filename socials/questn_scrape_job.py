from cli_scheduler.scheduler_job import SchedulerJob

from questn_users_crawler import QuestNUserCrawler
from constants.time_constants import TimeConstants


class CrawlQuestNJob(SchedulerJob):
    def __init__(self,
                 quests_file: str,
                 interval: int = TimeConstants.DAYS_7,
                 retry: bool = True):
        super().__init__(scheduler=f'^true@{interval}#{retry}')
        self._scraper = QuestNUserCrawler(quests_file=quests_file)

    def _execute(self):
        self._scraper.get_quests()

