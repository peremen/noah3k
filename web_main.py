#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import web
import config, board, user, article, mail
from datetime import datetime
from cgi import parse_qs
import posixpath
import util
from render import render
import i18n
_ = i18n.custom_gettext
from web_board import board_actions
import urllib, urllib2

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
        recaptcha_url = 'http://www.google.com/recaptcha/api/verify'
        recaptcha_data = dict(challenge = data.recaptcha_challenge_field,
                response = data.recaptcha_response_field,
                remoteip = web.ctx.ip,
                privatekey = config.recaptcha_private_key)
        req = urllib2.Request(recaptcha_url, urllib.urlencode(recaptcha_data))
        response = urllib2.urlopen(req)
        page = response.read().split('\n')
        if page[0] == 'false':
            if page[1].strip() == 'incorrect-captcha-sol':
                return render[theme].error(error_message = _('INCORRECT_CAPTCHA'), help_context='error')
            else:
                return render[theme].error(error_message = _('CAPTCHA_ERROR'), help_context='error')
        username = data.id.strip()
        if username == '':
            return render[theme].error(error_message = _('NO_USERNAME_SPECIFIED'), help_context='error')
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

        self.session_set(username)
        user.update_last_login(web.ctx.session.uid, web.ctx.ip)
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
        user_input = web.input()
        username, password = user_input.username.strip(), user_input.password.strip()
        referer = user_input.url.strip()
        if referer == '' or referer == 'None':
            if theme == 'default':
                referer = web.ctx.env.get('HTTP_REFERER', '/')
            else:
                referer = web.ctx.env.get('HTTP_REFERER', '/%s' % theme)
        if referer.endswith('login'):
            if theme == 'default':
                referer = '/'
            else:
                referer = '/%s' % theme
        err = ''
        valid = True
        login = (False, 'UNDEFINED')
        autologin = user_input.has_key('autologin')
        username, password = username.strip(), password.strip()
        if username == '' or password == '':
            err = _('No user ID or password specified.')
            valid = False

        if valid:
            login = user.login(username, password)
            if login[0]:
                # 로그인 성공. referer로 돌아감.
                u = self.session_set(username)
                if autologin:
                    web.ctx.session.persistent = True
                else:
                    web.ctx.session.persistent = False
                user.update_last_login(u.uSerial, web.ctx.ip)
            else:
                # 로그인 실패
                err = login[1]
        if not login[0]:
            return render[theme].login(title = _('Login'), board_desc=_('Login'),
                    lang="ko", error = err, referer = referer)
        else:
            raise web.seeother(referer)
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
    def lost_login_get(self, theme):
        return render[theme].lost_login(title=_('Lost Login?'), lang='ko',
                board_desc = _('Lost Login?'))

    @util.error_catcher
    def lost_login_post(self, theme):
        data = web.input()
        recaptcha_url = 'http://www.google.com/recaptcha/api/verify'
        recaptcha_data = dict(challenge = data.recaptcha_challenge_field,
                response = data.recaptcha_response_field,
                remoteip = web.ctx.ip,
                privatekey = config.recaptcha_private_key)
        req = urllib2.Request(recaptcha_url, urllib.urlencode(recaptcha_data))
        response = urllib2.urlopen(req)
        page = response.read().split('\n')
        if page[0] == 'false':
            if page[1].strip() == 'incorrect-captcha-sol':
                return render[theme].error(error_message = _('INCORRECT_CAPTCHA'), help_context='error')
            else:
                return render[theme].error(error_message = _('CAPTCHA_ERROR'), help_context='error')
        found_users = user.get_user_from_email(data.email)
        if not found_users:
            return render[theme].error(error_message = _('NO_SUCH_MAIL_ADDRESS'), help_context='error')
        salt_string = ''
        for u in found_users:
            salt = user.get_password_salt(u.uSerial)
            salt_string = salt_string + '* User %s: http://noah.kaist.ac.kr/+recover_password?id=%s&key=%s\n' % (u.uId, u.uId, salt)
        message_title = _('NOAH password recovery')
        message_body = _('''Dear NOAH user,

Some user on IP %s requested new password of your account(s). Following list contains your account(s). Click on the corresponding link for recovering password of account.

%s

If you did not requested password recovery, then please log in into your account. This link will not be vaild after logging into the account.''') % (web.ctx.ip, salt_string)
        mail.mail(data.email, message_title, message_body)
        return _('Message Sent. Please follow instructions on the message.')
         
    @util.error_catcher
    def recover_password_get(self, theme):
        if web.ctx.query == '':
            qs = dict()
        else:
            # XXX: http://bugs.python.org/issue8136
            qs = parse_qs(urllib.unquote(web.ctx.query[1:]).encode('latin-1').decode('utf-8'))

        if not (qs.has_key('id') and qs.has_key('key')):
            return render[theme].error(error_message = _('INVALID_LINK'),
                    help_context = 'error')
        user_id = qs['id'][0]
        key = qs['key'][0]
        uid = user._get_uid_from_username(user_id)
        if uid < 0:
            return render[theme].error(error_message = _('INVALID_USERNAME'),
                    help_context = 'error')
        if user.get_password_salt(uid) != key:
            return render[theme].error(error_message = _('INVALID_PASSWORD_KEY'),
                    help_context = 'error')

        self.session_set(user_id)
        web.ctx.session.persistent = False
        user.update_last_login(uid, web.ctx.ip)
        return render[theme].error(error_message = _('CHANGE_PASSWORD_NOW'),
                help_context = 'error')

    @util.error_catcher
    def credits_get(self, theme):
        return render[theme].credits(title = _('Credits'),
               lang="ko", board_desc=_('Credits'), )

    def session_set(self, username):
        u = user.get_user(user._get_uid_from_username(username))[1];
        web.ctx.session.uid = u.uSerial
        web.ctx.session.username = u.uId
        web.ctx.session.usernick = u.uNick
        web.ctx.session.lang = u.language
        return u
