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

class article_actions:
    def GET(self, mobile, board_name, action, article_id):
        return self.caller(mobile, board_name, action, article_id, 'get')

    def POST(self, mobile, board_name, action, article_id):
        return self.caller(mobile, board_name, action, article_id, 'post')

    def caller(self, mobile, board_name, action, article_id, method):
        if mobile:
            mobile = True
        else:
            mobile = False
        board_id = board._get_board_id_from_path(board_name)
        if board_id < 0:
            raise web.notfound(render[mobile].error(lang='ko', error_message = 'INVALID_BOARD'))
        try:
            return eval('self.%s_%s' % (action, method))(mobile, board_name, board_id, int(article_id))
        except AttributeError:
            raise web.notfound(render[mobile].error(lang='ko', error_message = 'INVALID_ACTION'))

    def read_get(self, mobile, board_name, board_id, article_id):
        board_info = board.get_board_info(board_id)
        board_desc = board_info.bDescription
        a = article.get_article(board_id, article_id)
        comment = article.get_comment(article_id)

        prev_id = -1
        next_id = -1

        if not a:
            raise web.notfound(render[mobile].error(lang="ko", error_message = u"NO_SUCH_ARTICLE"))
        if a.aIndex > 1:
            prev_id = article.get_article_id_by_index(board_id, a.aIndex - 1)
        if a.aIndex < article._get_article_count(board_id):
            next_id = article.get_article_id_by_index(board_id, a.aIndex + 1)
        page_no = article.get_page_by_article_id(board_id, article_id, config.page_size)

        return render[mobile].read_article(article = a,
            title = u"%s - %s - Noah3K" % (a.aIndex, a.aTitle),
            board_path = board_name, board_desc = board_desc,
            comments = comment, lang="ko", page_no = page_no,
            prev_id = prev_id, next_id = next_id, feed = True)

    @util.session_helper
    def reply_get(self, mobile, board_name, board_id, article_id, current_uid = -1):
        board_info = board.get_board_info(board_id)
        board_desc = board_info.bDescription
        article_ = article.get_article(board_id, article_id)
        quote_text = u'%s님의 글 "%s"에서:' % (user._get_username_from_uid(article_.uSerial), util.remove_bracket(article_.aTitle))
        body = '\n\n\n[quote=%s]%s\n[/quote]' % (quote_text, article_.aContent)
        return render[mobile].editor(title = u"답글 쓰기 - /%s - Noah3K" % board_name,
                action='reply/%s' % article_id, action_name = u"답글 쓰기",
                board_path = board_name, board_desc = board_desc,
                lang="ko", body = body, article_title = article_.aTitle)

    @util.session_helper
    def reply_post(self, mobile, board_name, board_id, article_id, current_uid = -1):
        reply = dict(title = web.input().title, body = web.input().content)
        board_info = board.get_board_info(board_id)
        ret = article.reply_article(current_uid, board_id, article_id, reply)
        if ret[0] == True:
            if mobile:
                raise web.seeother('/m/%s/+read/%s' % (board_name, ret[1]))
            else:
                raise web.seeother('/%s/+read/%s' % (board_name, ret[1]))
        else:
            return render[mobile].error(lang='ko', error_message = ret[1])

    @util.session_helper
    def modify_get(self, mobile, board_name, board_id, article_id, current_uid = -1):
        board_info = board.get_board_info(board_id)
        board_desc = board_info.bDescription
        article_ = article.get_article(board_id, article_id)
        return render[mobile].editor(title = u"글 수정하기 - /%s - Noah3K" % board_name,
                action='modify/%s' % article_id, action_name = u"글 수정하기",
                board_path = board_name, board_desc = board_desc,
                article_title = article_.aTitle, body = article_.aContent,
                lang="ko", )

    @util.session_helper
    def modify_post(self, mobile, board_name, board_id, article_id, current_uid = -1):
        a = dict(title = web.input().title, body = web.input().content)
        board_info = board.get_board_info(board_id)
        ret = article.modify_article(current_uid, board_id, article_id, a)
        if ret[0] == True:
            if mobile:
                raise web.seeother('/m/%s/+read/%s' % (board_name, ret[1]))
            else:
                raise web.seeother('/%s/+read/%s' % (board_name, ret[1]))
        else:
            return render[mobile].error(lang='ko', error_message = ret[1])

    @util.session_helper
    def delete_get(self, mobile, board_name, board_id, article_id, current_uid = -1):
        if mobile:
            default_referer = os.path.join('/m', board_name, '+read', str(article_id))
            action=os.path.join('/m', board_name, '+delete', str(article_id))
        else:
            default_referer = os.path.join('/', board_name, '+read', str(article_id))
            action=os.path.join('/', board_name, '+delete', str(article_id))
        return render[mobile].question(lang='ko', question=u'글을 삭제하시겠습니까?',
                board_path = board_name, board_desc = u'확인', title=u'확인',
                action = action,
                referer=web.ctx.env.get('HTTP_REFERER', default_referer))

    @util.confirmation_helper
    @util.session_helper
    def delete_post(self, mobile, board_name, board_id, article_id, current_uid = -1):
        ret = article.delete_article(current_uid, article_id)
        if ret[0] == True:
            if mobile:
                raise web.seeother('/m/%s' % (board_name))
            else:
                raise web.seeother('/%s' % (board_name))
        else:
            return render[mobile].error(lang='ko', error_message = ret[1])

    @util.session_helper
    def comment_post(self, mobile, board_name, board_id, article_id, current_uid = -1):
        comment = web.input().comment
        board_info = board.get_board_info(board_id)
        ret = article.write_comment(current_uid, board_id, article_id, comment)
        if ret[0] == True:
            if mobile:
                raise web.seeother('/m/%s/+read/%s' % (board_name, article_id))
            else:
                raise web.seeother('/%s/+read/%s' % (board_name, article_id))
        else:
            return render[mobile].error(lang='ko', error_message = ret[1])

    @util.session_helper
    def comment_delete_get(self, mobile, board_name, board_id, comment_id, current_uid = -1):
        ret = article.delete_comment(current_uid, comment_id)
        if ret[0] == True:
            if mobile:
                raise web.seeother('/m/%s/+read/%s' % (board_name, ret[1]))
            else:
                raise web.seeother('/%s/+read/%s' % (board_name, ret[1]))
        else:
            return render[mobile].error(lang='ko', error_message = ret[1])

