import sys
import os
sys.path.append(os.path.dirname(sys.path[0]))

import json
import time
import requests
from urllib.parse import urlencode

from utils.logger_utils import get_logger, get_file_handler
from databases.social_users_db import SocialUsersDB
from utils.retry_handler import retry_handler

logger = get_logger('Zealy User Crawler')
logger.addHandler(get_file_handler())

BASE_URL = 'https://api.zealy.io/communities'
BASE_URL_2 = 'https://backend.zealy.io/api/communities'

COMMUNITY_THRESHOLD = 100  # only get communities with over 100 users
USER_THRESHOLD = 5e-2  # only get top 5% percent users of each community
USER_LIMIT = 1000  # only get maximum 5k users from each community

headers = {
    'Origin': 'https://zealy.io',
    'Referer': 'https://zealy.io/',
    # 'Cookie': '__cf_bm=kuPMYVZ1JfDYoNfHK_k6yG1soOEl1IJLxqmZIWgpoyU-1679891327-0-ASNiS3KCWlMLz0f/PKxsa1npngRv+bpQLOTZ48FlTRitJk/caJbB8S9Y4SIMNLtya8/eRYePbn+MP1BF5H/G2vQ=; connect.sid=s%3AH3B0BE8nL_bU-HVpPomw9xRN6iHhPK8E.FvXqX3oPd2GoJ%2FJ5lQQ%2FdoCX7BlETQ%2BZUSo3Ux0c0e4',
}


class ZealyUserCrawler:
    def __init__(self, batch_size: int = 100,
                 communities_file: str = 'data/zealy_communities.json',
                 database: SocialUsersDB = None):
        self.batch_size = batch_size
        self.communities_file = communities_file
        self.database = database

        self._total_users: int = 0
        self._progress_users: int = 0

    @staticmethod
    def _get_communities(page=1, count=30) -> requests.api.request:
        query = {
            'limit': count,
            'page': page,
            'category': 'popular'
        }
        url = f'{BASE_URL}?{urlencode(query)}'
        response = requests.get(url, headers=headers)
        return response

    @staticmethod
    def _get_leaderboard(subdomain, page) -> requests.api.request:
        query = {
            'page': page
            # 'limit': count
        }
        url = f'{BASE_URL_2}/{subdomain}/leaderboard?{urlencode(query)}'
        response = requests.get(url, headers=headers)
        return response

    @staticmethod
    def _get_user(subdomain, user_id) -> requests.api.request:
        url = f'{BASE_URL}/{subdomain}/users/{user_id}'
        response = requests.get(url, headers=headers)
        return response

    def get_top_communities(self, batch_size=None, communities_file=None):
        number_of_pages = 1
        page = 0
        data = []
        if not batch_size:
            batch_size = self.batch_size
        if not communities_file:
            communities_file = self.communities_file

        while page < number_of_pages:
            try:
                quests_resp = self._get_communities(page=page, count=batch_size)
                if 200 <= quests_resp.status_code < 300:
                    quests_response = quests_resp.json()

                    number_of_pages = quests_response['totalPages']

                    quests = quests_response['communities']
                    data.extend([{'id': q['id'], 'name': q['name'], 'subdomain': q['subdomain'], 'totalMembers': int(q.get('totalMembers', 0))}
                                 for q in quests])
                    logger.info(f'Loaded {len(data)} communities after page [{page + 1}] / {number_of_pages}')
                else:
                    raise requests.exceptions.RequestException(f'Fail ({quests_resp.status_code}) to load communities of page [{page}]')
            except Exception as ex:
                logger.exception(ex)
            finally:
                page += 1
                time.sleep(1)

        data = sorted(data, key=lambda x: x['totalMembers'], reverse=True)

        with open(communities_file, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f'Saved {len(data)} communities')

    def get_users(self, start_community_idx: int = 0):
        """Get users from a community file
        Params:
            start_community_idx: only start from community at this idx from the communities json file
        """
        with open(self.communities_file) as f:
            communities = json.load(f)
            communities = [q for q in communities if q['totalMembers'] >= COMMUNITY_THRESHOLD]

        n_communities = len(communities)
        self._total_users = sum([c['totalMembers'] for c in communities])

        logger.info("###############################")
        logger.info(f'There are {n_communities} communities')
        logger.info("###############################\n")

        for _i, community in enumerate(communities[start_community_idx:]):
            logger.info(f'Get users of community {_i + start_community_idx} / {n_communities}: '
                        f'{community["name"]} ({community["totalMembers"]} members)')
            try:
                self._get_community_users(community_info=community)
                self._progress_users = sum([c['totalMembers'] for c in communities[:_i]])
                logger.info(f'Successfully get users of community {community["name"]}. '
                            f'Progress: {(self._progress_users / self._total_users * 100):.2f}%')
            except Exception as ex:
                logger.exception(f"Can't get users of community {community['name']}: {ex}")

    @retry_handler(retries_number=3)
    def _get_community_users(self, community_info: dict):
        page_number = 1
        total_n_users = 0
        while True:
            page_users: dict[str, dict] = dict()  # {user_id: user_info}

            leaderboard_resp = self._get_leaderboard(subdomain=community_info['subdomain'],
                                                     page=page_number)
            n_pages = leaderboard_resp.json()['totalPages']
            n_users = leaderboard_resp.json()['totalRecords']
            list_users = leaderboard_resp.json()['data']
            for user in list_users:
                user_id = user['userId']
                user_info = self._get_user_info(community_subdomain=community_info['subdomain'],
                                                user_id=user_id)
                if user_info:
                    page_users[user_id] = user_info
                    page_users[user_id]['idZealy'] = page_users[user_id].pop('id')

            logger.info(f'Community {community_info["name"]}: '
                        f'scraped to page {page_number} / {n_pages} pages. '
                        f'total {total_n_users} users')

            total_n_users += len(page_users)
            # if community has no users with blockchain address, move on to next community
            if (page_number > n_pages
                    or len(page_users) == 0
                    or len(page_users) > (n_users * USER_THRESHOLD)
                    or total_n_users > USER_LIMIT):
                break

            # update to database
            _mongo_dicts = [{
                '_id': k,
                **v
            } for k, v in page_users.items()]
            self.database.update_users(data=_mongo_dicts)
            page_number += 1

    def _get_user_info(self, community_subdomain: str, user_id: str,
                       sleep_time: float = 1e-4) -> dict:
        user_info = dict()

        try:
            user_resp = self._get_user(subdomain=community_subdomain,
                                       user_id=user_id)
            assert 200 <= user_resp.status_code < 300
            user_info = self._format_quester(user_resp.json())
        except AssertionError as a:
            logger.exception(f'Failed to load user id {user_id}: {a}')
        except KeyError as k:
            logger.exception(f'Failed to get info of user id {user_id}: {k}')
        except Exception as ex:
            logger.exception(ex)
        finally:
            time.sleep(sleep_time)

        return user_info

    @staticmethod
    def _format_quester(quester):
        """Remove users without blockchain addresses"""
        displayed_information = quester.get('displayedInformation') or []
        if 'wallet' not in displayed_information or len(displayed_information) <= 1:
            return None

        user = {'id': quester['id'], 'addresses': {}}
        for chain, address in quester.get('addresses').items():
            user['addresses'][chain] = address.lower()

        discord_username = quester.get('discordHandle')
        if discord_username:
            user['discord'] = discord_username

        twitter_username = quester.get('twitterUsername')
        if twitter_username:
            user['twitter'] = twitter_username

        return user


if __name__ == '__main__':
    db = SocialUsersDB()
    crawler = ZealyUserCrawler(batch_size=100,
                               communities_file='../data/Crew3/communities.json',
                               database=db)
    crawler.get_top_communities()
    crawler.get_users()
