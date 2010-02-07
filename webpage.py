#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import web
from web.contrib.template import render_mako
from board import board

urls = (
    '/(m/|)', 'main_page',
 #   '/(m/|)\*', 'board_list', 
    '/(m/|)\+join/', 'join',
    '/(m/|)\+login/', 'login',
    '/(m/|)\+logout/', 'logout',
    '/(m/|)\+u/(\S*)/', 'personal_page',
    '/(m/|)\+u/(\S*)/settings/', 'personal_settings',
    '/(m/|)\+u/(\S*)/favorites/', 'personal_favorites',
    '/(m/|)\+u/(\S*)/recent(\?\S*|)/', 'personal_recent',
    '/(m/|)\+help/(\S*)/', 'help',
    '/(m/|)\+credits/', 'credits',
# 다른 모든 action은 view_board 위로 올라가야 함.
    '/(m/|)(\S*)/\*', 'view_subboard_list',
    '/(m/|)(\S*)(\?\S*|)', 'view_board',
)

app = web.application(urls, globals(), autoreload = True)

desktop_render = render_mako(
    directories = [os.path.join(os.path.dirname(__file__), 'templates/desktop/').replace('\\','/'),],
    input_encoding = 'utf-8', output_encoding = 'utf-8',
)

mobile_render = render_mako(
    directories = [os.path.join(os.path.dirname(__file__), 'templates/mobile/').replace('\\','/'),],
    input_encoding = 'utf-8', output_encoding = 'utf-8',
)

class main_page:
    def GET(self, mobile):
        if not mobile:
            return desktop_render.main(title = "Noah3K", lang="ko")
        else:
            return mobile_render.main()

class join:
    def GET(self, mobile):
        if not mobile:
            return desktop_render.join(title = u"회원 가입 - Noah3K", lang="ko")
        else:
            return mobile_render.join()
    def POST(self, mobile):
        pass

class login:
    def GET(self, mobile):
        if not mobile:
            return desktop_render.login(title = u"로그인 - Noah3K", lang="ko")
        else:
            return mobile_render.login()
    def POST(self, mobile):
        pass

class logout:
    def GET(self, mobile):
        if not mobile:
            return desktop_render.logout(title = u"로그아웃 - Noah3K", lang="ko")
        else:
            return mobile_render.logout()

class help:
    def GET(self, mobile, context):
        if not mobile:
            return desktop_render.help(title = u"도움말: %s - Noah3K" % context, lang="ko")
        else:
            return mobile_render.help()

class credits:
    def GET(self, mobile):
        if not mobile:
            return desktop_render.credits(title = u"개발자 정보 - Noah3K", lang="ko")
        else:
            return mobile_render.credits()

class view_board:
    def GET(self, mobile, board_name, query_string):
        b = board()
        board_id = b._get_board_id_from_path(board_name)
        if board_id < 0:
            return # No such board
        board_info = b.get_board_info(board_id)
        # bSerial: board_id, bName: 전체 경로, uSerial: 보대, bParent: 부모 보드, bDescription: 보드 짧은 설명
        # bDatetime: 개설 시간, bInformation: 보드 긴 설명, bType = 디렉터리/보드/블로그,
        # bReply: bWrite: bComment: 모름
        if not mobile:
            return desktop_render.view_board(title = u"%s - Noah3K" % board_info.bName, board_path = board_info.bName[1:],
                    board_desc = board_info.bDescription, lang="ko")
        else:
            return mobile_render.view_board()

class view_subboard_list:
    def GET(self, mobile, board_name):
        print "view_subboard_list"
        b = board()
        board_id = b._get_board_id_from_path(board_name)
        if board_id < 0:
            return # No such board
        board_info = b.get_board_info(board_id)
        child_board = b.get_child(board_id)
        if not mobile:
            return desktop_render.view_subboard_list(title = u"%s - Noah3K" % board_name, board_path = board_info.bName[1:],
                    board_desc = board_info.bDescription, child_boards = child_board, lang="ko")
        else:
            return mobile_render.view_subboard_list()

if __name__ == "__main__":
    app.run()
