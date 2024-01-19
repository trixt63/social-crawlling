import sys
import os
sys.path.append(os.path.dirname(sys.path[0]))

import json
import time

import requests
from urllib.parse import urlencode

from utils.logger_utils import get_logger
from databases.social_users_db import SocialUsersDB

logger = get_logger('Crew3 User Crawler')

BASE_URL = 'https://api.zealy.io/communities'

headers = {
    'Origin': 'https://zealy.io',
    'Referer': 'https://zealy.io/',
    # 'Cookie': '__cf_bm=kuPMYVZ1JfDYoNfHK_k6yG1soOEl1IJLxqmZIWgpoyU-1679891327-0-ASNiS3KCWlMLz0f/PKxsa1npngRv+bpQLOTZ48FlTRitJk/caJbB8S9Y4SIMNLtya8/eRYePbn+MP1BF5H/G2vQ=; connect.sid=s%3AH3B0BE8nL_bU-HVpPomw9xRN6iHhPK8E.FvXqX3oPd2GoJ%2FJ5lQQ%2FdoCX7BlETQ%2BZUSo3Ux0c0e4',
    
}


class Crew3UserCrawler:
    def __init__(self, batch_size, communities_file, database: SocialUsersDB):
        self.batch_size = batch_size
        self.communities_file = communities_file
        self.database = database

    @staticmethod
    def _get_communities(page=1, count=30):
        query = {
            'limit': count,
            'page': page,
            'category': 'popular'
        }
        url = f'{BASE_URL}?{urlencode(query)}'
        response = requests.get(url, headers=headers)
        return response

    @staticmethod
    def _get_leaderboard(subdomain, page=1, count=1000):
        # For pagination
        # query = {
        #     'page': page,
        #     'limit': count
        # }
        # url = f'{BASE_URL}/{subdomain}/leaderboard?{urlencode(query)}'
        url = f'{BASE_URL}/{subdomain}/leaderboard'
        response = requests.get(url, headers=headers)
        return response

    @staticmethod
    def _get_user(subdomain, user_id):
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
                    number_of_pages = 10

                    quests = quests_response['communities']
                    data.extend([{'id': q['id'], 'name': q['name'], 'subdomain': q['subdomain'], 'totalMembers': int(q.get('totalMembers', 0))} for q in quests])
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

    def get_users(self, communities_file=None, exporter: SocialUsersDB = None):
        if not communities_file:
            communities_file = self.communities_file
        if not exporter:
            exporter = self.database

        with open(communities_file) as f:
            data = json.load(f)
            data = [q for q in data if q['totalMembers']]
        n_communities = len(data)

        logger.info("###############################")
        logger.info(f'There are {n_communities} communities')
        logger.info("###############################\n")

        # users = {}
        # t = int(file[5:10])
        for idx, quest in enumerate(data):
            try:
                logger.info(f'[{idx}] / {n_communities} Get users of {quest["name"]}...')
                subdomain = quest['subdomain']

                leaderboard_resp = self._get_leaderboard(subdomain)
                list_users = leaderboard_resp.json()['leaderboard']
                n_users = len(list_users)
                logger.info(f'There are {n_users} users to get info')

                data = {}
                
                # i = 0
                users = {}

                _batch_users = {}
                for i, user in enumerate(list_users):

                    user_id = user['userId']
                    if user_id in users:
                        continue
                    else:
                        try:
                            questers_resp = self._get_user(subdomain=subdomain, user_id=user['userId'])
                            if 200 <= questers_resp.status_code < 300:
                                questers_response = questers_resp.json()
                                q_ = self.format_quester(questers_response)
                                if q_:
                                    # data[user_id] = q_
                                    _batch_users[user_id] = q_
                                    _batch_users[user_id].update({k: user[k] for k in ['xp', 'name', 'numberOfQuests']})
                            else:
                                raise requests.exceptions.RequestException(
                                    f'Fail ({questers_resp.status_code}) to load user {user_id}')
                        except Exception as ex:
                            logger.exception(ex)
                        finally:
                            time.sleep(0.001)
                    if not i % self.batch_size:
                        users.update(_batch_users)
                        exporter.update_users(_batch_users)
                        _batch_users = {}
                        logger.info(f"To {i} / {n_users} users")
                    # i+=1
                users.update(data)
                # with open('user_'+f'{t}'+'.json', 'w') as f:
                #     json.dump(users, f)
                # logger.info(f'Saved {len(data)} users in {quest["name"]}')
                # logger.info(f'End {quest["name"]} with {len(data)} [{len(users)}] users \n')
                # t+=1
            except Exception as e:
                # logger.info(f"err {e} as index: {t}")
                logger.exception(f"Error at {idx}: {e}")

    @staticmethod
    def format_quester(quester):
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
    crawler = Crew3UserCrawler(batch_size=100,
                               communities_file='../data/Crew3/communities.json',
                               database=db)
    crawler.get_top_communities()
    crawler.get_users()
