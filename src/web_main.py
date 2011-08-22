#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import web
import config, board, user, article, mail
from datetime import datetime
from cgi import parse_qs
import posixpath
import util
from config import render
import i18n
_ = i18n.custom_gettext
from web_board import board_actions
import urllib, urllib2

class main_actions:
    def GET(self, theme, action):
        return self.caller(theme, action, 'get')

    def POST(self, theme, action):
        return self.caller(theme, action, 'post')

    @util.theme
    def caller(self, action, method):
        try:
            return eval('self.%s_%s' % (action, method))()
        except AttributeError:
            raise web.notfound(util.render().error(error_message = _('INVALID_ACTION'), help_context='error'))

    @util.error_catcher
    def join_get(self):
        ref_path = util.link('/')
        return util.render().join(title = _('Join'),
               lang="ko", board_desc=_('Join'),
               referer = web.ctx.env.get('HTTP_REFERER', ref_path))

    @util.error_catcher
    @util.confirmation_helper
    def join_post(self):
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
                return util.render().error(error_message = _('INCORRECT_CAPTCHA'), help_context='error')
            else:
                return util.render().error(error_message = _('CAPTCHA_ERROR'), help_context='error')
        username = data.id.strip()
        if username == '':
            return util.render().error(error_message = _('NO_USERNAME_SPECIFIED'), help_context='error')
        if user._get_uid_from_username(username) > 0:
            return util.render().error(error_message = _('ID_ALREADY_EXISTS'), help_context='error')
        if data.password1 != data.password2:
            return util.render().error(error_message = _('PASSWORD_DO_NOT_MATCH'), help_context='error')
        if len(data.password1) < 6:
            return util.render().error(error_message = _('PASSWORD_TOO_SHORT'), help_context='error')
        nick = data.nick
        email = data.email
        password = data.password1
        ret = user.join(locals())
        if not ret[0]:
            return util.render().error(error_message = ret[1], help_context='error')

        self.session_set(username)
        user.update_last_login(web.ctx.session.uid, web.ctx.ip)
        raise web.seeother(util.link('/'))

    @util.error_catcher
    def login_get(self):
        if web.config.theme == 'm':
            referer = web.ctx.env.get('HTTP_REFERER', '/m/+u/+new_article')
            if referer.endswith('/m') or referer.endswith('/m/'):
                referer = '/m/+u/+new_article'
        else:
            referer = web.ctx.env.get('HTTP_REFERER', util.link('/'))

        try:
            if web.ctx.session.uid is not 0:
                web.seeother(referer)
        except AttributeError:
            pass

        return util.render().login(title = _('Login'), board_desc=_('Login'),
                lang="ko", referer = referer)

    @util.error_catcher
    def login_xdomain_get(self):
        qs = web.ctx.query
        if len(qs) > 0:
            qs = qs[1:]
            qs = parse_qs(qs)

        if type(qs) != dict:
            return util.render().login(title = _('Login'), board_desc=_('Login'),
                lang="ko", error = _('INVALID_PASSWORD'), referer = util.link('/'))

        referer = util.link('/')
        if qs.has_key('referer'):
            referer = qs['referer'][0]
        password_hash = ''
        if qs.has_key('password_hash'):
            password_hash = qs['password_hash'][0]
        persistent = False
        if qs.has_key('persistent'):
            persistent = (int(qs['persistent'][0]) == 1)
        username = ''
        if qs.has_key('username'):
            username = qs['username'][0]

        login = user.login(username, password_hash, True)
        if not login[0]:
            err = login[1]
            return util.render().login(title = _('Login'), board_desc=_('Login'),
                lang="ko", error = err, referer = referer)

        u = self.session_set(username)
        if persistent:
            web.ctx.session.persistent = True
        else:
            web.ctx.session.persistent = False
        user.update_last_login(u.uSerial, web.ctx.ip)
        raise web.seeother(referer)

    @util.error_catcher
    def login_post(self):
        user_input = web.input()
        username, password = user_input.username.strip(), user_input.password.strip()
        referer = user_input.url.strip()
        if referer == '' or referer == 'None':
            referer = web.ctx.env.get('HTTP_REFERER', 'http://noah.kaist.ac.kr' + util.link('/'))
        if referer.endswith('/+login'):
            referer = referer[:-6]
        err = ''
        valid = True
        login = (False, _('UNDEFINED'))
        autologin = user_input.has_key('autologin')
        username, password = username.strip(), password.strip()
        if username == '' or password == '':
            err = _('No user ID or password specified.')
            valid = False

        if not valid:
            return util.render().login(title = _('Login'), board_desc=_('Login'),
                    lang="ko", error = err, referer = referer)

        login = user.login(username, password)
        if login[0]:
            # 로그인 성공. +login_xdomain에서는 세션 설정 후 referer로 돌아감.
            xdomain_qs = urllib.urlencode({'referer':referer,
                'username': username,
                'persistent': 1 if autologin else 0,
                'password_hash': user._generate_noah3k_password(password),
                })
            if referer.startswith('https'):
                pos = referer.find('/', len('https')+3)
                if pos > 0:
                    host = referer[:pos]
                else:
                    host = 'http://noah.haje.org'
            elif referer.startswith('http'):
                pos = referer.find('/', len('http')+3)
                if pos > 0:
                    host = referer[:pos]
                else:
                    host = 'http://noah.kaist.ac.kr'
            else:
                host = 'http://noah.kaist.ac.kr'
            raise web.seeother('%s/+login_xdomain?%s' % (host, xdomain_qs))
        else:
            # 로그인 실패
            err = login[1]
            return util.render().login(title = _('Login'), board_desc=_('Login'),
                lang="ko", error = err, referer = referer)

    @util.error_catcher
    def logout_get(self):
        web.ctx.session.uid = 0
        web.ctx.session.kill()
        referer = web.ctx.env.get('HTTP_REFERER', util.link('/'))
        raise web.seeother(referer)

    @util.error_catcher
    def lost_login_get(self):
        return util.render().lost_login(title=_('Lost Login?'), lang='ko',
                board_desc = _('Lost Login?'))

    @util.error_catcher
    def lost_login_post(self):
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
                return util.render().error(error_message = _('INCORRECT_CAPTCHA'), help_context='error')
            else:
                return util.render().error(error_message = _('CAPTCHA_ERROR'), help_context='error')
        found_users = user.get_user_from_email(data.email)
        if not found_users:
            return util.render().error(error_message = _('NO_SUCH_MAIL_ADDRESS'), help_context='error')
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
        return util.render().error(error_message = _('Message Sent. Please follow instructions on the message.'),
                error_class = _('Information'))
         
    @util.error_catcher
    def recover_password_get(self):
        if web.ctx.query == '':
            qs = dict()
        else:
            # XXX: http://bugs.python.org/issue8136
            qs = parse_qs(urllib.unquote(web.ctx.query[1:]).encode('latin-1').decode('utf-8'))

        if not (qs.has_key('id') and qs.has_key('key')):
            return util.render().error(error_message = _('INVALID_LINK'),
                    help_context = 'error')
        user_id = qs['id'][0]
        key = qs['key'][0]
        uid = user._get_uid_from_username(user_id)
        if uid < 0:
            return util.render().error(error_message = _('INVALID_USERNAME'),
                    help_context = 'error')
        if user.get_password_salt(uid) != key:
            return util.render().error(error_message = _('INVALID_PASSWORD_KEY'),
                    help_context = 'error')

        self.session_set(user_id)
        web.ctx.session.persistent = False
        user.update_last_login(uid, web.ctx.ip)
        new_pw = user.generate_random_password()
        user.update_password(uid, new_pw)
        return util.render().error(error_message = _('Your temporary password is "%s"(case-sensitive). Change password now.') % new_pw,
                error_class = _('Information'))

    @util.error_catcher
    def credits_get(self):
        return util.render().credits(title = _('Credits'),
               lang="ko", board_desc=_('Credits'), )

    @util.error_catcher
    def all_get(self):
        qs = web.ctx.query
        if len(qs) > 0:
            qs = qs[1:]
            qs = parse_qs(qs)

        t = (article._get_all_article_count() + config.page_size -1) / config.page_size
        if qs:
            page = int(qs['page'][0])
        else:
            page = 1

        all_article = article.get_all_articles(config.page_size, page)
        return util.render().board_aggregated(lang="ko",
            title = _('All Posts'),
            board_desc = _('All Posts'),
            articles=all_article,
            total_page = t, page = page,
            action = '/+all',
            help_context = 'board')

    def session_set(self, username):
        u = user.get_user(user._get_uid_from_username(username))[1];
        web.ctx.session.uid = u.uSerial
        web.ctx.session.username = u.uId
        web.ctx.session.usernick = u.uNick
        web.ctx.session.lang = u.language
        return u

