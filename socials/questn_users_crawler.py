import json
import time

import requests
from urllib.parse import urlencode

from databases.social_users_db import SocialUsersDB
from utils.logger_utils import get_logger

logger = get_logger('QuestN User Crawler')

BASE_URL = 'https://api.questn.com/consumer/quest'


class QuestNUserCrawler:
    @staticmethod
    def _get_quests(page=1, count=100):
        query = {
            'count': count,
            'page': page,
            'search': '',
            'category': 100,
            'status_filter': 0,
            'rewards_filter': 0,
            'tag_filter': 0,
            'user_id': 0
        }
        url = f'{BASE_URL}/discover_list/?{urlencode(query)}'
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        return response

    @staticmethod
    def _get_questers(quest_id, page=1, count=1000):
        query = {
            'quest_id': quest_id,
            'page': page,
            'count': count
        }
        url = f'{BASE_URL}/user_participants/?{urlencode(query)}'
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        return response

    def get_quests(self, quest_batch_size=100):
        number_of_pages = 1
        page = 0
        data = []
        while page < number_of_pages:
            page += 1
            try:
                quests_resp = self._get_quests(page=page, count=quest_batch_size)
                if 200 <= quests_resp.status_code < 300:
                    quests_response = quests_resp.json()
                    result = quests_response['result']

                    number_of_pages = result['num_pages']

                    quests = result['data']
                    data.extend([{'id': q['id'], 'title': q['title'], 'submissions': q.get('submissions') or 0} for q in quests])
                    logger.info(f'Loaded {len(data)} quests after page [{page}]')
                else:
                    raise requests.exceptions.RequestException(f'Fail ({quests_resp.status_code}) to load quests of page [{page}]')
            except Exception as ex:
                logger.exception(ex)
            finally:
                time.sleep(1)
                
        data = sorted(data, key=lambda x: x['submissions'], reverse=True)

        with open('test/QuestN/quests.json', 'w') as f:
            json.dump(data, f)
        logger.info(f'Saved {len(data)} quests')

    def get_users(self, user_batch_size=1000, min_submissions=0, max_submissions=None, exporter: SocialUsersDB = None):
        with open('test/QuestN/quests.json') as f:
            data = json.load(f)
            data = [q for q in data if self.check_submission(q['submissions'], min_submissions, max_submissions)]

        logger.info("###############################")
        logger.info(f'There are {len(data)} quests')
        logger.info("###############################\n")

        for idx, quest in enumerate(data):
            logger.info(f'[{idx + 1}] Get questers of {quest["title"]} ({quest["submissions"]} submissions)...')
            quest_id = quest['id']

            number_of_pages = 1
            page = 0
            data = []
            while page < number_of_pages:
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
                                data.append(q_)
                        logger.info(f'Loaded {len(data)} questers after page [{page}]')
                    else:
                        raise requests.exceptions.RequestException(
                            f'Fail ({questers_resp.status_code}) to load questers of page [{page}]')
                except Exception as ex:
                    logger.exception(ex)
                finally:
                    time.sleep(1)

            if data and (exporter is not None):
                self.export_users(exporter, data)

            logger.info(f'End {quest["title"]} with {len(data)} users \n')

    @staticmethod
    def format_quester(quester):
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

    @staticmethod
    def check_submission(n, min_submissions=0, max_submissions=None):
        if n < min_submissions:
            return False
        if (max_submissions is not None) and (n > max_submissions):
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
    # crawler.get_quests(quest_batch_size=100)
    crawler.get_users(user_batch_size=10000, min_submissions=5000, max_submissions=10000)
