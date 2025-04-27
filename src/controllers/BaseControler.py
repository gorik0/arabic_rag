from os import path
import random
import string
from helpers.config import get_settings


class BaseController():
    def __init__(self):
        self.app_settings = get_settings()
        self.base_dir = path.dirname(path.dirname(__file__))
        self.files_dir = path.join(self.base_dir, 'assets/files') 
    def generate_random_string (self, len : int ):
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=len))