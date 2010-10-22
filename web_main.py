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
from render import render
import i18n
_ = i18n.custom_gettext
from web_board import board_actions

class main_actions:
    def GET(self, theme, action):
        return self.caller(theme, action, 'get')

    def POST(self, theme, action):
        return self.caller(theme, action, 'post')

    def caller(self, theme, action, method):
        if theme and not render.has_key(theme):
            ba = board_actions()
            return ba.caller('default', theme, action, method)
        if not theme:
            theme = 'default'
        try:
            return eval('self.%s_%s' % (action, method))(theme)
        except AttributeError:
            raise web.notfound(render[theme].error(error_message = _('INVALID_ACTION'), help_context='error'))

    @util.error_catcher
    def join_get(self, theme):
        if theme == 'default':
            ref_path = '/'
        else:
            ref_path = '/%s' % theme
        return render[theme].join(title = _('Join'),
               lang="ko", board_desc=_('Join'),
               referer = web.ctx.env.get('HTTP_REFERER', ref_path))

    @util.error_catcher
    @util.confirmation_helper
    def join_post(self, theme):
        data = web.input()
        username = data.id
        if user._get_uid_from_username(username) > 0:
            return render[theme].error(error_message = _('ID_ALREADY_EXISTS'), help_context='error')
        if data.password1 != data.password2:
            return render[theme].error(error_message = _('PASSWORD_DO_NOT_MATCH'), help_context='error')
        if len(data.password1) < 6:
            return render[theme].error(error_message = _('PASSWORD_TOO_SHORT'), help_context='error')
        nick = data.nick
        email = data.email
        password = data.password1
        ret = user.join(locals())
        if not ret[0]:
            return render[theme].error(error_message = ret[1], help_context='error')
        uid = user._get_uid_from_username(username)
        web.ctx.session.uid = uid
        web.ctx.session.username = username
        user.update_last_login(uid, web.ctx.ip)
        if theme == 'default':
            raise web.seeother('/')
        else:
            raise web.seeother('/%s' % theme)

    @util.error_catcher
    def login_get(self, theme):
        if theme == 'm':
            referer = web.ctx.env.get('HTTP_REFERER', '/m/+u/+new_article')
            if referer.endswith('/m') or referer.endswith('/m/'):
                referer = '/m/+u/+new_article'
        elif theme == 'default':
            referer = web.ctx.env.get('HTTP_REFERER', '/')
        else:
            referer = web.ctx.env.get('HTTP_REFERER', '/%s' % theme)

        try:
            if web.ctx.session.uid is not 0:
                web.seeother(referer)
        except AttributeError:
            pass

        return render[theme].login(title = _('Login'), board_desc=_('Login'),
                lang="ko", referer = referer)

    @util.error_catcher
    def login_post(self, theme):
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
            return render[theme].login(title = _('Login'), board_desc=_('Login'),
                    lang="ko", error = err, referer = referer)
        else:
            raise web.seeother(web.input().url)
            # 이전 페이지로 '묻지 않고' 되돌림

    @util.error_catcher
    def logout_get(self, theme):
        web.ctx.session.uid = 0
        web.ctx.session.kill()
        if theme == 'default':
            referer = web.ctx.env.get('HTTP_REFERER', '/')
        else:
            referer = web.ctx.env.get('HTTP_REFERER', '/%s' % theme)
        raise web.seeother(referer)

    @util.error_catcher
    def credits_get(self, theme):
        return render[theme].credits(title = _('Credits'),
               lang="ko", board_desc=_('Credits'), )

