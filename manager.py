#!/usr/bin/env python

import logging
import asyncio
from tornado.options import define, options
import tornado.options
import tornado.platform.asyncio

from yiyun import create_app
from yiyun.models import (BaseModel, Admin, User, Team, Activity,
                          Sport, TeamMember, TeamMemberGroup, Client, Match,
                          MatchStatus)


from yiyun.helpers import setting_from_object, find_subclasses, create_token
import local_settings

define("port", default=9000, help="run on the given port", type=int)
define("cmd", default='runserver', metavar="runserver|createall")
define("debug", default=False, help="debug mode", type=bool)


def main():

    settings = setting_from_object(local_settings)
    if settings.get('debug', False):
        options.logging = "debug"

    tornado.options.parse_command_line()

    if options.debug:
        settings['debug'] = True

    if options.cmd == 'createall':
        """Create all database tables"""

        create_app(settings)

        if not Sport.table_exists():
            Sport.create_table()

        if not User.table_exists():
            User.create_table()

        if not Team.table_exists():
            Team.create_table()

        if not TeamMemberGroup.table_exists():
            TeamMemberGroup.create_table()

        if not TeamMember.table_exists():
            TeamMember.create_table()

        if not Activity.table_exists():
            Activity.create_table()

        if not Admin.table_exists():
            Admin.create_table()

        if not Match.table_exists():
            Match.create_table()

        if not MatchStatus.table_exists():
            MatchStatus.create_table()

        models = find_subclasses(BaseModel)
        for model in models:
            if model._meta.db_table.startswith("__"):
                print(("table skip: " + model._meta.db_table))
            elif model.table_exists():
                print(('table exist: ' + model._meta.db_table))
            else:
                model.create_table()
                print(('table created: ' + model._meta.db_table))

        print('create all [ok]')

    elif options.cmd == 'createadmin':
        app = create_app(settings)
        Admin.create(
            username="admin",
            password=Admin.create_password("admin"),
            mobile="17088888888",
            email="admin@yiyun.cn",
            name="Admin",
            is_superadmin=True,
            state=1
        )

    elif options.cmd == 'createclient':
        app = create_app(settings)
        Client.create(
            name="ios",
            key=create_token(32),
            secret=create_token(32)
        )

    elif options.cmd == 'run_as_wsgi':
        logging.info('server started. port %s' % options.port)

        import gevent.wsgi

        app = create_app(settings)

        # 转换成wsgi实例
        wsgi_app = tornado.wsgi.WSGIAdapter(app)

        http_server = gevent.wsgi.WSGIServer(('', options.port), wsgi_app)
        http_server.serve_forever()

    elif options.cmd == 'runserver':

        tornado.platform.asyncio.AsyncIOMainLoop().install()
        ioloop = asyncio.get_event_loop()

        app = create_app(settings)
        app.listen(options.port, xheaders=True)

        print("running...")
        ioloop.run_forever()
    elif options.cmd == "fix_notify":
        from fix_script.fix_match_start_nofity import fix_match_start_notify
        fix_match_start_notify()


if __name__ == '__main__':
    main()
