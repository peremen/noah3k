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

class main_actions:
    def GET(self, mobile, action):
        return self.caller(mobile, action, 'get')

    def POST(self, mobile, action):
        return self.caller(mobile, action, 'post')

    def caller(self, mobile, action, method):
        if mobile:
            mobile = True
        else:
            mobile = False
        try:
            return eval('self.%s_%s' % (action, method))(mobile)
        except AttributeError:
            raise web.notfound(render[mobile].error(lang='ko', error_message = 'INVALID_ACTION', help_context='error'))

    @util.error_catcher
    def join_get(self, mobile):
        if mobile:
            ref_path = '/m'
        else:
            ref_path = '/'
        return render[mobile].join(title = u"회원 가입 - Noah3K",
               lang="ko", board_desc=u"회원 가입",
               referer = web.ctx.env.get('HTTP_REFERER', ref_path))

    @util.error_catcher
    @util.confirmation_helper
    def join_post(self, mobile):
        data = web.input()
        username = data.id
        if user._get_uid_from_username(username) > 0:
            return render[mobile].error(lang='ko', error_message = 'ID_ALREADY_EXISTS', help_context='error')
        if data.password1 != data.password2:
            return render[mobile].error(lang='ko', error_message = 'PASSWORD_DO_NOT_MATCH', help_context='error')
        if len(data.password1) < 6:
            return render[mobile].error(lang='ko', error_message = 'PASSWORD_TOO_SHORT', help_context='error')
        nick = data.nick
        email = data.email
        password = data.password1
        ret = user.join(locals())
        if not ret[0]:
            return render[mobile].error(lang='ko', error_message = ret[1], help_context='error')
        uid = user._get_uid_from_username(username)
        web.ctx.session.uid = uid
        web.ctx.session.username = username
        user.update_last_login(uid, web.ctx.ip)
        if mobile:
            raise web.seeother('/m')
        else:
            raise web.seeother('/')

    @util.error_catcher
    def login_get(self, mobile):
        if mobile:
            referer = web.ctx.env.get('HTTP_REFERER', '/m')
        else:
            referer = web.ctx.env.get('HTTP_REFERER', '/')
        return render[mobile].login(title = u"로그인 - Noah3K", board_desc=u"로그인",
                lang="ko", referer = referer)

    @util.error_catcher
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
            else:
                # 로그인 실패
                err = login[1]
        if not login[0]:
            return render[mobile].login(title = u"로그인 - Noah3K", board_desc=u"로그인",
                    lang="ko", error = err, referer = referer)
        else:
            raise web.seeother(web.input().url)
            # 이전 페이지로 '묻지 않고' 되돌림

    @util.error_catcher
    def logout_get(self, mobile):
        web.ctx.session.uid = 0
        web.ctx.session.kill()
        if mobile:
            referer = web.ctx.env.get('HTTP_REFERER', '/m')
        else:
            referer = web.ctx.env.get('HTTP_REFERER', '/')
        raise web.seeother(referer)

    @util.error_catcher
    def credits_get(self, mobile):
        return render[mobile].credits(title = u"개발자 정보 - Noah3K",
               lang="ko", board_desc=u"개발자 정보", )

