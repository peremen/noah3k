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
    def GET(self, mobile, username):
        return self.caller(mobile, username, 'get')

    def POST(self, mobile, username):
        return self.caller(mobile, username, 'post')

    def caller(self, mobile, username, method):
        user_id = user._get_uid_from_username(username)
        if user_id < 0:
            raise web.notfound(desktop_render.error(lang='ko', error_message = 'INVALID_USER'))
        try:
            return eval('self.%s_real' % (method))(mobile, username, user_id)
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
            return eval('self.%s_%s' % (action, method))(mobile, username, user_id, action)
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
