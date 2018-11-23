from redis import Redis

from src.page_loader import PageLoader
from src.server import App


def main():
    client = Redis(host='localhost', port=6379, db=0)
    client.flushall()
    storage_path = '/home/apollon/PycharmProjects/caching_server/data'

    loader = PageLoader(
        database=client,
        storage_path=storage_path,
        url_prefix='http://localhost:8080/?url='
    )

    app = App(loader, storage_path)
    app.run(host='localhost', port=8080, debug=True)


if __name__ == '__main__':
    main()
