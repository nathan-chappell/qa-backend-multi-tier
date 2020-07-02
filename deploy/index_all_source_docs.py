# index_all_source_docs.py

from pathlib import Path
import asyncio

from aiohttp import ClientSession

async def index_all(directory, index_name):
    dir_path = Path(directory)
    if not dir_path.exists():
        raise RuntimeError(f'{path} does not exist')
    async with ClientSession() as session:
        for path in dir_path.glob('*.txt'):
            if not path.name.endswith('.txt'):
                continue
            with open(path) as file:
                text = file.read()
            body = {'operation': 'create', 'docId': path.name, 'text': text}
            async with session.post('http://0.0.0.0:8080/index',json=body) as response:
                print(f'{path.name} - {response.status}')

if __name__ == '__main__':
    coro = index_all('data/source_docs','deployment-index')
    asyncio.get_event_loop().run_until_complete(coro)
