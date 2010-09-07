#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import web
import config
import board, user, article
import util, attachment, acl
from datetime import datetime
from cgi import parse_qs
import posixpath
from config import render
import i18n
_ = i18n.custom_gettext

class board_actions:
    def GET(self, mobile, board_name, action, dummy):
        if action[0] == '+':
            action = dummy
        if action == '*':
            action = 'subboard_list'
        return self.caller(mobile, board_name, action, 'get')

    def POST(self, mobile, board_name, action, dummy):
        if action[0] == '+':
            action = dummy
        return self.caller(mobile, board_name, action, 'post')

    def caller(self, mobile, board_name, action, method):
        if mobile:
            mobile = True
        else:
            mobile = False
        if board_name == '^root':
            board_id = 1
        else:
            board_id = board._get_board_id_from_path(board_name)
        if board_id < 0:
            raise web.notfound(render[mobile].error(error_message = _('INVALID_BOARD'), help_context='error'))
        try:
            return eval('self.%s_%s' % (action, method))(mobile, board_name, board_id)
        except AttributeError:
            raise web.notfound(render[mobile].error(error_message = _('INVALID_ACTION'), help_context='error'))

    @util.error_catcher
    @util.session_helper
    def write_get(self, mobile, board_name, board_id, current_uid = -1):
        board_info = board.get_board_info(board_id)
        board_desc = board_info.bDescription
        user_info = user.get_user(current_uid)[1]
        return render[mobile].editor(title = u"글 쓰기 - %s - %s" % (board_name, config.branding),
                action='write', action_name = u"글 쓰기",
                board_path = board_name, board_desc = board_desc, lang="ko",
                body = '\n\n\n%s' % user_info['uSig'], help_context='editor')

    @util.error_catcher
    @util.session_helper
    def write_post(self, mobile, board_name, board_id, current_uid = -1):
        a = dict(title = web.input().title, body = web.input().content)
        board_info = board.get_board_info(board_id)
        ret = article.write_article(current_uid, board_id, a)
        if ret[0] == True:
            fs = web.ctx.get('_fieldstorage')
            try:
                for f in fs['new_attachment']:
                    attachment.add_attachment(ret[1], f.filename, f.value)
            except TypeError:
                pass
            if mobile:
                raise web.seeother('/m/%s/+read/%s' % (board_name, ret[1]))
            else:
                raise web.seeother('/%s/+read/%s' % (board_name, ret[1]))
        else:
            return render[mobile].error(error_message = ret[1], help_context='error')

    @util.error_catcher
    def rss_get(self, mobile, board_name, board_id):
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
        return config.desktop_render.rss(board_path = board_name,
                board_desc = board_info.bDescription,
                articles=articles, today=date)

    @util.error_catcher
    def atom_get(self, mobile, board_name, board_id):
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
        return config.desktop_render.atom(board_path = board_name,
                board_desc = board_info.bDescription,
                articles=articles, today=date)

    @util.error_catcher
    @util.session_helper
    def add_to_favorites_get(self, mobile, board_name, board_id, current_uid = -1):
        user.add_favorite_board(current_uid, board_id)
        if mobile:
            raise web.seeother('/m/%s' % board_name)
        else:
            raise web.seeother('/%s' % board_name)

    @util.error_catcher
    @util.session_helper
    def remove_from_favorites_get(self, mobile, board_name, board_id, current_uid = -1):
        user.remove_favorite_board(current_uid, board_id)
        if mobile:
            raise web.seeother('/m/%s' % board_name)
        else:
            raise web.seeother('/%s' % board_name)

    @util.error_catcher
    def summary_get(self, mobile, board_name, board_id):
        board_info = board.get_board_info(board_id)
        return render[mobile].board_summary(board_info = board_info,
                board_path = board_name,
                board_desc = board_info.bDescription, 
                title = u'정보 - %s - %s' % (board_info.bName, config.branding))

    @util.error_catcher
    def subboard_list_get(self, mobile, board_name = '', board_id = 1):
        board_info = board.get_board_info(board_id)
        child_board = board.get_child(board_id)
        if board_name == "":
            board_name = u"초기 화면"
            board_path = ""
        else:
            board_path = board_name
            if board_name[0] != '/':
                board_name = '/%s' % (board_name)
        return render[mobile].view_subboard_list(lang="ko",
                title = u"%s - %s" % (board_name, config.branding),
                board_path = board_path,
                board_desc = board_info.bDescription,
                child_boards = child_board)

    @util.error_catcher
    def cover_get(self, mobile, board_name, board_id):
        board_info = board.get_board_info(board_id)
        return desktop_render.cover(title = u'%s - %s' % (board_name, config.branding),
                board_cover = board_info.bInformation)

    @util.error_catcher
    @util.session_helper
    def create_board_get(self, mobile, board_name, board_id, current_uid = -1):
        board_info = board.get_board_info(board_id)
        if not acl.is_allowed('board', board_id, current_uid, 'create'):
            return render[mobile].error(error_message = _('NO_PERMISSION'), help_context='error')
        default_referer = posixpath.join('/', board_name, '+summary')
        if mobile:
            default_referer = posixpath.join('/m', default_referer)
        return render[mobile].board_editor(action='create_board', board_info = board_info,
                board_path = board_name, board_desc = board_info.bDescription, 
                title = u'하위 게시판 만들기 - %s - %s' % (board_info.bName, config.branding),
                referer = web.ctx.env.get('HTTP_REFERER', default_referer))

    @util.error_catcher
    @util.confirmation_helper
    @util.session_helper
    def create_board_post(self, mobile, board_name, board_id, current_uid = -1):
        board_info = board.get_board_info(board_id)
        if not acl.is_allowed('board', board_id, current_uid, 'create'):
            return render[mobile].error(error_message = _('NO_PERMISSION'), help_context='error')
        user_data = web.input()
        comment, write_by_other = 0, 0 # XXX: DB 스키마를 BOOLEAN으로 바꿔야 함
        if user_data.commentable == 'yes':
            comment = 1
        if user_data.writable == 'yes':
            write_by_other = 1
        owner_uid = user._get_uid_from_username(user_data.owner)
        if owner_uid < 0:
            return render[mobile].error(error_message=_('NO_SUCH_USER_FOR_BOARD_ADMIN'), help_context='error')
        if user_data.name.strip() == '':
            return desktop_render.error(error_message = _('NO_NAME_SPECIFIED'), help_context='error')
        new_path = posixpath.join('/', board_name, user_data.name)
        if board._get_board_id_from_path(new_path) > 0:
            return render[mobile].error(error_message = _('BOARD_EXISTS'), help_context='error')

        settings = dict(path=new_path, board_owner = owner_uid,
                cover = user_data.information,
                description = user_data.description,
                type = int(user_data.type),
                guest_write = write_by_other,
                can_comment = comment,
                current_uid = current_uid)
        ret = board.create_board(board_id, settings)
        if ret[0] == False:
            return render[mobile].error(error_message = ret[1] ,help_context = 'error')
        if mobile:
            raise web.seeother('/m%s' % (new_path))
        else:
            raise web.seeother('%s' % (new_path))

    @util.error_catcher
    @util.session_helper
    def modify_get(self, mobile, board_name, board_id, current_uid = -1):
        board_info = board.get_board_info(board_id)
        if not acl.is_allowed('board', board_id, current_uid, 'modify'):
            return render[mobile].error(error_message=_('NO_PERMISSION'), help_context='error')
        default_referer = posixpath.join('/', board_name, '+summary')
        if mobile:
            default_referer = posixpath.join('/m', default_referer)
        return render[mobile].board_editor(action='modify', board_info = board_info,
                board_path = board_name, board_desc = board_info.bDescription, 
                title = u'정보 수정 - %s - %s' % (board_info.bName, config.branding),
                referer = web.ctx.env.get('HTTP_REFERER', default_referer))

    @util.error_catcher
    @util.session_helper
    @util.confirmation_helper
    def modify_post(self, mobile, board_name, board_id, current_uid = -1):
        board_info = board.get_board_info(board_id)
        if not acl.is_allowed('board', board_id, current_uid, 'modify'):
            return render[mobile].error(error_message=_('NO_PERMISSION'), help_context='error')
        comment, write_by_other = 0, 0 # XXX: DB 스키마를 BOOLEAN으로 바꿔야 함
        if web.input().commentable.strip() == 'yes':
            comment = 1
        if web.input().writable.strip() == 'yes':
            write_by_other = 1
        owner_uid = user._get_uid_from_username(web.input().owner)
        if owner_uid < 0:
            return render[mobile].error(error_message=_('NO_SUCH_USER_FOR_BOARD_ADMIN'), help_context='error')

        board_info = dict(path = web.input().path, name = web.input().name,
                owner = owner_uid, board_type = web.input().type,
                can_comment = comment, can_write_by_other = write_by_other,
                description = web.input().description,
                cover = web.input().information)
        result = board.edit_board(current_uid, board_id, board_info)
        if result[0] == False:
            return render[mobile].error(error_message = result[1], help_context='error')
        else:
            if mobile:
                raise web.seeother('/m%s/+summary' % result[1])
            else:
                raise web.seeother('%s/+summary' % result[1])

    @util.error_catcher
    @util.session_helper
    def delete_get(self, mobile, board_name, board_id, current_uid = -1):
        default_referer = posixpath.join('/', board_name, '+summary')
        if mobile:
            default_referer = posixpath.join('/m', default_referer)
        action = posixpath.join('/', board_name, '+delete')
        if mobile:
            action = posixpath.join('/m', action)
        return render[mobile].question(question=u'이 게시판을 삭제하시겠습니까?',
                board_path = board_name, board_desc = u'확인', title=u'확인',
                action=action,
                referer=web.ctx.env.get('HTTP_REFERER', default_referer))

    @util.error_catcher
    @util.session_helper
    @util.confirmation_helper
    def delete_post(self, mobile, board_name, board_id, current_uid = -1):
        ret = board.delete_board(current_uid, board_id)
        if ret[0] == True:
            if mobile:
                raise web.seeother('/m%s' % (ret[1]))
            else:
                raise web.seeother('%s' % (ret[1]))
        else:
            return render[mobile].error(error_message = ret[1], help_context='error')

