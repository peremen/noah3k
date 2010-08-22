#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import web
from web.contrib.template import render_mako
import config
import board, user, article
from cgi import parse_qs
from datetime import datetime
import posixpath

desktop_render = render_mako(
    directories = [os.path.join(os.path.dirname(__file__), 'templates/desktop/').replace('\\','/'),],
    input_encoding = 'utf-8', output_encoding = 'utf-8',
)

mobile_render = render_mako(
    directories = [os.path.join(os.path.dirname(__file__), 'templates/mobile/').replace('\\','/'),],
    input_encoding = 'utf-8', output_encoding = 'utf-8',
)

class board_actions:
    def GET(self, mobile, board_name, action, dummy):
        if action[0] == '+':
            action = dummy
        if action == '*':
            action = 'subboard_list'
        return self.caller(mobile, board_name, action, 'get')

    def POST(self, mobile, board_name, action, dummy):
        if action[0] == '+':
            action = dummy
        return self.caller(mobile, board_name, action, 'post')

    def caller(self, mobile, board_name, action, method):
        board_id = board._get_board_id_from_path(board_name)
        if board_id < 0:
            raise web.notfound(desktop_render.error(lang='ko', error_message = 'INVALID_BOARD'))
        try:
            return eval('self.%s_%s' % (action, method))(mobile, board_name)
        except:
            raise web.notfound(desktop_render.error(lang='ko', error_message = 'INVALID_ACTION'))

    def write_get(self, mobile, board_name):
        try:
            current_uid = web.ctx.session.uid
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
                    lang="ko", )

    def write_post(self, mobile, board_name):
        try:
            current_uid = web.ctx.session.uid
        except:
            return
        a = dict(title = web.input().title, body = web.input().content)
        board_id = board._get_board_id_from_path(board_name)
        board_info = board.get_board_info(board_id)
        board_path = board_info.bName[1:]
        if board_id < 0:
            return
        ret = article.write_article(current_uid, board_id, a)
        if ret[0] == True:
            raise web.seeother('/%s/+read/%s' % (board_path, ret[1]))
        else:
            return desktop_render.error(lang='ko', error_message = ret[1])

    def rss_get(self, mobile, board_name):
        page_size = 20
        board_id = board._get_board_id_from_path(board_name)
        if board_id < 0:
            return # No such board
        board_info = board.get_board_info(board_id)
        if board_info.bType == 0: # 디렉터리
            return

        date = datetime.today()
        page = article._get_total_page_count(board_id, page_size)
        articles = article.get_article_list(board_id, page_size, page)
        web.header('Content-Type', 'application/rss+xml')
        return desktop_render.rss(board_path = board_info.bName[1:],
                board_desc = board_info.bDescription,
                articles=articles, today=date)

    def atom_get(self, mobile, board_name):
        page_size = 20
        board_id = board._get_board_id_from_path(board_name)
        if board_id < 0:
            return # No such board
        board_info = board.get_board_info(board_id)
        if board_info.bType == 0: # 디렉터리
            return

        date = datetime.today()
        page = article._get_total_page_count(board_id, page_size)
        articles = article.get_article_list(board_id, page_size, page)
        web.header('Content-Type', 'application/atom+xml')
        return desktop_render.atom(board_path = board_info.bName[1:],
                board_desc = board_info.bDescription,
                articles=articles, today=date)

    def summary_get(self, mobile, board_name):
        board_id = board._get_board_id_from_path(board_name)
        if board_id < 0:
            return
        board_info = board.get_board_info(board_id)
        return desktop_render.board_summary(board_info = board_info,
                board_path = board_info.bName[1:],
                board_desc = board_info.bDescription, lang='ko',
                title = u'정보 - %s - Noah3k' % board_info.bName,
                )

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
                    board_desc = board_info.bDescription, child_boards = child_board, lang="ko", )
        else:
            return mobile_render.view_subboard_list()

    def create_board_get(self, mobile, board_name):
        try:
            current_uid = web.ctx.session.uid
        except:
            return desktop_render.error(lang='ko', error_message='NOT_LOGGED_IN')
        board_id = board._get_board_id_from_path(board_name)
        if board_id < 0:
            return desktop_render.error(lang='ko', error_message='INVALID_BOARD')
        # if !acl.get_permission(modify_board, user):
        board_info = board.get_board_info(board_id)
        if current_uid != board_info.uSerial:
            return desktop_render.error(lang='ko', error_message='NO_PERMISSION')
        return desktop_render.board_editor(action='create_board', board_info = board_info,
                board_path = board_info.bName[1:],
                board_desc = board_info.bDescription, lang='ko',
                title = u'하위 게시판 만들기 - %s - Noah3k' % board_info.bName)

    def create_board_post(self, mobile, board_name):
        try:
            current_uid = web.ctx.session.uid
        except:
            return desktop_render.error(lang='ko', error_message='NOT_LOGGED_IN')
        board_id = board._get_board_id_from_path(board_name)
        if board_id < 0:
            return desktop_render.error(lang='ko', error_message='INVALID_BOARD')
        # if !acl.get_permission(modify_board, user):
        board_info = board.get_board_info(board_id)
        if current_uid != board_info.uSerial:
            return desktop_render.error(lang='ko', error_message='NO_PERMISSION')
        user_data = web.input()
        comment, write_by_other = 0, 0 # XXX: DB 스키마를 BOOLEAN으로 바꿔야 함
        if user_data.commentable == 'yes':
            comment = 1
        if user_data.writable == 'yes':
            write_by_other = 1
        owner_uid = user._get_uid_from_username(user_data.owner)
        if owner_uid < 0:
            return desktop_render.error(lang='ko', error_message='NO_SUCH_USER_FOR_BOARD_ADMIN')
        if user_data.name.strip() == '':
            return desktop_render.error(lang='ko', error_message = 'NO_NAME_SPECIFIED')
        new_path = posixpath.join('/', board_name, user_data.name)
        if board._get_board_id_from_path(new_path) > 0:
            return desktop_render.error(lang='ko', error_message = 'BOARD_EXISTS')

        settings = dict(path=new_path, board_owner = owner_uid,
                cover = user_data.information,
                description = user_data.description,
                type = int(user_data.type),
                guest_write = write_by_other,
                can_comment = comment,
                current_uid = current_uid)
        ret = board.create_board(board_id, settings)
        if ret[0] == False:
            return desktop_render.error(lang='ko', error_message = ret[1])
        raise web.seeother('%s' % (new_path))

    def modify_get(self, mobile, board_name):
        try:
            current_uid = web.ctx.session.uid
        except:
            return desktop_render.error(lang='ko', error_message='NOT_LOGGED_IN')
        board_id = board._get_board_id_from_path(board_name)
        if board_id < 0:
            return desktop_render.error(lang='ko', error_message='INVALID_BOARD')
        # if !acl.get_permission(modify_board, user):
        board_info = board.get_board_info(board_id)
        if current_uid != board_info.uSerial:
            return desktop_render.error(lang='ko', error_message='NO_PERMISSION')
        return desktop_render.board_editor(action='modify', board_info = board_info,
                board_path = board_info.bName[1:],
                board_desc = board_info.bDescription, lang='ko',
                title = u'정보 수정 - %s - Noah3k' % board_info.bName)

    def modify_post(self, mobile, board_name):
        try:
            current_uid = web.ctx.session.uid
        except:
            return desktop_render.error(lang='ko', error_message='NOT_LOGGED_IN')
        board_id = board._get_board_id_from_path(board_name)
        if board_id < 0:
            return desktop_render.error(lang='ko', error_message='INVALID_BOARD')
        # if !acl.get_permission(modify_board, user):
        board_info = board.get_board_info(board_id)
        if current_uid != board_info.uSerial:
            return desktop_render.error(lang='ko', error_message='NO_PERMISSION')
        comment, write_by_other = 0, 0 # XXX: DB 스키마를 BOOLEAN으로 바꿔야 함
        if web.input().commentable.strip() == 'yes':
            comment = 1
        if web.input().writable.strip() == 'yes':
            write_by_other = 1
        owner_uid = user._get_uid_from_username(web.input().owner)
        if owner_uid < 0:
            return desktop_render.error(lang='ko', error_message='NO_SUCH_USER_FOR_BOARD_ADMIN')

        board_info = dict(path = web.input().path, name = web.input().name,
                owner = owner_uid, board_type = web.input().type,
                can_comment = comment, can_write_by_other = write_by_other,
                description = web.input().description,
                cover = web.input().information)
        result = board.edit_board(board_id, board_info)
        if result[0] == False:
            return desktop_render.error(lang='ko', error_message = result[1])
        else:
            raise web.seeother('%s/+summary' % result[1])

    def delete_get(self, mobile, board_name):
        try:
            current_uid = web.ctx.session.uid
        except:
            return
        board_id = board._get_board_id_from_path(board_name)
        if board_id < 0:
            return desktop_render.error(lang='ko', error_message='INVALID_BOARD')
        ret = board.delete_board(current_uid, board_id)
        if ret[0] == True:
            raise web.seeother('%s' % (ret[1]))
        else:
            return desktop_render.error(lang='ko', error_message = ret[1])

