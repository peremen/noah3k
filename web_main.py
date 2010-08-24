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

class main_actions:
    def GET(self, mobile, action):
        return self.caller(mobile, action, 'get')

    def POST(self, mobile, action):
        return self.caller(mobile, action, 'post')

    def caller(self, mobile, action, method):
        try:
            return eval('self.%s_%s' % (action, method))(mobile)
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

    def join_get(self, mobile):
        if not mobile:
            return desktop_render.join(title = u"회원 가입 - Noah3K",
                   lang="ko", board_desc=u"회원 가입", )
        else:
            return mobile_render.join()

    def login_get(self, mobile):
        referer = web.ctx.env.get('HTTP_REFERER', '/')
        if not mobile:
            return desktop_render.login(title = u"로그인 - Noah3K", board_desc=u"로그인",
                    lang="ko", referer = referer)
        else:
            return mobile_render.login()

    def login_post(self, mobile):
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
                uid = user._get_uid_from_username(username)
                web.ctx.session.uid = uid
                web.ctx.session.username = username
                user.update_last_login(uid, web.ctx.ip)
                login = True
            else:
                # 로그인 실패
                err = login[1]
        if not login:
            return desktop_render.login(title = u"로그인 - Noah3K", board_desc=u"로그인",
                    lang="ko", error = err, referer = referer)
        else:
            raise web.seeother(web.input().url)
            # 이전 페이지로 '묻지 않고' 되돌림

    def logout_get(self, mobile):
        web.ctx.session.uid = 0
        web.ctx.session.kill()
        referer = web.ctx.env.get('HTTP_REFERER', '/')
        raise web.seeother(referer)

    def credits_get(self, mobile):
        if not mobile:
            return desktop_render.credits(title = u"개발자 정보 - Noah3K",
                   lang="ko", board_desc=u"개발자 정보", )
        else:
            return mobile_render.credits()

