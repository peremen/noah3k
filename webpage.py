#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import web
from web.contrib.template import render_mako
from board import board
from user import user
from cgi import parse_qs

urls = (
    r'/(m/|)', 'main_page',
 #   '/(m/|)\*', 'board_list', 
    r'/(m/|)\+join', 'join',
    r'/(m/|)\+login', 'login',
    r'/(m/|)\+logout', 'logout',
    r'/(m/|)\+u/(\S*)', 'personal_page',
    r'/(m/|)\+u/(\S*)/settings', 'personal_settings',
    r'/(m/|)\+u/(\S*)/favorites', 'personal_favorites',
    r'/(m/|)\+u/(\S*)/recent', 'personal_recent',
    r'/(m/|)\+help/(\S*)', 'help',
    r'/(m/|)\+credits', 'credits',
# 다른 모든 action은 view_board 위로 올라가야 함.
    r'/(m/|)(\S*)/\+read/(\d*)', 'read_article',
    r'/(m/|)(\S*)/\*', 'view_subboard_list',
    r'/(m/|)(\S*)', 'view_board',
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
        v = view_subboard_list()
        return v.GET(mobile, "")
#        if not mobile:
#            return desktop_render.main(title = "Noah3K", lang="ko")
#        else:
#            return mobile_render.main()

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
            return desktop_render.login(title = u"로그인 - Noah3K", board_desc=u"로그인",
                    lang="ko")
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
    def GET(self, mobile, board_name):
        page_size = 20
        b = board()
        board_id = b._get_board_id_from_path(board_name)
        if board_id < 0:
            return # No such board
        board_info = b.get_board_info(board_id)
        qs = web.ctx.query
        if len(qs) > 0:
            qs = qs[1:]
            qs = parse_qs(qs)

        if qs:
            page = int(qs['page'][0])
        else:
            page = b._get_total_page_count(board_id, page_size)
        # bSerial: board_id, bName: 전체 경로, uSerial: 보대, bParent: 부모 보드, bDescription: 보드 짧은 설명
        # bDatetime: 개설 시간, bInformation: 보드 긴 설명, bType = 디렉터리/보드/블로그,
        # bReply: bWrite: bComment: 모름
        if not mobile:
            return desktop_render.view_board(title = u"%s - Noah3K" % board_info.bName, board_path = board_info.bName[1:],
                board_desc = board_info.bDescription, lang="ko", articles=b.get_article_list(0, board_id, page_size, page), page=page,
                total_page = b._get_total_page_count(board_id, page_size))
        else:
            return mobile_render.view_board()

class view_subboard_list:
    def GET(self, mobile, board_name):
        b = board()
        board_id = b._get_board_id_from_path(board_name)
        if board_id < -1:
            return # No such board
        board_info = b.get_board_info(board_id)
        child_board = b.get_child(board_id)
        if board_name == "":
            board_name = u"초기 화면"
            board_path = ""
        else:
            board_path = board_info.bName[1:]
        if not mobile:
            return desktop_render.view_subboard_list(title = u"%s - Noah3K" % board_name, board_path = board_path,
                    board_desc = board_info.bDescription, child_boards = child_board, lang="ko")
        else:
            return mobile_render.view_subboard_list()


class read_article:
    def GET(self, mobile, board_name, article_id):
        b = board()
        board_id = b._get_board_id_from_path(board_name)
        if board_id < -1:
            return
        board_info = b.get_board_info(board_id)
        board_path = board_info.bName[1:]
        board_desc = board_info.bDescription
        article = b.get_article(0, board_id, int(article_id))
        # aSerial: 글 UID bSerial: 글이 있는 보드 aIndex: 게시판에 보이는 가상 글 번호 aTitle: 제목
        # aId: 글쓴이 ID aNick: 글쓴이의 당시 닉네임 
        # uSerial: 글쓴이의 UID (여기서 aId/aNick 유도 가능)
        # aContent: 본문 aLastGuest: 모름 aHit: 조회 수
        # aEmphasis: 강조 여부 aDatetime: 최초 작성 시간 aEditedDatetime: 수정 시간, 없으면 NULL
        # aLevel: 글 깊이 aParent: aLevel > 0의 경우 바로 윗 부모 글. assert(aLevel == 0 && aParent == NULL)
        # aRoot: 깊이가 계속 깊어져 갔을 때 최종적인 부모. aParent == NULL인 경우 자기 자신.
        if not mobile:
            return desktop_render.read_article(article = article,
                title = u"%s - Noah3K" % board_name,
                board_path = board_path, board_desc = board_desc,
                comments = None, lang="ko")
        else:
            return mobile_render.read_article()
if __name__ == "__main__":
    app.run()
