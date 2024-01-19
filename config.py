import os

from dotenv import load_dotenv

load_dotenv()


class SocialUsersDBConfig:
    CONNECTION_URL = os.getenv("SOCIAL_USERS_CONNECTION_URL")
    DATABASE = os.getenv("SOCIAL_USERS_DATABASE")
