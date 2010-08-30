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

class personal_page:
    @util.session_helper
    def GET(self, mobile, username, current_uid = -1):
        if mobile:
            mobile = True
        else:
            mobile = False
        user_id = user._get_uid_from_username(username)
        if user_id < 0:
            raise web.notfound(render[mobile].error(lang='ko', error_message = 'INVALID_USER'))
        f = [{'type':'rss', 'path':'/+u/%s/+favorite_rss' % username, 'name':u'즐겨찾기 피드 (RSS)'},
             {'type':'atom', 'path':'/+u/%s/+favorite_atom' % username, 'name':u'즐겨찾기 피드 (Atom)'},]
        return render[mobile].myinfo(user = user.get_user(user_id)[1],
                username = username, user_id = user_id,
                lang='ko', title = u'내 정보', board_desc = u'내 정보',
                feeds = f)

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
            raise web.notfound(render[mobile].error(lang='ko', error_message = 'INVALID_USER'))
        try:
            return eval('self.%s_%s' % (action, method))(mobile, username, user_id)
        except AttributeError:
            raise web.notfound(render[mobile].error(lang='ko', error_message = 'INVALID_ACTION'))

    def favorite_rss_get(self, mobile, username, user_id):
        articles = user.get_favorite_board_feed(user_id, config.favorite_feed_size)
        date = datetime.today()
        return desktop_render.rss(today = date,
                articles = articles, board_path="+u/%s/+favorite_rss" % username,
                board_desc = u'%s의 즐겨찾는 보드 피드' % username,
                link_address = 'http://noah.kaist.ac.kr/+u/%s' % username)

    def favorite_atom_get(self, mobile, username, user_id):
        articles = user.get_favorite_board_feed(user_id, config.favorite_feed_size)
        date = datetime.today()
        return desktop_render.atom(today = date,
                articles = articles, board_path="+u/%s/+favorite_atom" % username,
                board_desc = u'%s의 즐겨찾는 보드 피드' % username,
                self_address = 'http://noah.kaist.ac.kr/+u/%s/+favorite_atom' % username,
                href_address = 'http://noah.kaist.ac.kr/+u/%s' % username)

    @util.session_helper
    def modify_get(self, mobile, username, user_id, current_uid = -1):
        if user_id != current_uid:
            return render[mobile].error(lang='ko', error_message='MODIFYING_OTHERS_INFORMATION')
        referer = posixpath.join('/', '+u', username)
        if mobile:
            referer = posixpath.join('/m', referer)
        return render[mobile].myinfo_edit(user = user.get_user(user_id)[1],
                username = username, user_id = user_id,
                lang='ko', title = u'내 정보 수정',
                board_desc = u'내 정보 수정',
                referer = web.ctx.env.get('HTTP_REFERER', referer))

    @util.confirmation_helper
    @util.session_helper
    def modify_post(self, mobile, username, user_id, current_uid = -1):
        data = web.input()
        if not user.verify_password(user_id, data.oldpass):
            return render[mobile].error(lang='ko', error_message='INVALID_PASSWORD')
        if data.newpass1 != data.newpass2:
            return render[mobile].error(lang='ko', error_message = 'PASSWORD_DO_NOT_MATCH')
        if len(data.newpass1) > 0 and len(data.newpass1) < 6:
            return render[mobile].error(lang='ko', error_message = 'PASSWORD_TOO_SHORT')
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

    @util.session_helper
    def leave_get(self, mobile, username, user_id, current_uid = -1):
        if user_id != current_uid:
            return render[mobile].error(lang='ko', error_message='MODIFYING_OTHERS_INFORMATION')
        default_referer = posixpath.join('/', '+u', username)
        return render[mobile].leave(lang='ko', board_desc = u'회원 탈퇴',
                title=u'회원 탈퇴', username = username,
                referer = web.ctx.env.get('HTTP_REFERER', default_referer),)

    @util.confirmation_helper
    @util.session_helper
    def leave_post(self, mobile, username, user_id, current_uid = -1):
        password = web.input().password
        if not user.verify_password(user_id, password):
            return render[mobile].error(lang='ko', error_message='WRONG_PASSWORD')

        result = user.delete_user(user_id)
        if not result[0]:
            return render[mobile].error(lang='ko', error_message = result[1])
        web.ctx.session.uid = 0
        web.ctx.session.kill()
        if mobile:
            raise web.seeother('/m')
        else:
            raise web.seeother('/')
