import json
import os
from typing import Optional, Type, TypeVar
from models.order import Order
from models.trade import Trade

T = TypeVar("T")


class DataManager:
    _DATA_DIR = os.path.dirname(os.path.abspath(__file__))
    _MODEL_FILES = {
        Order: os.path.join(_DATA_DIR, "orders.json"),
        Trade: os.path.join(_DATA_DIR, "trades.json"),
    }

    @staticmethod
    def get_all(model_class: Type[T]) -> list[T]:
        filepath = DataManager._MODEL_FILES[model_class]
        data = DataManager._load_json(filepath)
        return [model_class.from_dict(d) for d in data]

    @staticmethod
    def get_by_id(model_class: Type[T], item_id: str) -> Optional[T]:
        for item in DataManager.get_all(model_class):
            if item.id == item_id:
                return item
        return None

    @staticmethod
    def save(item: T) -> None:
        model_class = type(item)
        filepath = DataManager._MODEL_FILES[model_class]
        items = DataManager.get_all(model_class)
        items.append(item)
        DataManager._save_json(filepath, [i.to_dict() for i in items])

    @staticmethod
    def delete_by_id(model_class: Type[T], item_id: str) -> bool:
        filepath = DataManager._MODEL_FILES[model_class]
        items = DataManager.get_all(model_class)
        filtered = [i for i in items if i.id != item_id]
        if len(filtered) < len(items):
            DataManager._save_json(filepath, [i.to_dict() for i in filtered])
            return True
        return False

    @staticmethod
    def update(item: T) -> bool:
        model_class = type(item)
        filepath = DataManager._MODEL_FILES[model_class]
        items = DataManager.get_all(model_class)
        for i, existing in enumerate(items):
            if existing.id == item.id:
                items[i] = item
                DataManager._save_json(filepath, [x.to_dict() for x in items])
                return True
        return False

    @staticmethod
    def _load_json(filepath: str) -> list:
        if not os.path.exists(filepath):
            return []
        with open(filepath, "r") as f:
            return json.load(f)

    @staticmethod
    def _save_json(filepath: str, data: list) -> None:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
