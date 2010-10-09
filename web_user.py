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
import pm

class personal_page:
    @util.error_catcher
    @util.session_helper
    def GET(self, mobile, username, current_uid = -1):
        if mobile:
            mobile = True
        else:
            mobile = False
        user_id = user._get_uid_from_username(username)
        if user_id < 0:
            raise web.notfound(render[mobile].error(error_message = _('INVALID_USER'), help_context='error'))
        f = [{'type':'rss', 'path':'/+u/%s/+favorite_rss' % username, 'name':u'즐겨찾기 피드 (RSS)'},
             {'type':'atom', 'path':'/+u/%s/+favorite_atom' % username, 'name':u'즐겨찾기 피드 (Atom)'},]
        return render[mobile].myinfo(user = user.get_user(user_id)[1],
                username = username, user_id = user_id,
                title = u'내 정보', board_desc = u'내 정보',
                feeds = f, help_context='myinfo')

class personal_actions:
    # TODO: 로그인 필요한 동작에서는 사용자 이름을 빼내는 방법 생각해 볼 것.
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
            raise web.notfound(render[mobile].error(error_message = _('INVALID_USER'), help_context='error'))
        try:
            return eval('self.%s_%s' % (action, method))(mobile, username, user_id)
        except AttributeError:
            raise web.notfound(render[mobile].error(error_message = _('INVALID_ACTION'), help_context='error'))

    @util.error_catcher
    def favorite_rss_get(self, mobile, username, user_id):
        articles = user.get_favorite_board_feed(user_id, config.favorite_feed_size)
        date = datetime.today()
        web.header('Content-Type', 'application/rss+xml')
        return config.desktop_render.rss(today = date,
                articles = articles, board_path="+u/%s/+favorite_rss" % username,
                board_desc = u'%s의 즐겨찾는 보드 피드' % username,
                link_address = 'http://noah.kaist.ac.kr/+u/%s' % username)

    @util.error_catcher
    def favorite_atom_get(self, mobile, username, user_id):
        articles = user.get_favorite_board_feed(user_id, config.favorite_feed_size)
        date = datetime.today()
        web.header('Content-Type', 'application/atom+xml')
        return config.desktop_render.atom(today = date,
                articles = articles, board_path="+u/%s/+favorite_atom" % username,
                board_desc = u'%s의 즐겨찾는 보드 피드' % username,
                self_address = 'http://noah.kaist.ac.kr/+u/%s/+favorite_atom' % username,
                href_address = 'http://noah.kaist.ac.kr/+u/%s' % username)

    @util.error_catcher
    @util.session_helper
    def new_article_get(self, mobile, username, user_id, current_uid = -1):
        if user_id != current_uid:
            raise web.unauthorized(render[mobile].error(error_message=_('LOOKING_OTHERS_NEW_ARTICLES'), help_context='error'))

        return render[mobile].new_article(articles = user.get_unreaded_articles(user_id),
                title = u'새글읽기',
                board_desc = u'새글읽기')

    @util.error_catcher
    @util.session_helper
    def modify_get(self, mobile, username, user_id, current_uid = -1):
        if user_id != current_uid:
            raise web.unauthorized(render[mobile].error(error_message=_('MODIFYING_OTHERS_INFORMATION'), help_context='error'))
        referer = posixpath.join('/', '+u', username)
        if mobile:
            referer = posixpath.join('/m', referer)
        return render[mobile].myinfo_edit(user = user.get_user(user_id)[1],
                username = username, user_id = user_id,
                title = u'내 정보 수정',
                board_desc = u'내 정보 수정',
                referer = web.ctx.env.get('HTTP_REFERER', referer),
                help_context = 'myinfo')

    @util.error_catcher
    @util.confirmation_helper
    @util.session_helper
    def modify_post(self, mobile, username, user_id, current_uid = -1):
        data = web.input()
        if not user.verify_password(user_id, data.oldpass):
            return render[mobile].error(error_message=_('INVALID_PASSWORD'), help_context='error')
        if data.newpass1 != data.newpass2:
            return render[mobile].error(error_message = _('PASSWORD_DO_NOT_MATCH'), help_context='error')
        if len(data.newpass1) > 0 and len(data.newpass1) < 6:
            return render[mobile].error(error_message = _('PASSWORD_TOO_SHORT'), help_context='error')
        if len(data.newpass1) == 0:
            password = data.oldpass
        else:
            password = data.newpass1
        nick = data.nick
        email = data.email
        homepage = data.homepage
        sig = data.sig
        introduction = data.introduction
        language = data.language
        user_info = user.get_user(user_id)
        change_lang = False
        if language != user_info[1].language:
            change_lang = True
        ret = user.modify_user(user_id, locals())
        if change_lang:
            web.ctx.session.lang = language
        if mobile:
            raise web.seeother('/m/+u/%s' % username)
        else:
            raise web.seeother('/+u/%s' % username)

    @util.error_catcher
    @util.session_helper
    def leave_get(self, mobile, username, user_id, current_uid = -1):
        if user_id != current_uid:
            return render[mobile].error(error_message=_('MODIFYING_OTHERS_INFORMATION'), help_context='error')
        default_referer = posixpath.join('/', '+u', username)
        return render[mobile].leave(board_desc = u'회원 탈퇴',
                title=u'회원 탈퇴', username = username,
                referer = web.ctx.env.get('HTTP_REFERER', default_referer),)

    @util.error_catcher
    @util.confirmation_helper
    @util.session_helper
    def leave_post(self, mobile, username, user_id, current_uid = -1):
        password = web.input().password
        if not user.verify_password(user_id, password):
            return render[mobile].error(error_message= _('INVALID_PASSWORD'), help_context='error')

        result = user.delete_user(user_id)
        if not result[0]:
            return render[mobile].error(error_message = result[1], help_context='error')
        web.ctx.session.uid = 0
        web.ctx.session.kill()
        if mobile:
            raise web.seeother('/m')
        else:
            raise web.seeother('/')

    @util.error_catcher
    @util.session_helper
    def my_board_get(self, mobile, username, user_id, current_uid = -1):
        my_board = user.get_owned_board(user_id)
        return render[mobile].view_subboard_list(
            child_boards = my_board, board_path = '',
            title=u'내 게시판', board_desc = u'내 게시판',
            list_type = u'내 게시판')

    @util.error_catcher
    @util.session_helper
    def favorites_get(self, mobile, username, user_id, current_uid = -1):
        fav_board = []
        for b in user.get_favorite_board(user_id):
            fav_board.append(board.get_board_info(b.bSerial))
        return render[mobile].view_subboard_list(
            child_boards = fav_board, board_path = '',
            title=u'즐겨찾는 게시판', board_desc = u'즐겨찾는 게시판',
            list_type = u'즐겨찾는 게시판')

    @util.error_catcher
    @util.session_helper
    def inbox_get(self, mobile, username, user_id, current_uid = -1):
        if user_id != current_uid:
            raise web.unauthorized(render[mobile].error(error_message=_('NO_PERMISSION'), help_context='error'))
        qs = web.ctx.query
        if len(qs) > 0:
            qs = qs[1:]
            qs = parse_qs(qs)
        if qs:
            page = int(qs['page'][0])
        else:
            page = 1
        mails = pm.inbox(user_id, page, config.mail_size)
        return config.desktop_render.inbox(mails = mails, 
                mailbox_name = u'받은 편지함',
                title = '%s - %s - %s' % (u'받은 편지함', username, config.branding),
                page = page, total_page = pm.inbox_count(user_id) / config.mail_size + 1)

    @util.error_catcher
    @util.session_helper
    def reply_message_get(self, mobile, username, user_id, current_uid = -1):
        message_id = -1
        qs = web.ctx.query
        if len(qs) > 0:
            qs = qs[1:]
            qs = parse_qs(qs)
        if qs:
            message_id = int(qs['message_id'][0])
        else:
            raise web.notfound(render[mobile].error(error_message=_('NO_SUCH_MESSAGE'), help_context='error'))
        mail = pm.get_mail(message_id)
        if mail.mReceiverSerial != current_uid:
            raise web.unauthorized(render[mobile].error(error_message=_('NO_PERMISSION'), help_context='error'))
        quote_text = u'메시지 "%s"에서:' % mail.mTitle
        return config.desktop_render.editor_mail(
            title = '%s - %s' % (u'답장 쓰기', config.branding),
            mail_title = 'Re: %s' % mail.mTitle,
            mail_body = '\n\n[quote=%s]%s\n[/quote]' % (quote_text, mail.mContent),
            mail_receiver = user._get_username_from_uid(mail.mSenderSerial))

    @util.error_catcher
    @util.session_helper
    def write_message_get(self, mobile, username, user_id, current_uid = -1):
        if user_id != current_uid:
            raise web.unauthorized(render[mobile].error(error_message=_('NO_PERMISSION'), help_context='error'))
        return config.desktop_render.editor_mail(
                title = '%s - %s' % (u'메시지 쓰기', config.branding))

    @util.error_catcher
    @util.session_helper
    def write_message_post(self, mobile, username, user_id, current_uid = -1):
        if user_id != current_uid:
            raise web.unauthorized(render[mobile].error(error_message=_('NO_PERMISSION'), help_context='error'))
        data = web.input()
        title = data.title
        body = data.body
        receiver_id = data.id
        receiver_uid = user._get_uid_from_username(receiver_id)
        if receiver_uid < 0:
            raise web.notfound(render[mobile].error(error_message=_('INVALID_RECEIVER'), help_context='error'))
        result = pm.send_mail(current_uid, receiver_uid, title, body)
        if not result[0]:
            raise web.internalerror(render[mobile].error(error_message=result[1], help_context='error'))
        else:
            raise web.seeother('/+u/%s/+inbox' % username)

    @util.error_catcher
    @util.session_helper
    def read_message_get(self, mobile, username, user_id, current_uid = -1):
        # XXX: 현재는 메시지 번호를 Query String에 담아서 전달한다.
        # 차후 정규 표현식을 고쳐서 다른 게시판처럼 만들어야 한다.
        message_id = -1
        qs = web.ctx.query
        if len(qs) > 0:
            qs = qs[1:]
            qs = parse_qs(qs)
        if qs:
            message_id = int(qs['message_id'][0])
        else:
            raise web.notfound(render[mobile].error(error_message=_('NO_SUCH_MESSAGE'), help_context='error'))
        mail = pm.get_mail(message_id)
        if mail.mReceiverSerial != current_uid:
            raise web.unauthorized(render[mobile].error(error_message=_('NO_PERMISSION'), help_context='error'))
        pm.mark_as_read(message_id)
        return config.desktop_render.read_mail(mail = mail, 
                title = '%s - %s - %s' % (u'메시지 보기', mail.mTitle, config.branding),)

    @util.error_catcher
    @util.session_helper
    def delete_message_get(self, mobile, username, user_id, current_uid = -1):
        # XXX: 현재는 메시지 번호를 Query String에 담아서 전달한다.
        # 차후 정규 표현식을 고쳐서 다른 게시판처럼 만들어야 한다.
        message_id = -1
        qs = web.ctx.query
        if len(qs) > 0:
            qs = qs[1:]
            qs = parse_qs(qs)
        if qs:
            message_id = int(qs['message_id'][0])
        else:
            raise web.notfound(render[mobile].error(error_message=_('NO_SUCH_MESSAGE'), help_context='error'))
        mail = pm.get_mail(message_id)
        if mail.mReceiverSerial != current_uid:
            raise web.unauthorized(render[mobile].error(error_message=_('NO_PERMISSION'), help_context='error'))
        if mobile:
            default_referer = posixpath.join('/m/+u', username, '+inbox')
            action='%s?message_id=%s' % (posixpath.join('/m/+u', username, '+delete_message'), message_id)
        else:
            default_referer = posixpath.join('/+u', username, '+inbox')
            action='%s?message_id=%s' % (posixpath.join('/+u', username, '+delete_message'), message_id)
        return render[mobile].question(question=u'메시지를 삭제하시겠습니까?',
                board_path = '', board_desc = u'확인', title=u'확인',
                action = action,
                referer=web.ctx.env.get('HTTP_REFERER', default_referer))

    @util.error_catcher
    @util.confirmation_helper
    @util.session_helper
    def delete_message_post(self, mobile, username, user_id, current_uid = -1):
        # XXX: 현재는 메시지 번호를 Query String에 담아서 전달한다.
        # 차후 정규 표현식을 고쳐서 다른 게시판처럼 만들어야 한다.
        message_id = -1
        qs = web.ctx.query
        if len(qs) > 0:
            qs = qs[1:]
            qs = parse_qs(qs)
        if qs:
            message_id = int(qs['message_id'][0])
        else:
            raise web.notfound(render[mobile].error(error_message=_('NO_SUCH_MESSAGE'), help_context='error'))
        mail = pm.get_mail(message_id)
        if mail.mReceiverSerial != current_uid:
            raise web.unauthorized(render[mobile].error(error_message=_('NO_PERMISSION'), help_context='error'))
        result = pm.delete_mail(message_id)
        if result[0]:
            if mobile:
                raise web.seeother('/m/+u/%s/+inbox' % username)
            else:
                raise web.seeother('/+u/%s/+inbox' % username)
        else:
            return config.render[mobile].error(error_message = ret[1],
                    help_context = 'error')
