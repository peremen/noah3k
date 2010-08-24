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

class personal_page:
    def session_helper(self, mobile):
        try:
            current_uid = web.ctx.session.uid
        except:
            raise web.unauthorized(desktop_render.error(lang="ko", error_message = u"NOT_LOGGED_IN"))
        if current_uid < 1:
            raise web.internalerror(desktop_render.error(lang="ko", error_message = u"INVALID_UID"))
        return current_uid

    def GET(self, mobile, username):
        user_id = self.session_helper(mobile)
        user_id = user._get_uid_from_username(username)
        if user_id < 0:
            raise web.notfound(desktop_render.error(lang='ko', error_message = 'INVALID_USER'))
        return desktop_render.myinfo(user = user.get_user(user_id)[1],
                username = username, user_id = user_id,
                lang='ko', title = u'내 정보',
                board_desc = u'내 정보')

class personal_actions:
    def GET(self, mobile, username, action):
        return self.caller(mobile, username, action, 'get')

    def POST(self, mobile, username, action):
        return self.caller(mobile, username, action, 'post')

    def caller(self, mobile, username, action, method):
        user_id = user._get_uid_from_username(username)
        if user_id < 0:
            raise web.notfound(desktop_render.error(lang='ko', error_message = 'INVALID_USER'))
        try:
            return eval('self.%s_%s' % (action, method))(mobile, username, user_id)
        except AttributeError:
            raise web.notfound(desktop_render.error(lang='ko', error_message = 'INVALID_ACTION'))

    def session_helper(self, mobile):
        try:
            current_uid = web.ctx.session.uid
        except:
            raise web.unauthorized(desktop_render.error(lang="ko", error_message = u"NOT_LOGGED_IN"))
        if current_uid < 1:
            raise web.internalerror(desktop_render.error(lang="ko", error_message = u"INVALID_UID"))
        return current_uid

    def modify_get(self, mobile, username, user_id):
        self.session_helper(mobile)
        return desktop_render.myinfo_edit(user = user.get_user(user_id)[1],
                username = username, user_id = user_id,
                lang='ko', title = u'내 정보 수정',
                board_desc = u'내 정보 수정')

    def modify_post(self, mobile, username, user_id):
        self.session_helper(mobile)
        data = web.input()
        if not user.verify_password(user_id, data.oldpass):
            return desktop_render.error(lang='ko',
                    error_message='INVALID_PASSWORD')
        if data.newpass1 != data.newpass2:
            return desktop_render.error(lang='ko',
                    error_message = 'PASSWORD_DO_NOT_MATCH')
        if len(data.newpass1) > 0 and len(data.newpass1) < 6:
            return desktop_render.error(lang='ko',
                    error_message = 'PASSWORD_TOO_SHORT')
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
        raise web.seeother('/+u/%s' % username)
