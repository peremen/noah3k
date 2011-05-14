#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import web
import util
import config
from config import db, render
import board, user, article
from cgi import parse_qs
from datetime import datetime
import posixpath
from web_article import article_actions
from web_board import board_actions
from web_user import personal_page, personal_actions, personal_actions_unauthorized, personal_page_others
from web_main import main_actions
from web_noah2k_support import noah2k_support
from web_api import api
import i18n
_ = i18n.custom_gettext
#import linesman.middleware

urls = (
# 다른 모든 action은 view_board 위로 올라가야 함.
    r'/(.*)/', 'redirect',
    r'/(\w*).jsp', 'noah2k_support',
    r'/\+api', 'api',
    r'/(?:' + config.theme_regex_main + ')?', 'main_page',
    r'/(?:' + config.theme_regex + ')?\+help/(\S*)', 'help',

    r'/(?:' + config.theme_regex + ')?\+u/(\S*)/\+(\w*)', 'personal_actions_unauthorized',
    r'/(?:' + config.theme_regex + ')?\+u/\+(\w*)', 'personal_actions',
    r'/(?:' + config.theme_regex + ')?\+u/(\w*)', 'personal_page_others',
    r'/(?:' + config.theme_regex + ')?\+u', 'personal_page',

    r'/(?:' + config.theme_regex + ')?\+(\w*)', 'main_actions',
    r'/(?:' + config.theme_regex + ')?(\S*)/\+(\w*)/(\d*)', 'article_actions',
    r'/(?:' + config.theme_regex + ')?(\S*)/((?:\+)\w*|\*)', 'board_actions',
    r'/(?:' + config.theme_regex + ')?(\S*)', 'view_board',
)

app = web.application(urls, globals(), autoreload = True)

if web.config.get('_session') is None:
    store = web.session.DBStore(db, 'sessions')
    session = web.session.Session(app, store, initializer={'count':0})
    web.config._session = session
else:
    session = web.config._session

def session_hook():
    web.ctx.session = session
app.add_processor(web.loadhook(session_hook))

class redirect:
    def GET(self, path):
        raise web.seeother('/' + path)
    def POST(self, path):
        raise web.seeother('/' + path)

class main_page:
    @util.theme
    def GET(self):
        if web.config.theme == 'm':
            v = board_actions()
            return v.subboard_list_get()
        else:
            child_board = board.get_child(1)

            notice_board_path = '/divisionCS/Notice'
            notice_board_id = board._get_board_id_from_path(notice_board_path)
            a = article.get_recent_article_list(notice_board_id, 5)

            student_notice_board_path = '/divisionCS/studentNotice'
            student_notice_board_id = board._get_board_id_from_path(student_notice_board_path)
            b = article.get_recent_article_list(student_notice_board_id, 5)

            freeboard_path = '/garbage'
            freeboard_id = board._get_board_id_from_path(freeboard_path)
            c = article.get_recent_article_list(freeboard_id, 5)

            undergraduate_path = '/divisionCS/undergraduate'
            undergraduate_id = board._get_board_id_from_path(undergraduate_path)
            d = article.get_recent_article_list(undergraduate_id, 5)

            return util.render().main(title = u'전산학과 BBS 노아입니다', lang='ko',
                    board_desc = _('[KAIST CS BBS]'), board_path = '',
                    child_boards = child_board,
                    notice_board_path = notice_board_path, notice_articles = a,
                    student_notice_board_path = student_notice_board_path, student_notice_articles = b, 
                    freeboard_path = freeboard_path, freeboard_articles = c,
                    undergraduate_path = undergraduate_path, undergraduate_articles = d,
                    help_context = 'main')

class help:
    @util.theme
    def GET(self, context):
        return util.render().help(title = _('Help: %s') % context, lang="ko",
                help_context = context)

class view_board:
    @util.theme
    def GET(self, board_name):
        if board_name == '*' or board_name == '^root':
            v = board_actions()
            return v.subboard_list_get()

        board_id = board._get_board_id_from_path(board_name)
        if board_id < 0:
            #try to find regex match
            board_id = board._get_board_id_from_regex_path(board_name)
            if board_id < 0:
                raise web.notfound(util.render().error(lang='ko', error_message=_('INVALID_BOARD'), help_context='error'))
            else:
                path = board._get_path_from_board_id(board_id)
                raise web.seeother(util.link(path))

        board_info = board.get_board_info(board_id)
        if board_info.bType == 0: # 디렉터리
            v = board_actions()
            return v.subboard_list_get(board_name, board_id)

        #processing new_article
        if web.ctx.session.has_key('uid'):
            uid = web.ctx.session.uid
            user.update_unreaded_articles_board(uid, board_id)

        qs = web.ctx.query
        if len(qs) > 0:
            qs = qs[1:]
            qs = parse_qs(qs)


        t = article._get_total_page_count(board_id, config.page_size)
        if qs:
            page = int(qs['page'][0])
        else:
            page = t

        a = article.get_article_list(board_id, config.page_size, page)
        m = article.get_marked_article(board_id)

        return util.render().board(lang="ko",
            title = board_info.bName,
            board_path = board_info.bName[1:],
            board_desc = board_info.bDescription,
            stylesheet = board_info.stylesheet,
            articles=a, marked_articles = m,
            total_page = t, page = page, feed = True,
            help_context = 'board')

application = app.wsgifunc()
#application = linesman.middleware.ProfilingMiddleware(app.wsgifunc(), session_history_path = os.path.join(os.path.dirname(__file__), 'error_report', 'sessions.dat'))

if __name__ == "__main__":
    app.run()
