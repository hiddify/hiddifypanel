from typing import TYPE_CHECKING
import importlib

class LazyLoader:
    def __init__(self, module_name: str,package=None):
        self.module_name = module_name
        self._module = None
        self.package=package


    def __getattr__(self, item):
        if self._module is None:
            self._module = importlib.import_module(self.module_name,self.package)
        return getattr(self._module, item)

if TYPE_CHECKING:
    from . import system
    from . import importer
    from . import github_issue
    from . import flask
    from . import convert
    from . import random
    from . import encode
    from . import auth
    from . import model
    from . import crypto
    from . import proxy
    from . import node
    from . import utils
    from . import network
else:
    # Define modules for lazy loading
    network = LazyLoader(".network",__name__)
    system = LazyLoader(".system",__name__)
    importer = LazyLoader(".importer",__name__)
    github_issue = LazyLoader(".github_issue",__name__)
    flask = LazyLoader(".flask",__name__)
    convert = LazyLoader(".convert",__name__)
    random = LazyLoader(".random",__name__)
    encode = LazyLoader(".encode",__name__)
    auth = LazyLoader(".auth",__name__)
    utils = LazyLoader(".utils",__name__)
    model = LazyLoader(".model",__name__)
    crypto = LazyLoader(".crypto",__name__)
    proxy = LazyLoader(".proxy",__name__)
    node = LazyLoader(".node",__name__)