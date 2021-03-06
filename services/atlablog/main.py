import asyncio

from peewee_async import PostgresqlDatabase
from sanic import Sanic
from sanic.config import Config
from sanic.response import json, text
from sanic.exceptions import ServerError

try:
    import uvloop as async_loop
except ImportError:
    async_loop = asyncio

from _buisness_views import BLOG_ENTRY_DB_NAME, COMMENT_ENTRY_DB_NAME, \
    FILES_ENTRY_DB_NAME
from _buisness_views.registration import bp as registration
from _buisness_views.login import bp as login
from _buisness_views.logout import bp as logout
from _buisness_views.blog import bp as blog
from _buisness_views.files import bp as files
from sessions import session_blueprint as sessions, get_session_service
from users import user_blueprint as users, get_user_service
from entries import entry_blueprint as entries, get_entry_service
from views import View
import settings


def make_app(view=None, database=None):
    if not view:
        view = View({"HTML_TEMPLATES_DIR": settings.TEMPLATES_DIR})
    if not database:
        database = PostgresqlDatabase(database=settings.DATABASE)

    app = Sanic(__name__)
    app.config = Config()
    app.config.LOGO = "Atlantis! Go FAST!"
    app.config.REQUEST_MAX_SIZE = 2000000  # 2 megababies
    app.config.REQUEST_TIMEOUT = 60 * 5  # 5 min
    app.static('/static', settings.STATIC_DIR)

    @app.middleware('response')
    async def halt_response(request, response):
        response.headers['Content-Security-Policy'] = \
            "default-src 'self' 'unsafe-inline';"
    return app


# ----------------------------------------------- #
# Run Server
# ----------------------------------------------- #

def recreatedb(loop=None):
    # loop
    if not loop:
        loop = async_loop.new_event_loop()
        asyncio.set_event_loop(loop)

    # init db
    service = get_user_service()
    service.dropdb()
    service.initdb()
    service = get_session_service()
    service.dropdb()
    service.initdb()
    service = get_entry_service(BLOG_ENTRY_DB_NAME)
    service.dropdb()
    service.initdb()
    service = get_entry_service(COMMENT_ENTRY_DB_NAME)
    service.dropdb()
    service.initdb()
    service = get_entry_service(FILES_ENTRY_DB_NAME)
    service.dropdb()
    service.initdb()


def main(debug=False, run=True):
    # loop
    loop = async_loop.new_event_loop()
    asyncio.set_event_loop(loop)
    # database
    database = PostgresqlDatabase(database=settings.DATABASE)
    #  templates
    view = View({"HTML_TEMPLATES_DIR": settings.TEMPLATES_DIR})
    # app
    app = make_app(view, database)
    app.blueprint(sessions, db=database, db_name='sessions', loop=loop)
    app.blueprint(users, db=database, db_name='users', loop=loop,
                  sessions_db_name='sessions')
    app.blueprint(entries, db=database, db_name=BLOG_ENTRY_DB_NAME, loop=loop)
    app.blueprint(entries, db=database, db_name=COMMENT_ENTRY_DB_NAME, loop=loop)
    app.blueprint(entries, db=database, db_name=FILES_ENTRY_DB_NAME, loop=loop)
    app.blueprint(registration, view=view)
    app.blueprint(login, view=view)
    app.blueprint(logout, view=view)
    app.blueprint(files, view=view)
    app.blueprint(blog, view=view)

    if run:
        app.run(host="0.0.0.0", port=8000, loop=loop, debug=debug)
    return app, loop, view, database


if __name__ == '__main__':
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] == 'recreatedb':
        app, loop, view, database = main(debug=True, run=False)
        recreatedb(loop)
    else:
        main(debug=True)
