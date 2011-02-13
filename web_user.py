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
import pm

class personal_actions_unauthorized:
    def GET(self, theme, username, action):
        if not render.has_key(theme):
            theme = 'default'
        user_id = user._get_uid_from_username(username)
        try:
            return eval('self.%s' % (action))(theme, username, user_id)
        except AttributeError:
            raise web.notfound(render[theme].error(error_message = _('INVALID_ACTION'), help_context='error'))

    @util.error_catcher
    def favorite_rss(self, theme, username, user_id):
        articles = user.get_favorite_board_feed(user_id, config.favorite_feed_size)
        date = datetime.today()
        web.header('Content-Type', 'application/rss+xml')

        return render['default'].rss(today = date,
                articles = articles, board_path="+u/%s/+favorite_rss" % username,
                board_desc = u'%s의 즐겨찾는 보드 피드' % username,
                link_address = 'http://noah.kaist.ac.kr/+u/%s' % username)

    @util.error_catcher
    def favorite_atom(self, theme, username, user_id):
        articles = user.get_favorite_board_feed(user_id, config.favorite_feed_size)
        date = datetime.today()
        web.header('Content-Type', 'application/atom+xml')

        return render['default'].atom(today = date,
                articles = articles, board_path="+u/%s/+favorite_atom" % username,
                board_desc = (u'%s의 즐겨찾는 보드 피드' % username),
                self_address = 'http://noah.kaist.ac.kr/+u/%s/+favorite_atom' % username,
                href_address = 'http://noah.kaist.ac.kr/+u/%s' % username)

class personal_page:
    @util.error_catcher
    @util.session_helper
    def GET(self, theme, current_uid = -1):
        if not render.has_key(theme):
            theme = 'default'
        user_id = web.ctx.session.uid

        f = [{'type':'rss', 'path':'/+u/+favorite_rss', 'name':u'즐겨찾기 피드 (RSS)'},
             {'type':'atom', 'path':'/+u/+favorite_atom', 'name':u'즐겨찾기 피드 (Atom)'},]
        return render[theme].myinfo(user = user.get_user(user_id)[1],
                user_id = user_id,
                title = _('My Information'), board_desc = _('My Information'),
                feeds = f, help_context='myinfo')

class personal_page_others:
    @util.error_catcher
    @util.session_helper
    def GET(self, theme, username, current_uid = -1):
        if not render.has_key(theme):
            theme = 'default'
        user_id = user._get_uid_from_username(username)
        if user_id < 0:
            raise web.notfound(render[theme].error(error_message = _('NO_SUCH_USER'), help_context='error'))
        return render[theme].myinfo(user = user.get_user(user_id)[1],
                user_id = user_id,
                title = _('User Information'), board_desc = _('User Information'),
                help_context='myinfo')

class personal_actions:
    def GET(self, theme, action):
        return self.caller(theme, action, 'get')

    def POST(self, theme, action):
        return self.caller(theme, action, 'post')

    def caller(self, theme, action, method):
        if not render.has_key(theme):
            theme ='default'
        try:
            return eval('self.%s_%s' % (action, method))(theme)
        except AttributeError:
            raise web.notfound(render[theme].error(error_message = _('INVALID_ACTION'), help_context='error'))

    @util.error_catcher
    @util.session_helper
    def new_article_get(self, theme, current_uid = -1):
        user.update_new_article_hit(current_uid)
        return render[theme].new_article(articles = user.get_unreaded_articles(current_uid),
                uid = current_uid, title = _('New Article'),
                board_desc = _('New Article'))

    @util.error_catcher
    @util.session_helper
    def clear_new_article_get(self, theme, current_uid = -1):
		user.read_all_articles(current_uid)
		if theme == 'default':
			raise web.seeother('/+u/+new_article')
		else:
			raise web.seeother('/%s/+u/+new_article' % theme)

    @util.error_catcher
    @util.session_helper
    def modify_get(self, theme, current_uid = -1):
        user_id = current_uid
        usr = user.get_user(user_id)[1]

        if theme == 'default':
            referer = '/+u'
        else:
            referer = '/%s/+u' % theme
        return render[theme].myinfo_edit(user = user.get_user(user_id)[1],
                user_id = user_id,
                title = _('Edit My Information'),
                board_desc = _('Edit My Information'),
                referer = web.ctx.env.get('HTTP_REFERER', referer),
                help_context = 'myinfo')

    @util.error_catcher
    @util.confirmation_helper
    @util.session_helper
    def modify_post(self, theme, current_uid = -1):
        user_id = current_uid
        usr = user.get_user(user_id)[1]

        data = web.input(profile_image = {})
        if data.newpass1 and not user.verify_password(user_id, data.oldpass):
            return render[theme].error(error_message=_('INVALID_PASSWORD'), help_context='error')
        if data.newpass1 != data.newpass2:
            return render[theme].error(error_message = _('PASSWORD_DO_NOT_MATCH'), help_context='error')
        if len(data.newpass1) > 0 and len(data.newpass1) < 6:
            return render[theme].error(error_message = _('PASSWORD_TOO_SHORT'), help_context='error')
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
        profile_image = data.profile_image.value
        delete_profile_image = data.has_key('delete_profile_image')

        ret = user.modify_user(user_id, locals())
        if change_lang:
            web.ctx.session.lang = language
        if theme == 'default':
            raise web.seeother('/+u')
        else:
            raise web.seeother('/%s/+u' % theme)

    @util.error_catcher
    @util.session_helper
    def leave_get(self, theme, current_uid = -1):
        user_id = current_uid
        usr = user.get_user(user_id)[1]

        default_referer = posixpath.join('/', '+u')
        return render[theme].leave(board_desc = _('Leave NOAH'),
                title=_('Leave NOAH'),
                referer = web.ctx.env.get('HTTP_REFERER', default_referer),)

    @util.error_catcher
    @util.confirmation_helper
    @util.session_helper
    def leave_post(self, theme, current_uid = -1):
        user_id = current_uid
        usr = user.get_user(user_id)[1]

        password = web.input().password
        if not user.verify_password(user_id, password):
            return render[theme].error(error_message= _('INVALID_PASSWORD'), help_context='error')

        result = user.delete_user(user_id)
        if not result[0]:
            return render[theme].error(error_message = result[1], help_context='error')
        web.ctx.session.uid = 0
        web.ctx.session.kill()
        if theme == 'default':
            raise web.seeother('/')
        else:
            raise web.seeother('/%s' % theme)

    @util.error_catcher
    @util.session_helper
    def my_board_get(self, theme, current_uid = -1):
        my_board = user.get_owned_board(current_uid)
        return render[theme].view_subboard_list(
            child_boards = my_board, board_path = '',
            title=_('My Boards'), board_desc = _('My Boards'),
            list_type = _('My Boards'))

    @util.error_catcher
    @util.session_helper
    def favorites_get(self, theme, current_uid = -1):
        fav_board = []
        for b in user.get_favorite_board(current_uid):
            fav_board.append(board.get_board_info(b.bSerial))
        return render[theme].view_subboard_list(
            child_boards = fav_board, board_path = '',
            title=_('Favorite Boards'), board_desc = _('Favorite Boards'),
            list_type = _('Favorite Boards'))

    @util.error_catcher
    @util.session_helper
    def inbox_get(self, theme, current_uid = -1):
        user_id = current_uid
        usr = user.get_user(user_id)[1]

        qs = web.ctx.query
        if len(qs) > 0:
            qs = qs[1:]
            qs = parse_qs(qs)
        if qs:
            page = int(qs['page'][0])
        else:
            page = 1
        mails = pm.inbox(user_id, page, config.mail_size)
        return render['default'].inbox(mails = mails, 
                mailbox_name = _('Inbox'),
                title = '%s - %s' % (_('Inbox'), usr['uId']),
                page = page, total_page = pm.inbox_count(user_id) / config.mail_size + 1)

    @util.error_catcher
    @util.session_helper
    def reply_message_get(self, theme, current_uid = -1):
        user_id = current_uid
        usr = user.get_user(user_id)[1]

        message_id = -1
        qs = web.ctx.query
        if len(qs) > 0:
            qs = qs[1:]
            qs = parse_qs(qs)
        if qs:
            message_id = int(qs['message_id'][0])
        else:
            raise web.notfound(render[theme].error(error_message=_('NO_SUCH_MESSAGE'), help_context='error'))
        mail = pm.get_mail(message_id)
        if mail.mReceiverSerial != current_uid:
            raise web.unauthorized(render[theme].error(error_message=_('NO_PERMISSION'), help_context='error'))
        quote_text = _('From message \"%s\":') % mail.mTitle
        return render['default'].editor_mail(
            title = _('Write Reply'),
            mail_title = 'Re: %s' % mail.mTitle,
            mail_body = '\n\n[quote=%s]%s\n[/quote]' % (quote_text, mail.mContent),
            mail_receiver = user._get_username_from_uid(mail.mSenderSerial))

    @util.error_catcher
    @util.session_helper
    def write_message_get(self, theme, current_uid = -1):
        return render['default'].editor_mail(title = _('Write Message'))

    @util.error_catcher
    @util.session_helper
    def write_message_post(self, theme, current_uid = -1):
        user_id = current_uid
        usr = user.get_user(user_id)[1]

        data = web.input()
        title = data.title
        body = data.body
        receiver_id = data.id
        receiver_uid = user._get_uid_from_username(receiver_id)
        if receiver_uid < 0:
            raise web.notfound(render[theme].error(error_message=_('INVALID_RECEIVER'), help_context='error'))
        result = pm.send_mail(current_uid, receiver_uid, title, body)
        if not result[0]:
            raise web.internalerror(render[theme].error(error_message=result[1], help_context='error'))
        else:
            raise web.seeother('/+u/+inbox')

    @util.error_catcher
    @util.session_helper
    def read_message_get(self, theme, current_uid = -1):
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
            raise web.notfound(render[theme].error(error_message=_('NO_SUCH_MESSAGE'), help_context='error'))
        mail = pm.get_mail(message_id)
        if mail.mReceiverSerial != current_uid:
            raise web.unauthorized(render[theme].error(error_message=_('NO_PERMISSION'), help_context='error'))
        pm.mark_as_read(message_id)
        return render['default'].read_mail(mail = mail, 
                title = '%s - %s' % (_('Read Message'), mail.mTitle)
                )

    @util.error_catcher
    @util.session_helper
    def delete_message_get(self, theme, current_uid = -1):
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
            raise web.notfound(render[theme].error(error_message=_('NO_SUCH_MESSAGE'), help_context='error'))
        mail = pm.get_mail(message_id)
        if mail.mReceiverSerial != current_uid:
            raise web.unauthorized(render[theme].error(error_message=_('NO_PERMISSION'), help_context='error'))
        if theme == 'default':
            default_referer = posixpath.join('/+u', '+inbox')
            action='%s?message_id=%s' % (posixpath.join('/+u', '+delete_message'), message_id)
        else:
            default_referer = posixpath.join('/%s/+u' % theme, '+inbox')
            action='%s?message_id=%s' % (posixpath.join('/%s/+u' % theme, '+delete_message'), message_id)
        return render[theme].question(question=_('Do you want to delete the message?'),
                board_path = '', board_desc = _('Confirmation'), title=_('Confirmation'),
                action = action,
                referer=web.ctx.env.get('HTTP_REFERER', default_referer))

    @util.error_catcher
    @util.confirmation_helper
    @util.session_helper
    def delete_message_post(self, theme, current_uid = -1):
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
            raise web.notfound(render[theme].error(error_message=_('NO_SUCH_MESSAGE'), help_context='error'))
        mail = pm.get_mail(message_id)
        result = pm.delete_mail(message_id)
        if result[0]:
            if theme == 'default':
                raise web.seeother('/+u/+inbox')
            else:
                raise web.seeother('/%s/+u/+inbox' % theme)
        else:
            return config.render[theme].error(error_message = ret[1],
                    help_context = 'error')
