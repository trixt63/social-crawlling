from pymongo import MongoClient, UpdateOne


class SocialUsersDB:
    def __init__(self, connection_url, database='TokenDatabase'):
        self.connection_url = connection_url.split('@')[-1]
        self.connection = MongoClient(connection_url)

        self.mongo_db = self.connection[database]

        self.users_collection = self.mongo_db['users']

    def update_users(self, users):
        data = []
        for user in users:
            number_of_quests = user.pop('numberOfQuests', 1)
            data.append(UpdateOne({'_id': user['_id']}, {'$set': user, '$inc': {'numberOfQuests': number_of_quests}}, upsert=True))
        self.users_collection.bulk_write(data)
