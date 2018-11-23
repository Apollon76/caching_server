import configparser
from typing import Dict, Any
from urllib.parse import urljoin

from redis import Redis

from src.page_loader import PageLoader
from src.server import App


def make_client(config: Dict[str, Any]) -> Redis:
    return Redis(host=config['host'], port=config['port'], db=config['db'])


def main():
    config = configparser.ConfigParser()
    config.read('../config.ini')

    storage_path = config[config.default_section]['storage_path']

    client = make_client(config['REDIS'])
    client.flushall()

    host = config[config.default_section]['host']
    port = config[config.default_section]['port']

    loader = PageLoader(
        database=client,
        storage_path=storage_path,
        url_prefix=urljoin(f'http://{host}:{port}', '/?url=')
    )

    app = App(loader, storage_path)
    app.run(host=host, port=port, debug=True)


if __name__ == '__main__':
    main()
