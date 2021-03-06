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

class personal_actions_unauthorized:
    @util.theme
    def GET(self, username, action):
        user_id = user._get_uid_from_username(username)
        try:
            return eval('self.%s' % (action))(username, user_id)
        except AttributeError:
            raise web.notfound(util.render().error(error_message = _('INVALID_ACTION'), help_context='error'))

    def generate_feed(self, username, user_id, feed_type, feed_source):
        # feed_type: 0: rss, 1: atom
        # feed_source: 0: 즐겨찾기, 1: 새글읽기
        if web.ctx.query == '':
            qs = dict()
            feed_size = config.feed_size
        else:
            qs = parse_qs(web.ctx.query[1:])
            feed_size = int(qs['size'][0])

        article = None
        date = datetime.today()
        feed_title = ''
        feed_user_address = 'http://noah.kaist.ac.kr/+u/%s' % username
        board_path = ''
        feed_self_address = ''

        if feed_source == 0:
            articles = user.get_favorite_board_feed(user_id, feed_size)
            feed_title = u'%s의 즐겨찾는 보드 피드' % username
            board_path = '+u/%s/+favorite_%s' % (username, '%s')
        elif feed_source == 1:
            articles = user.get_unreaded_articles(user_id, feed_size)
            feed_title = u'%s의 구독하는 보드 피드' % username
            board_path = '+u/%s/+subscription_%s' % (username, '%s')

        if feed_type == 0:
            web.header('Content-Type', 'application/rss+xml')
            board_path = board_path % ('rss')
            feed_self_address = 'http://noah.kaist.ac.kr/%s' % board_path

            return render['default'].rss(today = date,
                    articles = articles, board_path=board_path,
                    board_desc = feed_title,
                    link_address = feed_user_address)
        elif feed_type == 1:
            web.header('Content-Type', 'application/atom+xml')
            board_path = board_path % ('atom')
            feed_self_address = 'http://noah.kaist.ac.kr/%s' % board_path

            return render['default'].atom(today = date,
                    articles = articles, board_path = board_path,
                    board_desc = feed_title,
                    self_address = feed_self_address,
                    head_address = feed_user_address)
        else:
            return ''

    @util.error_catcher
    def favorite_rss(self, username, user_id):
        return self.generate_feed(username, user_id, 0, 0)

    @util.error_catcher
    def favorite_atom(self, username, user_id):
        return self.generate_feed(username, user_id, 1, 0)

    @util.error_catcher
    def subscription_rss(self, username, user_id):
        return self.generate_feed(username, user_id, 0, 1)

    @util.error_catcher
    def subscription_atom(self, username, user_id):
        return self.generate_feed(username, user_id, 1, 1)

class personal_page:
    @util.error_catcher
    @util.session_helper
    @util.theme
    def GET(self, current_uid = -1):
        user_id = web.ctx.session.uid

        f = [{'type':'rss', 'path':'/+u/+favorite_rss', 'name':u'즐겨찾기 피드 (RSS)'},
             {'type':'atom', 'path':'/+u/+favorite_atom', 'name':u'즐겨찾기 피드 (Atom)'},]
        return util.render().myinfo(user = user.get_user(user_id)[1],
                user_id = user_id,
                title = _('My Information'), board_desc = _('My Information'),
                feeds = f, help_context='myinfo')

class personal_page_others:
    @util.error_catcher
    @util.session_helper
    @util.theme
    def GET(self, username, current_uid = -1):
        user_id = user._get_uid_from_username(username)
        if user_id < 0:
            raise web.notfound(util.render().error(error_message = _('NO_SUCH_USER'), help_context='error'))
        return util.render().myinfo(user = user.get_user(user_id)[1],
                user_id = user_id,
                title = _('User Information'), board_desc = _('User Information'),
                help_context='myinfo')

class personal_actions:
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
    @util.session_helper
    def new_article_get(self, current_uid = -1):
        user.update_new_article_hit(current_uid)
        return util.render().new_article(articles = user.get_unreaded_articles(current_uid),
                uid = current_uid, title = _('New Article'),
                board_desc = _('New Article'))

    @util.error_catcher
    @util.session_helper
    def clear_new_article_get(self, current_uid = -1):
        user.read_all_articles(current_uid)
        raise web.seeother(util.link('/+u/+new_article'))

    @util.error_catcher
    @util.session_helper
    def modify_get(self, current_uid = -1):
        user_id = current_uid
        usr = user.get_user(user_id)[1]

        referer = util.link('/+u')
        return util.render().myinfo_edit(user = user.get_user(user_id)[1],
                user_id = user_id,
                title = _('Edit My Information'),
                board_desc = _('Edit My Information'),
                referer = web.ctx.env.get('HTTP_REFERER', referer),
                help_context = 'myinfo')

    @util.error_catcher
    @util.confirmation_helper
    @util.session_helper
    def modify_post(self, current_uid = -1):
        user_id = current_uid
        usr = user.get_user(user_id)[1]

        data = web.input(profile_image = {})
        if data.newpass1 and not user.verify_password(user_id, data.oldpass):
            return util.render().error(error_message=_('INVALID_PASSWORD'), help_context='error')
        if data.newpass1 != data.newpass2:
            return util.render().error(error_message = _('PASSWORD_DO_NOT_MATCH'), help_context='error')
        if len(data.newpass1) > 0 and len(data.newpass1) < 6:
            return util.render().error(error_message = _('PASSWORD_TOO_SHORT'), help_context='error')
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
        theme = data.theme
        user_info = user.get_user(user_id)
        change_lang = False
        if language != user_info[1].language:
            change_lang = True
        profile_image = data.profile_image.value
        delete_profile_image = data.has_key('delete_profile_image')

        ret = user.modify_user(user_id, locals())
        if change_lang:
            web.ctx.session.lang = language
        raise web.seeother(util.link('/+u'))

    @util.error_catcher
    @util.session_helper
    def leave_get(self, current_uid = -1):
        user_id = current_uid
        usr = user.get_user(user_id)[1]

        default_referer = posixpath.join('/', '+u')
        return util.render().leave(board_desc = _('Leave NOAH'),
                title=_('Leave NOAH'),
                referer = web.ctx.env.get('HTTP_REFERER', default_referer),)

    @util.error_catcher
    @util.confirmation_helper
    @util.session_helper
    def leave_post(self, current_uid = -1):
        user_id = current_uid
        usr = user.get_user(user_id)[1]

        password = web.input().password
        if not user.verify_password(user_id, password):
            return util.render().error(error_message= _('INVALID_PASSWORD'), help_context='error')

        result = user.delete_user(user_id)
        if not result[0]:
            return util.render().error(error_message = result[1], help_context='error')
        web.ctx.session.uid = 0
        web.ctx.session.kill()
        raise web.seeother(util.link('/'))

    @util.error_catcher
    @util.session_helper
    def my_board_get(self, current_uid = -1):
        my_board = user.get_owned_board(current_uid)
        return util.render().subboard_list(
            child_boards = my_board, board_path = '',
            title=_('My Boards'), board_desc = _('My Boards'),
            list_type = _('My Boards'))

    @util.error_catcher
    @util.session_helper
    def favorites_get(self, current_uid = -1):
        fav_board = []
        for b in user.get_favorite_board(current_uid):
            fav_board.append(board.get_board_info(b.bSerial))
        return util.render().subboard_list(
            child_boards = fav_board, board_path = '',
            title=_('Favorite Boards'), board_desc = _('Favorite Boards'),
            list_type = _('Favorite Boards'))

    @util.error_catcher
    @util.session_helper
    def inbox_get(self, current_uid = -1):
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
        return util.render().inbox(mails = mails, 
                mailbox_name = _('Inbox'),
                title = '%s - %s' % (_('Inbox'), usr['uId']),
                page = page, total_page = pm.inbox_count(user_id) / config.mail_size + 1)

    @util.error_catcher
    @util.session_helper
    def reply_message_get(self, current_uid = -1):
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
            raise web.notfound(util.render().error(error_message=_('NO_SUCH_MESSAGE'), help_context='error'))
        mail = pm.get_mail(message_id)
        if mail.mReceiverSerial != current_uid:
            raise web.unauthorized(util.render().error(error_message=_('NO_PERMISSION'), help_context='error'))
        quote_text = _('From message \"%s\":') % mail.mTitle
        return util.render().mail_edit(
            title = _('Write Reply'),
            mail_title = 'Re: %s' % mail.mTitle,
            mail_body = '\n\n[quote=%s]%s\n[/quote]' % (quote_text, mail.mContent),
            mail_receiver = user._get_username_from_uid(mail.mSenderSerial))

    @util.error_catcher
    @util.session_helper
    def write_message_get(self, current_uid = -1):
        return util.render().mail_edit(title = _('Write Message'))

    @util.error_catcher
    @util.session_helper
    def write_message_post(self, current_uid = -1):
        user_id = current_uid
        usr = user.get_user(user_id)[1]

        data = web.input()
        title = data.title
        body = data.body
        receiver_id = data.id
        receiver_uid = user._get_uid_from_username(receiver_id)
        if receiver_uid < 0:
            raise web.notfound(util.render().error(error_message=_('INVALID_RECEIVER'), help_context='error'))
        result = pm.send_mail(current_uid, receiver_uid, title, body)
        if not result[0]:
            raise web.internalerror(util.render().error(error_message=result[1], help_context='error'))
        else:
            raise web.seeother('/+u/+inbox')

    @util.error_catcher
    @util.session_helper
    def read_message_get(self, current_uid = -1):
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
            raise web.notfound(util.render().error(error_message=_('NO_SUCH_MESSAGE'), help_context='error'))
        mail = pm.get_mail(message_id)
        if mail.mReceiverSerial != current_uid:
            raise web.unauthorized(util.render().error(error_message=_('NO_PERMISSION'), help_context='error'))
        pm.mark_as_read(message_id)
        return util.render().mail(mail = mail, 
                title = '%s - %s' % (_('Read Message'), mail.mTitle)
                )

    @util.error_catcher
    @util.session_helper
    def delete_message_get(self, current_uid = -1):
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
            raise web.notfound(util.render().error(error_message=_('NO_SUCH_MESSAGE'), help_context='error'))
        mail = pm.get_mail(message_id)
        if mail.mReceiverSerial != current_uid:
            raise web.unauthorized(util.render().error(error_message=_('NO_PERMISSION'), help_context='error'))
        default_referer = posixpath.join(util.link('/+u'), '+inbox')
        action='%s?message_id=%s' % (posixpath.join(util.link('/+u'), '+delete_message'), message_id)
        return util.render().question(
                question=_('Do you want to delete the message?'),
                board_path = '', 
                board_desc = _('Confirmation'), 
                title=_('Confirmation'),
                action = action,
                referer=web.ctx.env.get('HTTP_REFERER', default_referer))

    @util.error_catcher
    @util.confirmation_helper
    @util.session_helper
    def delete_message_post(self, current_uid = -1):
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
            raise web.notfound(util.render().error(error_message=_('NO_SUCH_MESSAGE'), help_context='error'))
        mail = pm.get_mail(message_id)
        result = pm.delete_mail(message_id)
        if result[0]:
            raise web.seeother(util.link('/+u/+inbox'))
        else:
            return util.render().error(error_message = ret[1],
                    help_context = 'error')

    @util.error_catcher
    @util.session_helper
    def manage_subscription_get(self, current_uid = -1):
        subscribed_boards = user.get_subscription_board_with_detail(current_uid)
        favorite_boards = user.get_favorite_board_with_detail(current_uid)
        return util.render().manage_subscription(subscribed_boards = subscribed_boards,
                favorite_boards = favorite_boards,
                title = _('Manage subscribed and favorite boards'),
                board_desc = _('Manage subscribed and favorite boards'),
                )

    @util.error_catcher
    @util.session_helper
    def manage_subscription_post(self, current_uid = -1):
        data = web.input()
        favorite_add = False
        favorite_delete = False
        favorite_delete_list = []
        favorite_name = ''

        subscription_add = False
        subscription_delete = False
        subscription_delete_list = []
        subscription_name = ''

        for k in data.keys():
            if k.startswith('favorite_delete_'):
                favorite_delete_list.append(int(k[16:]))
            elif k.startswith('subscription_delete_'):
                subscription_delete_list.append(int(k[20:]))
            elif k == 'favorite_add':
                favorite_add = True
            elif k == 'favorite_delete':
                favorite_delete = True
            elif k == 'favorite_name':
                favorite_name = data[k]
            elif k == 'subscription_add':
                subscription_add = True
            elif k == 'subscription_delete':
                subscription_delete = True
            elif k == 'subscription_name':
                subscription_name = data[k]

        if favorite_add == True:
            if favorite_name.strip() == '':
                raise web.seeother(util.link('/+u/+manage_subscription'))
            board_id = board._get_board_id_from_path(favorite_name)
            if board_id < 0:
                raise web.notfound(util.render().error(lang='ko', error_message=_('INVALID_BOARD'), help_context='error'))
            user.add_favorite_board(current_uid, board_id)
        elif favorite_delete == True:
            for b in favorite_delete_list:
                user.remove_favorite_board(current_uid, b)
        elif subscription_add == True:
            if favorite_name.strip() == '':
                raise web.seeother(util.link('/+u/+manage_subscription'))
            board_id = board._get_board_id_from_path(subscription_name)
            if board_id < 0:
                raise web.notfound(util.render().error(lang='ko', error_message=_('INVALID_BOARD'), help_context='error'))
            user.add_subscription_board(current_uid, board_id)
        elif subscription_delete == True:
            for b in subscription_delete_list:
                user.remove_subscription_board(current_uid, b)

        raise web.seeother(util.link('/+u/+manage_subscription'))

    @util.error_catcher
    @util.session_helper
    def my_article_get(self, current_uid = -1):
        qs = web.ctx.query
        if len(qs) > 0:
            qs = qs[1:]
            qs = parse_qs(qs)

        t = (user.get_post_count(current_uid) + config.page_size -1) / config.page_size
        if qs:
            page = int(qs['page'][0])
        else:
            page = 1

        my_article = user.get_article_list_by_user(current_uid, config.page_size, page)
        return util.render().board_aggregated(lang="ko",
            title = _('My Posts'),
            board_desc = _('My Posts'),
            articles=my_article,
            total_page = t, page = page,
            action = '/+u/+my_article',
            help_context = 'board')
