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
import i18n
_ = i18n.custom_gettext

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
            raise web.notfound(render[mobile].error(error_message = _('INVALID_ACTION'), help_context='error'))

    @util.error_catcher
    def join_get(self, mobile):
        if mobile:
            ref_path = '/m'
        else:
            ref_path = '/'
        return render[mobile].join(title = _('Join - %s') % config.branding,
               lang="ko", board_desc=_('Join'),
               referer = web.ctx.env.get('HTTP_REFERER', ref_path))

    @util.error_catcher
    @util.confirmation_helper
    def join_post(self, mobile):
        data = web.input()
        username = data.id
        if user._get_uid_from_username(username) > 0:
            return render[mobile].error(error_message = _('ID_ALREADY_EXISTS'), help_context='error')
        if data.password1 != data.password2:
            return render[mobile].error(error_message = _('PASSWORD_DO_NOT_MATCH'), help_context='error')
        if len(data.password1) < 6:
            return render[mobile].error(error_message = _('PASSWORD_TOO_SHORT'), help_context='error')
        nick = data.nick
        email = data.email
        password = data.password1
        ret = user.join(locals())
        if not ret[0]:
            return render[mobile].error(error_message = ret[1], help_context='error')
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
            referer = web.ctx.env.get('HTTP_REFERER', '/m/+u/+new_article')
        else:
            referer = web.ctx.env.get('HTTP_REFERER', '/')

        try:
            if web.ctx.session.uid is not 0:
                web.seeother(referer)
        except AttributeError:
            pass

        return render[mobile].login(title = _('Login - %s') % config.branding, board_desc=_('Login'),
                lang="ko", referer = referer)

    @util.error_catcher
    def login_post(self, mobile):
        username, password = '', ''
        err = ''
        valid = True
        login = (False, 'UNDEFINED')
        username, password = web.input().username, web.input().password
        referer = web.input().url
        username, password = username.strip(), password.strip()
        if username == '' or password == '':
            err = _('No user ID or password specified.')
            valid = False

        if valid:
            login = user.login(username, password)
            if login[0]:
                # 로그인 성공. referer로 돌아감.
                uid = user._get_uid_from_username(username)
                web.ctx.session.uid = uid
                web.ctx.session.username = username
                web.ctx.session.lang = login[1]
                user.update_last_login(uid, web.ctx.ip)
            else:
                # 로그인 실패
                err = login[1]
        if not login[0]:
            return render[mobile].login(title = _('Login - %s') % config.branding, board_desc=_('Login'),
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
        return render[mobile].credits(title = _('Credits - %s') % config.branding,
               lang="ko", board_desc=_('Credits'), )

