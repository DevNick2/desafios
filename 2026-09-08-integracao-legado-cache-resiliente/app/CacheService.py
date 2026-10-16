import redis

from typing import Callable, TypeVar

T = TypeVar("T")


class CacheService:
    instance: redis.Redis

    def __init__(self, deserialize=None):
        self.instance = redis.Redis(
            host="localhost",
            port="6379",
            decode_responses=True
        )

    def set_key(self, key, value) -> None:
        if type(value) is dict:
            self.instance.hset(key, mapping=value)
        else:
            self.instance.set(key, value)

    def get_key(
        self,
        key,
        value_type=None,
        deserialize: Callable[[dict], T] = None
    ):
        if value_type == "dict":
            item = self.instance.hgetall(key)

            if deserialize is not None and item:
                return deserialize(item)
            elif item:
                return item

        return self.instance.get(key)
