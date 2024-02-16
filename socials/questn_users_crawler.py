import json
import time

import requests
from urllib.parse import urlencode

from databases.social_users_db import SocialUsersDB
from utils.logger_utils import get_logger

logger = get_logger('QuestN User Crawler')

BASE_URL = 'https://api.questn.com/consumer'

LIMIT_NUMBER_OF_PAGES = 100


class QuestNUserCrawler:
    def __init__(self, quests_file: str = 'data/questn_quests.json'):
        self.quest_file = quests_file

        self.current_quest_index = 0
        self.quests: list = []

    @staticmethod
    def _get_quests(page: int=1, count=21):
        """Call API to get all trending quests on QuestN
        """
        query = {
            'count': count,
            'page': page,
            'search': '',
            'category': 100,
            'status_filter': 100,
            'community_filter': 0,
            'rewards_filter': 0,
            'chain_filter': 0,
            'user_id': 0
        }
        url = f'{BASE_URL}/explore/list/?{urlencode(query)}'
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        return response

    @staticmethod
    def _get_questers(quest_id, page=1, count=1000):
        """Call API to get list of questers of a quest on QuestN (pagination)
        """
        query = {
            'quest_id': quest_id,
            'page': page,
            'count': count
        }
        url = f'{BASE_URL}/quest/user_participants/?{urlencode(query)}'
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        return response

    def get_quests(self, quest_batch_size=100):
        try:
            with open(self.quest_file, 'r') as f:
                self.quests = json.load(f)
        except FileNotFoundError:
            number_of_pages = 1
            page = 0
            while page < number_of_pages:
                page += 1
                try:
                    quests_resp = self._get_quests(page=page, count=quest_batch_size)
                    if 200 <= quests_resp.status_code < 300:
                        quests_response = quests_resp.json()
                        result = quests_response['result']

                        number_of_pages = result['num_pages']

                        _page_quests = result['data']
                        self.quests.extend([{'id': q['id'], 'title': q['title'], 'submissions': q.get('submissions', 0)}
                                            for q in _page_quests])
                        logger.info(f'Loaded {len(self.quests)} quests after page [{page}] / {number_of_pages}')
                    else:
                        raise requests.exceptions.RequestException(f'Fail ({quests_resp.status_code}) to load quests of page [{page}]')
                except Exception as ex:
                    logger.exception(ex)
                finally:
                    time.sleep(0.1)

            self.quests = sorted(self.quests, key=lambda x: x['submissions'], reverse=True)
            with open(self.quest_file, 'w') as f:
                json.dump(self.quests, f, indent=2)

        n_users = sum([q['submissions'] for q in self.quests])
        logger.info(f'Get {len(self.quests)} quests, {n_users} users')

    def get_users(self,
                  start_idx=None,
                  user_batch_size=1000,
                  min_submissions=10,
                  max_submissions=None,
                  exporter: SocialUsersDB = None):
        self.get_quests()
        self.filter_quests(min_submissions=min_submissions, max_submissions=max_submissions)

        logger.info("###############################")
        logger.info(f'There are {len(self.quests)} quests')
        logger.info("###############################\n")

        if start_idx is None:
            start_idx = self.current_quest_index

        for idx, quest in enumerate(self.quests[start_idx:]):
            logger.info(f'Get questers of quest {idx + start_idx} / {len(self.quests)}: '
                        f'{quest["title"]}: ({quest["submissions"]} submissions)...')
            quest_id = quest['id']

            number_of_pages = 1
            page = 0
            page_questers = []
            while page < number_of_pages and page <= LIMIT_NUMBER_OF_PAGES:
                page += 1
                try:
                    questers_resp = self._get_questers(quest_id=quest_id, page=page, count=user_batch_size)
                    if 200 <= questers_resp.status_code < 300:
                        questers_response = questers_resp.json()
                        result = questers_response['result']

                        number_of_pages = result['num_pages']

                        questers = result['data']
                        for q in questers:
                            q_ = self.format_quester(q)
                            if q_:
                                page_questers.append(q_)
                        logger.info(f'Loaded {len(page_questers)} questers after page {page} / {number_of_pages}')
                    else:
                        raise requests.exceptions.RequestException(
                            f'Fail ({questers_resp.status_code}) to load questers of page {page}')
                except Exception as ex:
                    logger.exception(ex)
                finally:
                    time.sleep(1)

            if page_questers and (exporter is not None):
                self.export_users(exporter, page_questers)

            self.current_quest_index = idx + start_idx

    @staticmethod
    def format_quester(quester: dict):
        """Get info about a quester, filter out questers without crypto wallets
        """
        address = quester.get('user_address')
        if not address:
            return None

        address = address.lower()

        discord_username = quester.get('discord_username')
        twitter_username = quester.get('twitter_username')
        if (not discord_username) and (not twitter_username):
            return None

        return {
            'id': quester['user_id'],
            'address': address,
            'discord': discord_username,
            'twitter': twitter_username
        }

    def filter_quests(self, min_submissions, max_submissions):
        """Filter out quests with too few submissions (or users)"""
        self.quests = [q for q in self.quests
                       if self._check_submission(q['submissions'], min_submissions, max_submissions)]

    @staticmethod
    def _check_submission(submissions, min_submissions=0, max_submissions=None):
        if submissions < min_submissions:
            return False
        if (max_submissions is not None) and (submissions > max_submissions):
            return False
        return True

    @staticmethod
    def export_users(exporter, users):
        data = []
        for user in users:
            user_id = user.pop('id')
            data.append({
                '_id': user['address'],
                'idQuestN': user_id,
                'numberOfQuests': 1,
                **user
            })
        exporter.update_users(data)
        logger.info(f'Exported {len(data)} users')


if __name__ == '__main__':
    crawler = QuestNUserCrawler()
    crawler.get_quests(quest_batch_size=100)
    # crawler.get_users(user_batch_size=10000, min_submissions=5000, max_submissions=10000,
    #                   exporter=SocialUsersDB())
