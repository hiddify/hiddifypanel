import sys

import click
from flask.cli import FlaskGroup

from . import create_app_wsgi


def _fast_get_setting() -> int | None:
    if len(sys.argv) < 3 or sys.argv[1] != "get-setting":
        return None
    from hiddifypanel.panel.setting_cli import print_setting

    return print_setting(sys.argv[2])


@click.group(
    cls=FlaskGroup,
    create_app=create_app_wsgi,
)
def main():
    pass


if __name__ == "__main__":  # pragma: no cover
    # code = _fast_get_setting()
    # if code is not None:
    #     raise SystemExit(code)
    main()
