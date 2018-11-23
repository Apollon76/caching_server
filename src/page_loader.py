import os
import shutil
from urllib.parse import urlparse, ParseResult, urljoin

import requests
from bs4 import BeautifulSoup
from redis import Redis
from requests import HTTPError

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
                 url_prefix: str):
        self.__database = database
        self.__storage_path = storage_path
        self.__url_prefix = url_prefix

    def load(self, url: str) -> str:
        result = self.__database.get(url)
        if result:
            return result.decode()

        base = urlparse(url)
        content = self.__get_content(url)
        page = BeautifulSoup(content, 'html.parser')

        self.__replace_links(page, base)

        for tag, attr in self.REPLACING_TAGS:
            self.__replace_files(page, base, tag, attr)

        self.__database.set(url, page.prettify())

        return page.prettify()

    def load_file(self, url: str) -> str:
        filename = self.__database.get(url)
        if filename is not None:
            return urljoin('http://localhost:8080/static/', filename.decode())

        _, extension = os.path.splitext(url)
        filename = utils.gen_filename() + extension
        path = os.path.join(self.__storage_path, filename)

        resp = requests.get(url, stream=True)
        resp.raise_for_status()

        with open(path, 'wb') as f:
            resp.raw.decode_content = True
            shutil.copyfileobj(resp.raw, f)

        self.__database.set(url, filename)

        return urljoin('http://localhost:8080/static/', filename)

    def __get_content(self, url: str) -> bytes:
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.content

    def __replace_files(self,
                        page: BeautifulSoup,
                        base: ParseResult,
                        tag_type: str,
                        attr: str):
        for tag in page.find_all(tag_type):
            url = tag.get(attr)
            if not url:
                continue
            url = utils.normalize_link(url, base)
            try:
                path = self.load_file(url)
            except HTTPError:
                continue
            tag[attr] = path

    def __replace_links(self, page: BeautifulSoup, base: ParseResult):
        for link in page.find_all('a'):
            url = link.get('href')
            if not url:
                continue
            url = utils.normalize_link(url, base)
            link['href'] = self.__url_prefix + url
