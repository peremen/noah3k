#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import web
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
import i18n
_ = i18n.custom_gettext

urls = (
# 다른 모든 action은 view_board 위로 올라가야 함.
    r'/(.*)/', 'redirect',
    r'/(\w*).jsp', 'noah2k_support',
    r'/(\w*|)', 'main_page',
    r'/(?:(\w+)/)?\+help/(\S*)', 'help',

    r'/(?:(\w+)/)?\+u/(\S*)/\+(\w*)', 'personal_actions_unauthorized',
    r'/(?:(\w+)/)?\+u/\+(\w*)', 'personal_actions',
    r'/(?:(\w+)/)?\+u/(\w*)', 'personal_page_others',
    r'/(?:(\w+)/)?\+u', 'personal_page',

    r'/(?:(\w+)/)?\+(\w*)', 'main_actions',
    r'/(?:(\w+)/)?(\S*)/\+(\w*)/(\d*)', 'article_actions',
    r'/(?:(\w+)/)?(\S*)/((?:\+)\w*|\*)', 'board_actions',
    r'/(?:(\w+)/)?(\S*)', 'view_board',
)

app = web.application(urls, globals(), autoreload = True)
application = app.wsgifunc()

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
    def GET(self, theme):
        if theme != "" and not render.has_key(theme):
            vb = view_board()
            return vb.GET('default', theme)
        if theme == 'm':
            v = board_actions()
            return v.subboard_list_get(theme)
        else:
            if theme == '':
                theme = 'default'
            child_board = board.get_child(1)

            notice_board_path = '/divisionCS/Notice'
            notice_board_id = board._get_board_id_from_path(notice_board_path)
            a = article.get_recent_article_list(notice_board_id, 5)

            student_notice_board_path = '/divisionCS/studentNotice'
            student_notice_board_id = board._get_board_id_from_path(student_notice_board_path)
            b = article.get_recent_article_list(student_notice_board_id, 5)
            return render[theme].main(title = u'전산학과 BBS 노아입니다', lang='ko',
                    board_desc = _('[KAIST CS BBS]'), board_path = '',
                    child_boards = child_board, notice_board_path = notice_board_path,
                    notice_articles = a, student_notice_board_path = student_notice_board_path,
                    student_notice_articles = b, help_context = 'main')

class help:
    def GET(self, theme, context):
        if not render.has_key(theme):
            theme = 'default'
        return render[theme].help(title = _('Help: %s') % context, lang="ko",
                help_context = context)

class view_board:
    def GET(self, theme, board_name):
        if board_name[0] == '/':
            board_name = board_name[1:]
        if not render.has_key(theme):
            if theme == None:
                theme = ''
            board_name = posixpath.join(theme, board_name)
            theme = 'default'
        if board_name == '*' or board_name == '^root':
            v = board_actions()
            return v.subboard_list_get(theme)
        board_id = board._get_board_id_from_path(board_name)
        if board_id < 0:
            #try to find regex match
            board_id = board._get_board_id_from_regex_path(board_name)
            if board_id < 0:
                raise web.notfound(render[theme].error(lang='ko', error_message=_('INVALID_BOARD'), help_context='error'))
            else:
                path = board._get_path_from_board_id(board_id)
                if theme == 'default':
                    raise web.seeother(path)
                else:
                    raise web.seeother(posixpath.join('/%s' % theme, path[1:]))

        board_info = board.get_board_info(board_id)
        if board_info.bType == 0: # 디렉터리
            v = board_actions()
            return v.subboard_list_get(theme, board_name, board_id)

        #processing new_article
        if web.ctx.session.has_key('uid'):
            uid = web.ctx.session.uid
            user.update_unreaded_articles_board(uid, board_id)


        qs = web.ctx.query
        if len(qs) > 0:
            qs = qs[1:]
            qs = parse_qs(qs)

        if qs:
            page = int(qs['page'][0])
        else:
            page = article._get_total_page_count(board_id, config.page_size)

        # bSerial: board_id, bName: 전체 경로, uSerial: 보대, bParent: 부모 보드, bDescription: 보드 짧은 설명
        # bDatetime: 개설 시간, bInformation: 보드 긴 설명, bType = 디렉터리/보드/블로그,
        # bReply: bWrite: bComment: 모름
        a = article.get_article_list(board_id, config.page_size, page)
        m = article.get_marked_article(board_id)
        t = article._get_total_page_count(board_id, config.page_size)
        return render[theme].view_board(lang="ko",
            title = board_info.bName,
            board_path = board_info.bName[1:],
            board_desc = board_info.bDescription,
            articles=a, marked_articles = m,
            total_page = t, page = page, feed = True,
            help_context = 'view_board')

if __name__ == "__main__":
    app.run()
