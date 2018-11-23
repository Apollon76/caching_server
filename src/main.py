from bottle import run, route
from redis import Redis

from src.page_loader import PageLoader
from src.server import App


@route('/hello')
def hello():
    return 'asdf'


def main():
    client = Redis(host='localhost', port=6379, db=0)
    loader = PageLoader(
        database=client,
        storage_path='/home/apollon/PycharmProjects/caching_server/data'
    )

    app = App(loader, '/home/apollon/PycharmProjects/caching_server/data')
    app.run(host='localhost', port=8080, debug=True)


if __name__ == '__main__':
    main()
