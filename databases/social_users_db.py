from pymongo import MongoClient, UpdateOne
from config import SocialUsersDBConfig


class SocialUsersDB:
    def __init__(self, connection_url=None, database=None,
                 collection=None):
        if not connection_url:
            connection_url = SocialUsersDBConfig.CONNECTION_URL
        if not database:
            database = SocialUsersDBConfig.DATABASE
        # self.connection_url = connection_url.split('@')[-1]
        self.connection = MongoClient(connection_url)

        self.mongo_db = self.connection[database]

        if not collection:
            self.users_collection = self.mongo_db[SocialUsersDBConfig.COLLECTION]
        else:
            self.users_collection = self.mongo_db[collection]

    def update_users(self, data: list[dict]):
        updates = []
        # for _id, user in data.items():
        #     user['_id'] = _id
        for user in data:
            number_of_quests = user.pop('numberOfQuests', 1)
            updates.append(UpdateOne({'_id': user['_id']},
                                     {'$set': user, '$inc': {'numberOfQuests': number_of_quests}},
                                     upsert=True))
        self.users_collection.bulk_write(updates)
