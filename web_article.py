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

class article_actions:
    def GET(self, mobile, board_name, action, article_id):
        return self.caller(mobile, board_name, action, article_id, 'get')

    def POST(self, mobile, board_name, action, article_id):
        return self.caller(mobile, board_name, action, article_id, 'post')

    def caller(self, mobile, board_name, action, article_id, method):
        board_id = board._get_board_id_from_path(board_name)
        if board_id < 0:
            raise web.notfound(desktop_render.error(lang='ko', error_message = 'INVALID_BOARD'))
        try:
            return eval('self.%s_%s' % (action, method))(mobile, board_name, int(article_id))
        except:
            raise web.notfound(desktop_render.error(lang='ko', error_message = 'INVALID_ACTION'))

    def read_get(self, mobile, board_name, article_id):
        try:
            board_id = board._get_board_id_from_path(board_name)
            if board_id < 0:
                return
            board_info = board.get_board_info(board_id)
            board_path = board_info.bName[1:]
            board_desc = board_info.bDescription
            a = article.get_article(board_id, article_id)
            comment = article.get_comment(article_id)

            prev_id = -1
            next_id = -1

            if not a:
                return desktop_render.error(lang="ko", error_message = u"글 없음" )

            if a.aIndex > 1:
                prev_id = article.get_article_id_by_index(board_id, a.aIndex - 1)
            if a.aIndex < article._get_article_count(board_id):
                next_id = article.get_article_id_by_index(board_id, a.aIndex + 1)

            if not mobile:
                return desktop_render.read_article(article = a,
                    title = u"%s - %s - Noah3K" % (a.aIndex, a.aTitle),
                    board_path = board_path, board_desc = board_desc,
                    comments = comment, lang="ko", 
                    prev_id = prev_id, next_id = next_id, feed = True)
            else:
                return mobile_render.read_article()
        except Exception as e:
            print e

    def reply_get(self, mobile, board_name, article_id):
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
            return desktop_render.editor(title = u"답글 쓰기 - /%s - Noah3K" % board_name,
                    action='reply/%s' % article_id, action_name = u"답글 쓰기",
                    board_path = board_path, board_desc = board_desc,
                    lang="ko", )

    def reply_post(self, mobile, board_name, article_id):
        try:
            current_uid = web.ctx.session.uid
        except:
            return
        pass
        reply = dict(title = web.input().title, body = web.input().content)
        board_id = board._get_board_id_from_path(board_name)
        board_info = board.get_board_info(board_id)
        board_path = board_info.bName[1:]
        if board_id < 0:
            return
        ret = article.reply_article(current_uid, board_id, article_id, reply)
        if ret[0] == True:
            raise web.seeother('/%s/+read/%s' % (board_path, ret[1]))
        else:
            return desktop_render.error(lang='ko', error_message = ret[1])

    def modify_get(self, mobile, board_name, article_id):
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
        article_ = article.get_article(board_id, article_id)
        if not mobile:
            return desktop_render.editor(title = u"글 수정하기 - /%s - Noah3K" % board_name,
                    action='modify/%s' % article_id, action_name = u"글 수정하기",
                    board_path = board_path, board_desc = board_desc,
                    article_title = article_.aTitle, body = article_.aContent,
                    lang="ko", )

    def modify_post(self, mobile, board_name, article_id):
        try:
            current_uid = web.ctx.session.uid
        except:
            return
        article = dict(title = web.input().title, body = web.input().content)
        board_id = board._get_board_id_from_path(board_name)
        board_info = board.get_board_info(board_id)
        board_path = board_info.bName[1:]
        if board_id < 0:
            return
        ret = article.modify_article(current_uid, board_id, article_id, article)
        if ret[0] == True:
            raise web.seeother('/%s/+read/%s' % (board_path, ret[1]))
        else:
            return desktop_render.error(lang='ko', error_message = ret[1])

    def delete_get(self, mobile, board_name, article_id):
        try:
            current_uid = web.ctx.session.uid
        except:
            return
        ret = article.delete_article(current_uid, article_id)
        if ret[0] == True:
            raise web.seeother('/%s' % (board_name))
        else:
            return desktop_render.error(lang='ko', error_message = ret[1])

    def comment_post(self, mobile, board_name, article_id):
        try:
            current_uid = web.ctx.session.uid
        except:
            return
        comment = web.input().comment
        board_id = board._get_board_id_from_path(board_name)
        board_info = board.get_board_info(board_id)
        board_path = board_info.bName[1:]
        if board_id < 0:
            return
        ret = article.write_comment(current_uid, board_id, article_id, comment)
        if ret[0] == True:
            raise web.seeother('/%s/+read/%s' % (board_name, article_id))
        else:
            return desktop_render.error(lang='ko', error_message = ret[1])

    def comment_delete_get(self, mobile, board_name, comment_id):
        try:
            current_uid = web.ctx.session.uid
        except:
            return
        ret = article.delete_comment(current_uid, comment_id)
        if ret[0] == True:
            raise web.seeother('/%s/+read/%s' % (board_name, ret[1]))
        else:
            return desktop_render.error(lang='ko', error_message = ret[1])

