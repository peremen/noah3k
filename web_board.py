#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import web
import config
import board, user, article
import util, attachment, acl
from datetime import datetime
from cgi import parse_qs
import urllib
import posixpath
from render import render
import i18n
_ = i18n.custom_gettext

class board_actions:
    def GET(self, theme, board_name, action):
        if action[0] == '+':
            action = action[1:]
        if action == '*':
            action = 'subboard_list'
        return self.caller(theme, board_name, action, 'get')

    def POST(self, theme, board_name, action):
        if action[0] == '+':
            action = action[1:]
        if action == '*':
            action = 'subboard_list'
        return self.caller(theme, board_name, action, 'post')

    def caller(self, theme, board_name, action, method):
        if not theme:
            theme = ''
        if board_name[0] == '/':
            board_name = board_name[1:]
        if not render.has_key(theme):
            board_name = posixpath.join(theme, board_name)
            theme = 'default'
        if board_name == '^root':
            board_id = 1
            board_name = '/'
        else:
            board_id = board._get_board_id_from_path(board_name)
        if board_id < 0:
            raise web.notfound(render[theme].error(error_message = _('INVALID_BOARD'), help_context='error'))
        try:
            return eval('self.%s_%s' % (action, method))(theme, board_name, board_id)
        except AttributeError:
            raise web.notfound(render[theme].error(error_message = _('INVALID_ACTION'), help_context='error'))

    @util.error_catcher
    @util.session_helper
    def subscribe_get(self, theme, board_name, board_id, current_uid = -1):
        if theme == 'default':
            referer = web.ctx.env.get('HTTP_REFERER', '/')
        else:
            referer = web.ctx.env.get('HTTP_REFERER', '/%s'%theme)

        if user.is_subscribed(current_uid, board_id):
            user.remove_subscription_board(current_uid, board_id)
        else:
            user.add_subscription_board(current_uid, board_id)

        raise web.seeother(referer)

    @util.error_catcher
    @util.session_helper
    def write_get(self, theme, board_name, board_id, current_uid = -1):
        board_info = board.get_board_info(board_id)
        board_desc = board_info.bDescription
        user_info = user.get_user(current_uid)[1]
        return render[theme].editor(title = _('Write article - %s') % (board_name),
                action='write', action_name = _('Write article'),
                board_path = board_name, board_desc = board_desc, lang="ko",
                body = '\n\n\n%s' % user_info['uSig'], help_context='editor')

    @util.error_catcher
    @util.session_helper
    def write_post(self, theme, board_name, board_id, current_uid = -1):
        a = dict(title = web.input().title, body = web.input().content)
        board_info = board.get_board_info(board_id)
        ret = article.write_article(current_uid, board_id, a)
        if ret[0] == True:
            user.update_unreaded_articles_board(current_uid, board_id)
            user.read_article(current_uid, ret[1])

            fs = web.ctx.get('_fieldstorage')
            try:
                if fs.has_key('new_attachment'):
                    new_attachment = fs['new_attachment']
                    if type(new_attachment) == list:
                        for f in new_attachment:
                            attachment.add_attachment(ret[1], f.filename, f.value)
                    else:
                        try:
                            attachment.add_attachment(ret[1], new_attachment.filename, new_attachment.value)
                        except:
                            pass
            except:
                pass
            if theme == 'default':
                raise web.seeother('/%s/+read/%s' % (board_name, ret[1]))
            else:
                raise web.seeother('/%s/%s/+read/%s' % (theme, board_name, ret[1]))
        else:
            return render[theme].error(error_message = ret[1], help_context='error')

    @util.error_catcher
    def rss_get(self, theme, board_name, board_id):
        if web.ctx.query == '':
            qs = dict()
            feed_size = config.feed_size
        else:
            qs = parse_qs(web.ctx.query[1:])
            feed_size = int(qs['size'][0])
        board_info = board.get_board_info(board_id)
        if board_info.bType == 0: # 디렉터리
            return

        date = datetime.today()
        articles = article.get_article_feed(board_id, feed_size)
        web.header('Content-Type', 'application/rss+xml')
        return render['default'].rss(board_path = board_name,
                board_desc = board_info.bDescription,
                articles=articles, today=date)

    @util.error_catcher
    def atom_get(self, theme, board_name, board_id):
        if web.ctx.query == '':
            qs = dict()
            feed_size = config.feed_size
        else:
            qs = parse_qs(web.ctx.query[1:])
            feed_size = int(qs['size'][0])
        board_info = board.get_board_info(board_id)
        if board_info.bType == 0: # 디렉터리
            return

        date = datetime.today()
        articles = article.get_article_feed(board_id, feed_size)
        web.header('Content-Type', 'application/atom+xml')
        return render['default'].atom(board_path = board_name,
                board_desc = board_info.bDescription,
                articles=articles, today=date)

    @util.error_catcher
    @util.session_helper
    def add_to_favorites_get(self, theme, board_name, board_id, current_uid = -1):
        user.add_favorite_board(current_uid, board_id)
        if theme == 'default':
            raise web.seeother('/%s' % board_name)
        else:
            raise web.seeother('/%s/%s' % (theme, board_name))

    @util.error_catcher
    @util.session_helper
    def remove_from_favorites_get(self, theme, board_name, board_id, current_uid = -1):
        user.remove_favorite_board(current_uid, board_id)
        if theme == 'default':
            raise web.seeother('/%s' % board_name)
        else:
            raise web.seeother('/%s/%s' % (theme, board_name))

    @util.error_catcher
    def summary_get(self, theme, board_name, board_id):
        board_info = board.get_board_info(board_id)
        if board_id == 1:
            board_name = '^root'
        return render[theme].board_summary(board_info = board_info,
                board_path = board_name,
                board_desc = board_info.bDescription, 
                title = _('Information - %s') % (board_info.bName))

    @util.error_catcher
    def subboard_list_get(self, theme, board_name = '', board_id = 1):
        board_info = board.get_board_info(board_id)
        child_board = board.get_child(board_id)
        if board_name == "":
            board_name = _('Main menu')
            board_path = ""
        else:
            board_path = board_name
            if board_name[0] != '/':
                board_name = '/%s' % (board_name)
        return render[theme].view_subboard_list(lang="ko",
                title = board_name,
                board_path = board_path,
                board_desc = board_info.bDescription,
                child_boards = child_board)

    @util.error_catcher
    def cover_get(self, theme, board_name, board_id):
        board_info = board.get_board_info(board_id)
        return render['default'].cover(title = board_name,
                board_cover = board_info.bInformation)

    @util.error_catcher
    @util.session_helper
    def create_board_get(self, theme, board_name, board_id, current_uid = -1):
        board_info = board.get_board_info(board_id)
        if not acl.is_allowed('board', board_id, current_uid, 'create'):
            return render[theme].error(error_message = _('NO_PERMISSION'), help_context='error')
        if board_id == 1:
            board_name = '^root'
        default_referer = posixpath.join('/', board_name, '+summary')
        if theme == 'default':
            default_referer = posixpath.join('/', default_referer)
        else:
            default_referer = posixpath.join('/%s'%theme, default_referer)
        return render[theme].board_editor(action='create_board', board_info = board_info,
                board_path = board_name, board_desc = board_info.bDescription, 
                title = _('Create child board - %s') % (board_info.bName),
                referer = web.ctx.env.get('HTTP_REFERER', default_referer))

    @util.error_catcher
    @util.confirmation_helper
    @util.session_helper
    def create_board_post(self, theme, board_name, board_id, current_uid = -1):
        board_info = board.get_board_info(board_id)
        if not acl.is_allowed('board', board_id, current_uid, 'create'):
            return render[theme].error(error_message = _('NO_PERMISSION'), help_context='error')
        user_data = web.input()
        comment = 1 if user_data.has_key('commentable') else 0
        write_by_other = 1 if user_data.has_key('writable') else 0
        indexable = 1 if user_data.has_key('indexable') else 0
        show_avatar = 1 if user_data.has_key('show_avatar') else 0

        owner_uid = user._get_uid_from_username(user_data.owner)
        if owner_uid < 0:
            return render[theme].error(error_message=_('NO_SUCH_USER_FOR_BOARD_ADMIN'), help_context='error')
        if user_data.name.strip() == '':
            return render[theme].error(error_message = _('NO_NAME_SPECIFIED'), help_context='error')
        new_path = posixpath.join('/', board_name, user_data.name)
        if board._get_board_id_from_path(new_path) > 0:
            return render[theme].error(error_message = _('BOARD_EXISTS'), help_context='error')

        settings = dict(path=new_path, board_owner = owner_uid,
                cover = user_data.information,
                description = user_data.description,
                type = int(user_data.type),
                guest_write = write_by_other,
                can_comment = comment,
                indexable = indexable, show_avatar = show_avatar,
                current_uid = current_uid)
        ret = board.create_board(board_id, settings)
        if ret[0] == False:
            return render[theme].error(error_message = ret[1] ,help_context = 'error')
        if theme == 'default':
            raise web.seeother('%s' % (new_path))
        else:
            raise web.seeother('/%s%s' % (theme, new_path))

    @util.error_catcher
    @util.session_helper
    def modify_get(self, theme, board_name, board_id, current_uid = -1):
        board_info = board.get_board_info(board_id)
        if not acl.is_allowed('board', board_id, current_uid, 'modify'):
            return render[theme].error(error_message=_('NO_PERMISSION'), help_context='error')
        if board_id == 1:
            board_name = '^root'
        default_referer = posixpath.join('/', board_name, '+summary')
        if theme == 'default':
            default_referer = posixpath.join('/', default_referer)
        else:
            default_referer = posixpath.join('/%s'%theme, default_referer)
        return render[theme].board_editor(action='modify', board_info = board_info,
                board_path = board_name, board_desc = board_info.bDescription, 
                title = _('Modify information - %s') % (board_info.bName),
                referer = web.ctx.env.get('HTTP_REFERER', default_referer))

    @util.error_catcher
    @util.session_helper
    @util.confirmation_helper
    def modify_post(self, theme, board_name, board_id, current_uid = -1):
        board_info = board.get_board_info(board_id)
        if not acl.is_allowed('board', board_id, current_uid, 'modify'):
            return render[theme].error(error_message=_('NO_PERMISSION'), help_context='error')
        data = web.input()
        comment = 1 if data.has_key('commentable') else 0
        write_by_other = 1 if data.has_key('writable') else 0
        indexable = 1 if data.has_key('indexable') else 0
        show_avatar = 1 if data.has_key('show_avatar') else 0

        owner_uid = user._get_uid_from_username(web.input().owner)
        if owner_uid < 0:
            return render[theme].error(error_message=_('NO_SUCH_USER_FOR_BOARD_ADMIN'), help_context='error')

        board_info = dict(path = data.path, name = data.name,
                owner = owner_uid, board_type = data.type,
                can_comment = comment, can_write_by_other = write_by_other,
                indexable = indexable, show_avatar = show_avatar,
                description = data.description,
                cover = data.information)
        result = board.edit_board(current_uid, board_id, board_info)
        if result[0] == False:
            return render[theme].error(error_message = result[1], help_context='error')
        else:
            if theme == 'default':
                raise web.seeother('%s' % result[1])
            else:
                raise web.seeother('/%s%s' % (theme, result[1]))

    @util.error_catcher
    @util.session_helper
    def delete_get(self, theme, board_name, board_id, current_uid = -1):
        if board_id == 1:
            board_name = '^root'
        if theme == 'default':
            default_referer = posixpath.join('/', board_name, '+summary')
            action = posixpath.join('/', board_name, '+delete')
        else:
            default_referer = posixpath.join('/%s' % theme, board_name, '+summary')
            action = posixpath.join('/%s' % theme, board_name, '+delete')
        return render[theme].question(question=_('Do you want to delete this board?'),
                board_path = board_name, board_desc = _('Confirmation'), title=_('Confirmation'),
                action=action,
                referer=web.ctx.env.get('HTTP_REFERER', default_referer))

    @util.error_catcher
    @util.session_helper
    @util.confirmation_helper
    def delete_post(self, theme, board_name, board_id, current_uid = -1):
        ret = board.delete_board(current_uid, board_id)
        if ret[0] == True:
            if theme == 'default':
                raise web.seeother('%s' % (ret[1]))
            else:
                raise web.seeother('/%s%s' % (theme, ret[1]))
        else:
            return render[theme].error(error_message = ret[1], help_context='error')

    @util.error_catcher
    def search_get(self, theme, board_name, board_id):
        board_info = board.get_board_info(board_id)
        if web.ctx.query == '':
            qs = dict()
        else:
            # XXX: http://bugs.python.org/issue8136
            qs = parse_qs(urllib.unquote(web.ctx.query[1:]).encode('latin-1').decode('utf-8'))

        if not qs.has_key('q'):
            return render[theme].error(error_message = _('NO_KEYWORD_SPECIFIED'),
                    help_context = 'error')
        keyword = qs['q'][0]
        if qs.has_key('size'):
            page_size = int(qs['size'][0])
        else:
            page_size = config.page_size
        if qs.has_key('page'):
            page_no = int(qs['page'][0])
        else:
            page_no = 1
        author = False
        title = True
        body = True
        if qs.has_key('author'):
            author = True
            title = False
            body = False
        if qs.has_key('title'):
            title = True
            body = False
        if qs.has_key('body'):
            body = True
        ret = article.search_article(board_id, keyword, page_size, page_no,
                author, title, body)
        search_qs = "/+search?"
        if author:
            search_qs += "author=1&"
        if title:
            search_qs += "title=1&"
        if body:
            search_qs += "body=1&"
        if keyword:
            search_qs += "q=%s" % urllib.quote(keyword.encode('utf-8'))
        if ret[0]:
            return render[theme].view_board(lang="ko",
                title = board_info.bName,
                board_path = board_info.bName[1:],
                board_desc = _('Search Results'),
                articles=ret[2], marked_articles = [],
                total_page = ret[1], page = page_no, feed = False,
                help_context = 'view_board', indent = False,
                author_checked = author, title_checked = title,
                body_checked = body, search_keyword = keyword,
                search_qs = search_qs)
        else:
            return render[theme].error(error_message = ret[1], help_context='error')
