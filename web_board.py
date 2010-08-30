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
import util

desktop_render = render_mako(
    directories = [os.path.join(os.path.dirname(__file__), 'templates/desktop/').replace('\\','/'),],
    input_encoding = 'utf-8', output_encoding = 'utf-8',
)

mobile_render = render_mako(
    directories = [os.path.join(os.path.dirname(__file__), 'templates/mobile/').replace('\\','/'),],
    input_encoding = 'utf-8', output_encoding = 'utf-8',
)

render = {False: desktop_render, True: mobile_render}

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
        if mobile:
            mobile = True
        else:
            mobile = False
        if board_name == '^root':
            board_id = 1
        else:
            board_id = board._get_board_id_from_path(board_name)
        if board_id < 0:
            raise web.notfound(render[mobile].error(lang='ko', error_message = 'INVALID_BOARD'))
        try:
            return eval('self.%s_%s' % (action, method))(mobile, board_name, board_id)
        except AttributeError:
            raise web.notfound(render[mobile].error(lang='ko', error_message = 'INVALID_ACTION'))

    @util.session_helper
    def write_get(self, mobile, board_name, board_id, current_uid = -1):
        board_info = board.get_board_info(board_id)
        board_desc = board_info.bDescription
        return render[mobile].editor(title = u"글 쓰기 - %s - Noah3K" % board_name,
                action='write', action_name = u"글 쓰기",
                board_path = board_name, board_desc = board_desc, lang="ko", )

    @util.session_helper
    def write_post(self, mobile, board_name, board_id, current_uid = -1):
        a = dict(title = web.input().title, body = web.input().content)
        board_info = board.get_board_info(board_id)
        ret = article.write_article(current_uid, board_id, a)
        if ret[0] == True:
            if mobile:
                raise web.seeother('/m/%s/+read/%s' % (board_name, ret[1]))
            else:
                raise web.seeother('/%s/+read/%s' % (board_name, ret[1]))
        else:
            return render[mobile].error(lang='ko', error_message = ret[1])

    def rss_get(self, mobile, board_name, board_id):
        board_info = board.get_board_info(board_id)
        if board_info.bType == 0: # 디렉터리
            return

        date = datetime.today()
        page = article._get_total_page_count(board_id, config.feed_size)
        articles = article.get_article_list(board_id, confid.feed_size, page)
        web.header('Content-Type', 'application/rss+xml')
        return desktop_render.rss(board_path = board_name,
                board_desc = board_info.bDescription,
                articles=articles, today=date)

    def atom_get(self, mobile, board_name, board_id):
        board_info = board.get_board_info(board_id)
        if board_info.bType == 0: # 디렉터리
            return

        date = datetime.today()
        page = article._get_total_page_count(board_id, config.feed_size)
        articles = article.get_article_list(board_id, confid.feed_size, page)
        web.header('Content-Type', 'application/atom+xml')
        return desktop_render.atom(board_path = board_name,
                board_desc = board_info.bDescription,
                articles=articles, today=date)

    @util.session_helper
    def add_to_favorites_get(self, mobile, board_name, board_id, current_uid = -1):
        user.add_favorite_board(current_uid, board_id)
        if mobile:
            raise web.seeother('/m/%s' % board_name)
        else:
            raise web.seeother('/%s' % board_name)

    @util.session_helper
    def remove_from_favorites_get(self, mobile, board_name, board_id, current_uid = -1):
        user.remove_favorite_board(current_uid, board_id)
        if mobile:
            raise web.seeother('/%s' % board_name)
        else:
            raise web.seeother('/m/%s' % board_name)

    def summary_get(self, mobile, board_name, board_id):
        board_info = board.get_board_info(board_id)
        return render[mobile].board_summary(board_info = board_info,
                board_path = board_name,
                board_desc = board_info.bDescription, lang='ko',
                title = u'정보 - %s - Noah3k' % board_info.bName,)

    def subboard_list_get(self, mobile, board_name = '', board_id = 1):
        board_info = board.get_board_info(board_id)
        child_board = board.get_child(board_id)
        if board_name == "":
            board_name = u"초기 화면"
            board_path = ""
        else:
            board_path = board_name
            if board_name[0] != '/':
                board_name = '/%s' % (board_name)
        return render[mobile].view_subboard_list(lang="ko",
                title = u"%s - Noah3K" % board_name,
                board_path = board_path,
                board_desc = board_info.bDescription,
                child_boards = child_board)

    def cover_get(self, mobile, board_name, board_id):
        board_info = board.get_board_info(board_id)
        return desktop_render.cover(title = u'%s - Noah3K' % board_name,
                board_cover = board_info.bInformation)

    @util.session_helper
    def create_board_get(self, mobile, board_name, board_id, current_uid = -1):
        # if !acl.get_permission(modify_board, user):
        board_info = board.get_board_info(board_id)
        if current_uid != board_info.uSerial:
            return render[mobile].error(lang='ko', error_message = 'NO_PERMISSION')
        return render[mobile].board_editor(action='create_board', board_info = board_info,
                board_path = board_name, board_desc = board_info.bDescription, lang='ko',
                title = u'하위 게시판 만들기 - %s - Noah3k' % board_info.bName,
                referer = posixpath.join('/', board_name, '+summary'))

    @util.confirmation_helper
    @util.session_helper
    def create_board_post(self, mobile, board_name, board_id, current_uid = -1):
        # if !acl.get_permission(modify_board, user):
        board_info = board.get_board_info(board_id)
        if current_uid != board_info.uSerial:
            return render[mobile].error(lang='ko', error_message = 'NO_PERMISSION')
        user_data = web.input()
        comment, write_by_other = 0, 0 # XXX: DB 스키마를 BOOLEAN으로 바꿔야 함
        if user_data.commentable == 'yes':
            comment = 1
        if user_data.writable == 'yes':
            write_by_other = 1
        owner_uid = user._get_uid_from_username(user_data.owner)
        if owner_uid < 0:
            return render[mobile].error(lang='ko', error_message='NO_SUCH_USER_FOR_BOARD_ADMIN')
        if user_data.name.strip() == '':
            return desktop_render.error(lang='ko', error_message = 'NO_NAME_SPECIFIED')
        new_path = posixpath.join('/', board_name, user_data.name)
        if board._get_board_id_from_path(new_path) > 0:
            return render[mobile].error(lang='ko', error_message = 'BOARD_EXISTS')

        settings = dict(path=new_path, board_owner = owner_uid,
                cover = user_data.information,
                description = user_data.description,
                type = int(user_data.type),
                guest_write = write_by_other,
                can_comment = comment,
                current_uid = current_uid)
        ret = board.create_board(board_id, settings)
        if ret[0] == False:
            return render[mobile].error(lang='ko', error_message = ret[1])
        if mobile:
            raise web.seeother('/m%s' % (new_path))
        else:
            raise web.seeother('%s' % (new_path))

    @util.session_helper
    def modify_get(self, mobile, board_name, board_id, current_uid = -1):
        # if !acl.get_permission(modify_board, user):
        board_info = board.get_board_info(board_id)
        if current_uid != board_info.uSerial:
            return render[mobile].error(lang='ko', error_message='NO_PERMISSION')
        default_referer = posixpath.join('/', board_name, '+summary')
        if mobile:
            default_referer = posixpath.join('/m', default_referer)
        return render[mobile].board_editor(action='modify', board_info = board_info,
                board_path = board_name, board_desc = board_info.bDescription, lang='ko',
                title = u'정보 수정 - %s - Noah3k' % board_info.bName,
                referer = web.ctx.env.get('HTTP_REFERER', default_referer))

    @util.session_helper
    @util.confirmation_helper
    def modify_post(self, mobile, board_name, board_id, current_uid = -1):
        # if !acl.get_permission(modify_board, user):
        board_info = board.get_board_info(board_id)
        if current_uid != board_info.uSerial:
            return render[mobile].error(lang='ko', error_message='NO_PERMISSION')
        comment, write_by_other = 0, 0 # XXX: DB 스키마를 BOOLEAN으로 바꿔야 함
        if web.input().commentable.strip() == 'yes':
            comment = 1
        if web.input().writable.strip() == 'yes':
            write_by_other = 1
        owner_uid = user._get_uid_from_username(web.input().owner)
        if owner_uid < 0:
            return render[mobile].error(lang='ko', error_message='NO_SUCH_USER_FOR_BOARD_ADMIN')

        board_info = dict(path = web.input().path, name = web.input().name,
                owner = owner_uid, board_type = web.input().type,
                can_comment = comment, can_write_by_other = write_by_other,
                description = web.input().description,
                cover = web.input().information)
        result = board.edit_board(board_id, board_info)
        if result[0] == False:
            return render[mobile].error(lang='ko', error_message = result[1])
        else:
            if mobile:
                raise web.seeother('/m%s/+summary' % result[1])
            else:
                raise web.seeother('%s/+summary' % result[1])

    @util.session_helper
    def delete_get(self, mobile, board_name, board_id, current_uid = -1):
        default_referer = posixpath.join('/', board_name, '+summary')
        if mobile:
            default_referer = posixpath.join('/m', default_referer)
        action = posixpath.join('/', board_name, '+delete')
        if mobile:
            action = posixpath.join('/m', action)
        return render[mobile].question(lang='ko', question=u'이 게시판을 삭제하시겠습니까?',
                board_path = board_name, board_desc = u'확인', title=u'확인',
                action=action,
                referer=web.ctx.env.get('HTTP_REFERER', default_referer))

    @util.session_helper
    @util.confirmation_helper
    def delete_post(self, mobile, board_name, board_id, current_uid = -1):
        ret = board.delete_board(current_uid, board_id)
        if ret[0] == True:
            if mobile:
                raise web.seeother('/m%s' % (ret[1]))
            else:
                raise web.seeother('%s' % (ret[1]))
        else:
            return render[mobile].error(lang='ko', error_message = ret[1])

