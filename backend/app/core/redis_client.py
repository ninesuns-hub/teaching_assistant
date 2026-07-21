import redis
from agent_core.config.settings import settings

class RedisClient:
    def __init__(self):
        self.client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )

    def set_code(self, email: str, code: str, expire: int = 300):
        """设置验证码，默认5分钟过期"""
        self.client.setex(f"verify_code:{email}", expire, code)

    def get_code(self, email: str) -> str:
        return self.client.get(f"verify_code:{email}")

    def delete_code(self, email: str):
        self.client.delete(f"verify_code:{email}")

    def can_send_code(self, email: str, cooldown: int = 60) -> bool:
        return not self.client.exists(f"verify_cooldown:{email}")

    def mark_code_sent(self, email: str, cooldown: int = 60):
        self.client.setex(f"verify_cooldown:{email}", cooldown, "1")

redis_client = RedisClient()
