#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import web
from web.contrib.template import render_mako
import config
import board, user
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
#    r'/(m/|)(\S*)/\+read/(\d*)', 'read_article',
#    r'/(m/|)(\S*)/\+modify/(\d*)', 'modify_article',
#    r'/(m/|)(\S*)/\+write', 'write_article',
#    r'/(m/|)(\S*)/\+delete/(\d*)', 'delete_article',
#    r'/(m/|)(\S*)/\+reply/(\d*)', 'reply_to_article',
    r'/(m/|)(\S*)/\+(\w*)/(\d*)', 'article_actions',
#    r'/(m/|)(\S*)/\*', 'view_subboard_list',
#    r'/(m/|)(\S*)/\+cover', 'view_cover',
#    r'/(m/|)(\S*)/\+admin', 'view_admin',
    r'/(m/|)(\S*)/(\+(\w*)|\*)', 'board_actions',
    r'/(m/|)(\S*)', 'view_board',
)

app = web.application(urls, globals(), autoreload = True)
if web.config.get('_session') is None:
    session = web.session.Session(app, web.session.DiskStore('sessions'), {'count':0})
    web.config._session = session
else:
    session = web.config._session

desktop_render = render_mako(
    directories = [os.path.join(os.path.dirname(__file__), 'templates/desktop/').replace('\\','/'),],
    input_encoding = 'utf-8', output_encoding = 'utf-8',
)

mobile_render = render_mako(
    directories = [os.path.join(os.path.dirname(__file__), 'templates/mobile/').replace('\\','/'),],
    input_encoding = 'utf-8', output_encoding = 'utf-8',
)

if web.config.get('_database') is None:
    db = web.database(dbn=config.db_type, user=config.db_user,
            pw = config.db_password, db = config.db_name,
            host=config.db_host, port=int(config.db_port))
    web.config._database = db
else:
    db = web.config._database

class main_page:
    def GET(self, mobile):
        v = board_actions()
        return v.subboard_list_get(mobile, "")
#        if not mobile:
#            return desktop_render.main(title = "Noah3K", lang="ko")
#        else:
#            return mobile_render.main()

class join:
    def GET(self, mobile):
        if not mobile:
            return desktop_render.join(title = u"회원 가입 - Noah3K",
                   lang="ko", board_desc=u"회원 가입", session = session)
        else:
            return mobile_render.join()
    def POST(self, mobile):
        pass

class login:
    def GET(self, mobile):
        referer = web.ctx.env.get('HTTP_REFERER', '/')
        if not mobile:
            return desktop_render.login(title = u"로그인 - Noah3K", board_desc=u"로그인",
                    lang="ko", session = session, referer = referer)
        else:
            return mobile_render.login()
    def POST(self, mobile):
        username, password = '', ''
        err = ''
        valid = True
        login = False
        username, password = web.input().username, web.input().password
        referer = web.input().url
        username, password = username.strip(), password.strip()
        if username == '' or password == '':
            err = u"사용자 이름이나 암호를 입력하지 않았습니다."
            valid = False

        if valid:
            login = user.login(username, password)
            if login[0]:
                # 로그인 성공. referer로 돌아감.
                err = u"로그인 성공"
                session.uid = user._get_uid_from_username(username)
                login = True
            else:
                # 로그인 실패
                err = login[1]
        if not login:
            return desktop_render.login(title = u"로그인 - Noah3K", board_desc=u"로그인",
                    lang="ko", session = session,
                    error = err, referer = referer)
        else:
            raise web.seeother(web.input().url)
            # 이전 페이지로 '묻지 않고' 되돌림

class logout:
    def GET(self, mobile):
        session.uid = 0
        session.kill()
        referer = web.ctx.env.get('HTTP_REFERER', '/')
        raise web.seeother(referer)

class help:
    def GET(self, mobile, context):
        if not mobile:
            return desktop_render.help(title = u"도움말: %s - Noah3K" % context, lang="ko", session = session)
        else:
            return mobile_render.help()

class credits:
    def GET(self, mobile):
        if not mobile:
            return desktop_render.credits(title = u"개발자 정보 - Noah3K",
                   lang="ko", board_desc=u"개발자 정보", session = session)
        else:
            return mobile_render.credits()

class view_board:
    def GET(self, mobile, board_name):
        page_size = 20
        board_id = board._get_board_id_from_path(board_name)
        if board_id < 0:
            return # No such board
        board_info = board.get_board_info(board_id)
        if board_info.bType == 0: # 디렉터리
            v = board_actions()
            return v.subboard_list_get(mobile, board_name)

        qs = web.ctx.query
        if len(qs) > 0:
            qs = qs[1:]
            qs = parse_qs(qs)

        if qs:
            page = int(qs['page'][0])
        else:
            page = board._get_total_page_count(board_id, page_size)
        # bSerial: board_id, bName: 전체 경로, uSerial: 보대, bParent: 부모 보드, bDescription: 보드 짧은 설명
        # bDatetime: 개설 시간, bInformation: 보드 긴 설명, bType = 디렉터리/보드/블로그,
        # bReply: bWrite: bComment: 모름
        if not mobile:
            return desktop_render.view_board(title = u"%s - Noah3K" % board_info.bName, board_path = board_info.bName[1:],
                board_desc = board_info.bDescription, lang="ko", articles=board.get_article_list(board_id, page_size, page), page=page,
                total_page = board._get_total_page_count(board_id, page_size),
                session = session)
        else:
            return mobile_render.view_board()

class article_actions:

    def read_get(self, mobile, board_name, article_id):
        board_id = board._get_board_id_from_path(board_name)
        if board_id < 0:
            return
        board_info = board.get_board_info(board_id)
        board_path = board_info.bName[1:]
        board_desc = board_info.bDescription
        article = board.get_article(board_id, article_id)
        comment = board.get_comment(article_id)
        if not article:
            return desktop_render.error(lang="ko", error_message = u"글 없음" )
        if not mobile:
            return desktop_render.read_article(article = article,
                title = u"%s - Noah3K" % article.aTitle,
                board_path = board_path, board_desc = board_desc,
                comments = comment, lang="ko", session = session)
        else:
            return mobile_render.read_article()

    def reply_get(self, mobile, board_name, article_id):
        try:
            current_uid = session.uid
        except:
            return desktop_render.error(lang="ko", error_message = u"로그인되지 않음" )
        if current_uid < 1:
            return desktop_render.error(lang="ko", error_message = u"잘못된 사용자 ID" )

        board_id = board._get_board_id_from_path(board_name)
        if board_id < 0:
            return
        board_info = board.get_board_info(board_id)
        board_path = board_info.bName[1:]
        board_desc = board_info.bDescription
        if not mobile:
            return desktop_render.editor(title = u"답글 쓰기 - %s - Noah3K" % board_name,
                    action='reply/%s' % article_id, action_name = u"답글 쓰기",
                    board_path = board_path, board_desc = board_desc,
                    lang="ko", session = session)

    def reply_post(self, mobile, board_name, article_id):
        try:
            current_uid = session.uid
        except:
            return
        pass
        reply = dict(title = web.input().title, body = web.input().content)
        board_id = board._get_board_id_from_path(board_name)
        board_info = board.get_board_info(board_id)
        board_path = board_info.bName[1:]
        if board_id < 0:
            return
        ret = board.reply_article(current_uid, board_id, article_id, reply)
        if ret[0] == True:
            raise web.seeother('/%s/+read/%s' % (board_path, ret[1]))
        else:
            return desktop_render.error(lang='ko', error_message = ret[1])

    def modify_get(self, mobile, board_name, article_id):
        try:
            current_uid = session.uid
        except:
            return desktop_render.error(lang="ko", error_message = u"로그인되지 않음" )
        if current_uid < 1:
            return desktop_render.error(lang="ko", error_message = u"잘못된 사용자 ID" )

        board_id = board._get_board_id_from_path(board_name)
        if board_id < 0:
            return
        board_info = board.get_board_info(board_id)
        board_path = board_info.bName[1:]
        board_desc = board_info.bDescription
        article = board.get_article(board_id, article_id)
        if not mobile:
            return desktop_render.editor(title = u"글 수정하기 - %s - Noah3K" % board_name,
                    action='modify/%s' % article_id, action_name = u"글 수정하기",
                    board_path = board_path, board_desc = board_desc,
                    article_title = article.aTitle, body = article.aContent,
                    lang="ko", session = session)

    def modify_post(self, mobile, board_name, article_id):
        try:
            current_uid = session.uid
        except:
            return
        article = dict(title = web.input().title, body = web.input().content)
        board_id = board._get_board_id_from_path(board_name)
        board_info = board.get_board_info(board_id)
        board_path = board_info.bName[1:]
        if board_id < 0:
            return
        ret = board.modify_article(current_uid, board_id, article_id, article)
        if ret[0] == True:
            raise web.seeother('/%s/+read/%s' % (board_path, ret[1]))
        else:
            return desktop_render.error(lang='ko', error_message = ret[1])

    def comment_post(self, mobile, board_name, article_id):
        try:
            current_uid = session.uid
        except:
            return
        comment = web.input().comment
        board_id = board._get_board_id_from_path(board_name)
        board_info = board.get_board_info(board_id)
        board_path = board_info.bName[1:]
        if board_id < 0:
            return
        ret = board.write_comment(current_uid, board_id, article_id, comment)
        if ret[0] == True:
            raise web.seeother('/%s/+read/%s' % (board_name, article_id))
        else:
            return desktop_render.error(lang='ko', error_message = ret[1])

    def delete_get(self, mobile, board_name, article_id):
        try:
            current_uid = session.uid
        except:
            return
        ret = board.delete_article(current_uid, article_id)
        if ret[0] == True:
            raise web.seeother('/%s' % (board_name))
        else:
            return desktop_render.error(lang='ko', error_message = ret[1])

    def comment_delete_get(self, mobile, board_name, comment_id):
        try:
            current_uid = session.uid
        except:
            return
        ret = board.delete_comment(current_uid, comment_id)
        if ret[0] == True:
            raise web.seeother('/%s/+read/%s' % (board_name, ret[1]))
        else:
            return desktop_render.error(lang='ko', error_message = ret[1])

    def GET(self, mobile, board_name, action, article_id):
        try:
            return eval('self.'+action+'_get')(mobile, board_name, article_id)
        except:
            return

    def POST(self, mobile, board_name, action, article_id):
        try:
            return eval('self.'+action+'_post')(mobile, board_name, article_id)
        except:
            pass

class board_actions:

    def write_get(self, mobile, board_name):
        try:
            current_uid = session.uid
        except:
            return desktop_render.error(lang="ko", error_message = u"로그인되지 않음" )
        if current_uid < 1:
            return desktop_render.error(lang="ko", error_message = u"잘못된 사용자 ID" )

        board_id = board._get_board_id_from_path(board_name)
        if board_id < 0:
            return
        board_info = board.get_board_info(board_id)
        board_path = board_info.bName[1:]
        board_desc = board_info.bDescription
        if not mobile:
            return desktop_render.editor(title = u"글 쓰기 - %s - Noah3K" % board_name,
                    action='write', action_name = u"글 쓰기",
                    board_path = board_path, board_desc = board_desc,
                    lang="ko", session = session)

    def write_post(self, mobile, board_name):
        try:
            current_uid = session.uid
        except:
            return
        pass
        article = dict(title = web.input().title, body = web.input().content)
        board_id = board._get_board_id_from_path(board_name)
        board_info = board.get_board_info(board_id)
        board_path = board_info.bName[1:]
        if board_id < 0:
            return
        ret = board.write_article(current_uid, board_id, article)
        if ret[0] == True:
            raise web.seeother('/%s/+read/%s' % (board_path, ret[1]))
        else:
            return desktop_render.error(lang='ko', error_message = ret[1])

    def subboard_list_get(self, mobile, board_name):
        board_id = board._get_board_id_from_path(board_name)
        if board_id < 0:
            return # No such board
        board_info = board.get_board_info(board_id)
        child_board = board.get_child(board_id)
        if board_name == "":
            board_name = u"초기 화면"
            board_path = ""
        else:
            board_path = board_info.bName[1:]
        if not mobile:
            return desktop_render.view_subboard_list(title = u"%s - Noah3K" % board_name, board_path = board_path,
                    board_desc = board_info.bDescription, child_boards = child_board, lang="ko", session = session)
        else:
            return mobile_render.view_subboard_list()

    def GET(self, mobile, board_name, action, dummy):
        if action[0] == '+':
            action = dummy
        if action == '*':
            action = 'subboard_list'
        return eval('self.'+action+'_get')(mobile, board_name)

    def POST(self, mobile, board_name, action, dummy):
        if action[0] == '+':
            action = dummy
        return eval('self.'+action+'_post')(mobile, board_name)

if __name__ == "__main__":
    app.run()
