from bottle import Bottle, static_file, request

from src.page_loader import PageLoader


class App(Bottle):
    def __init__(self,
                 loader: PageLoader,
                 storage_path: str,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__loader = loader
        self.__storage_path = storage_path

        self.route('/', callback=self.index)
        self.route('/static/<filename:path>', callback=self.server_static)

    def index(self) -> str:
        return self.__loader.load(request.query.url)

    def server_static(self, filename: str) -> str:
        print(filename)
        return static_file(filename, root=self.__storage_path)
