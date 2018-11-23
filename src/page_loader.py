import asyncio
import os
from urllib.parse import urlparse, ParseResult, urljoin

import aiohttp as aiohttp
import requests
from bs4 import BeautifulSoup
from redis import Redis

from src import utils


class LoadingError(Exception):
    pass


class PageLoader:
    REPLACING_TAGS = [
        ('img', 'src'),
        ('script', 'src'),
        ('link', 'href'),
    ]

    def __init__(self,
                 database: Redis,
                 storage_path: str,
                 url_prefix: str,
                 url_file_prefix: str):
        self.__database = database
        self.__storage_path = storage_path
        self.__url_prefix = url_prefix
        self.__url_file_prefix = url_file_prefix

    def load(self, url: str) -> str:
        result = self.__database.get(url)
        if result:
            return result.decode()

        base = urlparse(url)
        content = self.__get_content(url)
        page = BeautifulSoup(content, 'html.parser')

        self.__replace_links(page, base)

        for tag, attr in self.REPLACING_TAGS:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.__replace_files(loop, page, base, tag, attr))

        self.__database.set(url, page.prettify())

        return page.prettify()

    async def load_file(self, session: aiohttp.ClientSession, url: str) -> str:
        filename = self.__database.get(url)
        if filename is not None:
            return urljoin(self.__url_file_prefix, filename.decode())

        _, extension = os.path.splitext(url)
        filename = utils.gen_filename() + extension
        path = os.path.join(self.__storage_path, filename)

        async with session.get(url) as response:
            with open(path, 'wb') as f_handle:
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    f_handle.write(chunk)

        self.__database.set(url, filename)

        return urljoin(self.__url_file_prefix, filename)

    def __get_content(self, url: str) -> bytes:
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.content

    async def __replace_files(self,
                              loop,
                              page: BeautifulSoup,
                              base: ParseResult,
                              tag_type: str,
                              attr: str):
        urls = []
        for tag in page.find_all(tag_type):
            url = tag.get(attr)
            if not url:
                continue
            url = utils.normalize_link(url, base)
            urls.append(url)

        async with aiohttp.ClientSession(loop=loop) as session:
            tasks = [self.load_file(session, url) for url in urls]
            paths = await asyncio.gather(*tasks)

        pointer = 0
        for tag in page.find_all(tag_type):
            url = tag.get(attr)
            if not url:
                continue

            path = paths[pointer]
            pointer += 1

            tag[attr] = path

    def __replace_links(self, page: BeautifulSoup, base: ParseResult):
        for link in page.find_all('a'):
            url = link.get('href')
            if not url:
                continue
            url = utils.normalize_link(url, base)
            link['href'] = self.__url_prefix + url
