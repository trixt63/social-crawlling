import sys
import os
sys.path.append(os.path.dirname(sys.path[0]))

import json
import time

import requests
from urllib.parse import urlencode

from utils.logger_utils import get_logger
from databases.social_users_db import SocialUsersDB

logger = get_logger('Zealy User Crawler')

BASE_URL = 'https://api.zealy.io/communities'
BASE_URL_2 = 'https://backend.zealy.io/api/communities'

headers = {
    'Origin': 'https://zealy.io',
    'Referer': 'https://zealy.io/',
    # 'Cookie': '__cf_bm=kuPMYVZ1JfDYoNfHK_k6yG1soOEl1IJLxqmZIWgpoyU-1679891327-0-ASNiS3KCWlMLz0f/PKxsa1npngRv+bpQLOTZ48FlTRitJk/caJbB8S9Y4SIMNLtya8/eRYePbn+MP1BF5H/G2vQ=; connect.sid=s%3AH3B0BE8nL_bU-HVpPomw9xRN6iHhPK8E.FvXqX3oPd2GoJ%2FJ5lQQ%2FdoCX7BlETQ%2BZUSo3Ux0c0e4',
    
}


class ZealyUserCrawler:
    def __init__(self, batch_size, communities_file, database: SocialUsersDB):
        self.batch_size = batch_size
        self.communities_file = communities_file
        self.database = database

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
                    # number_of_pages = 10  # test

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

    def get_users(self):
        with open(self.communities_file) as f:
            communities = json.load(f)
            communities = [q for q in communities if q['totalMembers']]
        n_communities = len(communities)

        logger.info("###############################")
        logger.info(f'There are {n_communities} communities')
        logger.info("###############################\n")

        for _i, community in enumerate(communities):
            logger.info(f'Get users of community {_i} / {n_communities}: {community["name"]}')

            _n_pages = 1
            _page = 1
            _data = []
            while _page <= _n_pages:
                # _all_users_ids: set[str] = set()
                subdomain = community['subdomain']
                try:
                    leaderboard_resp = self._get_leaderboard(subdomain=subdomain, page=_page)
                    _n_pages = leaderboard_resp.json()['totalPages']
                    _n_users = leaderboard_resp.json()['totalRecords']

                    list_users = leaderboard_resp.json()['data']
                    _page_users: dict[str, dict] = dict()  # {user_id: user_info}
                    for user in list_users:
                        user_id = user['userId']
                        # if user_id in _all_users_ids:
                        #     continue
                        # else:
                        try:
                            user_resp = self._get_user(subdomain=subdomain, user_id=user['userId'])
                            if 200 <= user_resp.status_code < 300:
                                user_info = self.format_quester(user_resp.json())
                                if user_info:
                                    _page_users[user_id] = user_info
                                    _page_users[user_id]['idZealy'] = user_info.pop('id')
                                    # _page_users[user_id].update({k: user[k] for k in ['xp', 'name', 'numberOfQuests']})
                            else:
                                raise requests.exceptions.RequestException(
                                    f'Fail ({user_resp.status_code}) to load user {user_id}')
                        except Exception as ex:
                            logger.exception(ex)
                        finally:
                            # _all_users_ids.add(user_id)
                            time.sleep(0.001)
                    logger.info(f'Community {_i}/{n_communities} {community["name"]}: '
                                f'scraped to page {_page} / {_n_pages} pages, '
                                f'total {_n_users} users')
                    # update to database
                    self.database.update_users(_page_users)
                    _page_users.clear()
                    _page += 1
                except Exception as e:
                    logger.exception(f"Error at {_i}: {e}")

    @staticmethod
    def format_quester(quester):
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
