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

class personal_page:
    @util.session_helper
    def GET(self, mobile, username, current_uid = -1):
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

    @util.session_helper
    def modify_get(self, mobile, username, user_id, current_uid = -1):
        if user_id != current_uid:
            return desktop_render.error(lang='ko', error_message='MODIFYING_OTHERS_INFORMATION')
        return desktop_render.myinfo_edit(user = user.get_user(user_id)[1],
                username = username, user_id = user_id,
                lang='ko', title = u'내 정보 수정',
                board_desc = u'내 정보 수정',
                referer = os.path.join('/', '+u', username))

    @util.confirmation_helper
    @util.session_helper
    def modify_post(self, mobile, username, user_id, current_uid = -1):
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

    @util.session_helper
    def leave_get(self, mobile, username, user_id, current_uid = -1):
        if user_id != current_uid:
            return desktop_render.error(lang='ko', error_message='MODIFYING_OTHERS_INFORMATION')
        default_referer = os.path.join('/', '+u', username)
        return desktop_render.leave(lang='ko', board_desc = u'회원 탈퇴',
                title=u'회원 탈퇴', username = username,
                referer = web.ctx.env.get('HTTP_REFERER', default_referer),)

    @util.confirmation_helper
    @util.session_helper
    def leave_post(self, mobile, username, user_id, current_uid = -1):
        password = web.input().password
        if not user.verify_password(user_id, password):
            return desktop_render.error(lang='ko', error_message='WRONG_PASSWORD')

        result = user.delete_user(user_id)
        if not result[0]:
            return desktop_render.error(lang='ko', error_message = result[1])
        web.ctx.session.uid = 0
        web.ctx.session.kill()
        raise web.seeother('/')
