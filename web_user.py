#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import web
import config
import board, user, article
from cgi import parse_qs
from datetime import datetime
import posixpath
import util
from config import render

class personal_page:
    @util.error_catcher
    @util.session_helper
    def GET(self, mobile, username, current_uid = -1):
        if mobile:
            mobile = True
        else:
            mobile = False
        user_id = user._get_uid_from_username(username)
        if user_id < 0:
            raise web.notfound(render[mobile].error(error_message = 'INVALID_USER', help_context='error'))
        f = [{'type':'rss', 'path':'/+u/%s/+favorite_rss' % username, 'name':u'즐겨찾기 피드 (RSS)'},
             {'type':'atom', 'path':'/+u/%s/+favorite_atom' % username, 'name':u'즐겨찾기 피드 (Atom)'},]
        return render[mobile].myinfo(user = user.get_user(user_id)[1],
                username = username, user_id = user_id,
                title = u'내 정보', board_desc = u'내 정보',
                feeds = f, help_context='myinfo')

class personal_actions:
    def GET(self, mobile, username, action):
        return self.caller(mobile, username, action, 'get')

    def POST(self, mobile, username, action):
        return self.caller(mobile, username, action, 'post')

    def caller(self, mobile, username, action, method):
        if mobile:
            mobile = True
        else:
            mobile = False
        user_id = user._get_uid_from_username(username)
        if user_id < 0:
            raise web.notfound(render[mobile].error(error_message = 'INVALID_USER', help_context='error'))
        try:
            return eval('self.%s_%s' % (action, method))(mobile, username, user_id)
        except AttributeError:
            raise web.notfound(render[mobile].error(error_message = 'INVALID_ACTION', help_context='error'))

    @util.error_catcher
    def favorite_rss_get(self, mobile, username, user_id):
        articles = user.get_favorite_board_feed(user_id, config.favorite_feed_size)
        date = datetime.today()
        return desktop_render.rss(today = date,
                articles = articles, board_path="+u/%s/+favorite_rss" % username,
                board_desc = u'%s의 즐겨찾는 보드 피드' % username,
                link_address = 'http://noah.kaist.ac.kr/+u/%s' % username)

    @util.error_catcher
    def favorite_atom_get(self, mobile, username, user_id):
        articles = user.get_favorite_board_feed(user_id, config.favorite_feed_size)
        date = datetime.today()
        return desktop_render.atom(today = date,
                articles = articles, board_path="+u/%s/+favorite_atom" % username,
                board_desc = u'%s의 즐겨찾는 보드 피드' % username,
                self_address = 'http://noah.kaist.ac.kr/+u/%s/+favorite_atom' % username,
                href_address = 'http://noah.kaist.ac.kr/+u/%s' % username)

    @util.error_catcher
    @util.session_helper
    def modify_get(self, mobile, username, user_id, current_uid = -1):
        if user_id != current_uid:
            return render[mobile].error(error_message='MODIFYING_OTHERS_INFORMATION', help_context='error')
        referer = posixpath.join('/', '+u', username)
        if mobile:
            referer = posixpath.join('/m', referer)
        return render[mobile].myinfo_edit(user = user.get_user(user_id)[1],
                username = username, user_id = user_id,
                title = u'내 정보 수정',
                board_desc = u'내 정보 수정',
                referer = web.ctx.env.get('HTTP_REFERER', referer),
                help_context = 'myinfo')

    @util.error_catcher
    @util.confirmation_helper
    @util.session_helper
    def modify_post(self, mobile, username, user_id, current_uid = -1):
        data = web.input()
        if not user.verify_password(user_id, data.oldpass):
            return render[mobile].error(error_message='INVALID_PASSWORD', help_context='error')
        if data.newpass1 != data.newpass2:
            return render[mobile].error(error_message = 'PASSWORD_DO_NOT_MATCH', help_context='error')
        if len(data.newpass1) > 0 and len(data.newpass1) < 6:
            return render[mobile].error(error_message = 'PASSWORD_TOO_SHORT', help_context='error')
        if len(data.newpass1) == 0:
            password = data.oldpass
        else:
            password = data.newpass1
        nick = data.nick
        email = data.email
        homepage = data.homepage
        sig = data.sig
        introduction = data.introduction
        ret = user.modify_user(user_id, locals())
        if mobile:
            raise web.seeother('/m/+u/%s' % username)
        else:
            raise web.seeother('/+u/%s' % username)

    @util.error_catcher
    @util.session_helper
    def leave_get(self, mobile, username, user_id, current_uid = -1):
        if user_id != current_uid:
            return render[mobile].error(error_message='MODIFYING_OTHERS_INFORMATION', help_context='error')
        default_referer = posixpath.join('/', '+u', username)
        return render[mobile].leave(board_desc = u'회원 탈퇴',
                title=u'회원 탈퇴', username = username,
                referer = web.ctx.env.get('HTTP_REFERER', default_referer),)

    @util.error_catcher
    @util.confirmation_helper
    @util.session_helper
    def leave_post(self, mobile, username, user_id, current_uid = -1):
        password = web.input().password
        if not user.verify_password(user_id, password):
            return render[mobile].error(error_message='WRONG_PASSWORD', help_context='error')

        result = user.delete_user(user_id)
        if not result[0]:
            return render[mobile].error(error_message = result[1], help_context='error')
        web.ctx.session.uid = 0
        web.ctx.session.kill()
        if mobile:
            raise web.seeother('/m')
        else:
            raise web.seeother('/')

    @util.error_catcher
    @util.session_helper
    def my_board_get(self, mobile, username, user_id, current_uid = -1):
        my_board = user.get_owned_board(user_id)
        return render[mobile].view_subboard_list(
            child_boards = my_board, board_path = '',
            title=u'내 게시판', board_desc = u'내 게시판',
            list_type = u'내 게시판')

    @util.error_catcher
    @util.session_helper
    def favorites_get(self, mobile, username, user_id, current_uid = -1):
        fav_board = []
        for b in user.get_favorite_board(user_id):
            fav_board.append(board.get_board_info(b.bSerial))
        return render[mobile].view_subboard_list(
            child_boards = fav_board, board_path = '',
            title=u'즐겨찾는 게시판', board_desc = u'즐겨찾는 게시판',
            list_type = u'즐겨찾는 게시판')
