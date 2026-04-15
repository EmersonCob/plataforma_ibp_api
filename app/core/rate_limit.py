import time
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request
from redis.asyncio import Redis

from app.core.config import settings
from app.services.redis import get_redis


def parse_rate_limit(limit: str) -> tuple[int, int]:
    amount, period = limit.split("/")
    windows = {"second": 1, "minute": 60, "hour": 3600}
    return int(amount), windows.get(period, 60)


def rate_limiter(limit: str) -> Callable:
    amount, window_seconds = parse_rate_limit(limit)

    async def dependency(request: Request, redis: Redis = Depends(get_redis)) -> None:
        forwarded = request.headers.get("x-forwarded-for", "")
        client_ip = forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")
        bucket = int(time.time() // window_seconds)
        key = f"rate:{request.url.path}:{client_ip}:{bucket}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)
        if count > amount:
            raise HTTPException(status_code=429, detail="Muitas tentativas. Aguarde e tente novamente.")

    return dependency


login_rate_limit = rate_limiter(settings.login_rate_limit)
public_rate_limit = rate_limiter(settings.public_rate_limit)

