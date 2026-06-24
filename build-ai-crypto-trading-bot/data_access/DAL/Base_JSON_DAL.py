import json
import os
from typing import Callable


class Base_JSON_DAL:
    @staticmethod
    def read_data(file_path: str):
        if not os.path.exists(file_path):
            return []
        with open(file_path, "r") as f:
            data = f.read().strip()
            if not data:
                return []
            return json.loads(data)

    @staticmethod
    def write_data(file_path: str, items):
        with open(file_path, "w") as f:
            f.write(json.dumps(items, default=str))

    @staticmethod
    def insert(file_path: str, item):
        items = Base_JSON_DAL.read_data(file_path)
        items.append(item)
        Base_JSON_DAL.write_data(file_path, items)

    @staticmethod
    def get_all(file_path: str):
        return Base_JSON_DAL.read_data(file_path)

    @staticmethod
    def delete(file_path: str, match_fn: Callable):
        items = Base_JSON_DAL.read_data(file_path)
        items = [item for item in items if not match_fn(item)]
        Base_JSON_DAL.write_data(file_path, items)
