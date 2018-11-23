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
    URL_PREFIX = 'http://localhost:8080/?url='

    def __init__(self,
                 database: Redis,
                 storage_path: str):
        self.__database = database
        self.__storage_path = storage_path

    def load(self, url: str) -> str:
        result = self.__database.get(url)
        if result:
            return result.decode()

        base = urlparse(url)
        content = self.__get_content(url)
        page = BeautifulSoup(content, 'html.parser')

        handlers = [
            self.__replace_images,
            self.__replace_links,
            self.__replace_css,
            self.__replace_js,
        ]
        for handler in handlers:
            handler(page, base)

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

    def __replace_images(self, page: BeautifulSoup, base: ParseResult):
        for img in page.find_all('img'):
            url = img['src']
            url = utils.normalize_link(url, base)
            try:
                path = self.load_file(url)
            except HTTPError:
                continue
            img['src'] = path

    def __replace_links(self, page: BeautifulSoup, base: ParseResult):
        for link in page.find_all('a'):
            url = link.get('href')
            if not url:
                continue
            url = utils.normalize_link(url, base)
            link['href'] = self.URL_PREFIX + url

    def __replace_css(self, page: BeautifulSoup, base: ParseResult):
        for tag in page.find_all('link'):
            url = tag.get('href')
            if not url:
                continue
            url = utils.normalize_link(url, base)
            try:
                path = self.load_file(url)
            except HTTPError:
                continue
            tag['href'] = path

    def __replace_js(self, page: BeautifulSoup, base: ParseResult):
        for tag in page.find_all('script'):
            url = tag.get('src')
            if not url:
                continue
            url = utils.normalize_link(url, base)
            try:
                path = self.load_file(url)
            except HTTPError:
                continue
            tag['src'] = path
