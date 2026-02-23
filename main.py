import asyncio

from fastapi import Depends
from depends import inject


async def get_db():
    return "db"


async def return_async_handler(db=Depends(get_db)):
    return f"using async {db}"


def sync_get_db():
    return "db"


def return_sync_handler(db=Depends(sync_get_db)):
    return f"using sync {db}"


async def main():
    x = await inject(return_sync_handler)()
    print(x)

    y = await inject(return_async_handler)()
    print(y)

if __name__ == '__main__':
    asyncio.run(main())

