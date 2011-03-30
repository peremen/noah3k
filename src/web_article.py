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
import attachment
import acl
from config import render
import i18n
_ = i18n.custom_gettext

class article_actions:
    def GET(self, theme, board_name, action, article_id):
        return self.caller(theme, board_name, action, article_id, 'get')

    def POST(self, theme, board_name, action, article_id):
        return self.caller(theme, board_name, action, article_id, 'post')

    def caller(self, theme, board_name, action, article_id, method):
        if not theme:
            theme = ''
        if board_name[0] == '/':
            board_name = board_name[1:]
        if not render.has_key(theme):
            board_name = posixpath.join(theme, board_name)
            theme = 'default'
        board_id = board._get_board_id_from_path(board_name)
        if board_id < 0:
            raise web.notfound(render[theme].error(error_message = _('INVALID_BOARD'), help_context='error'))
        try:
            return eval('self.%s_%s' % (action, method))(theme, board_name, board_id, int(article_id))
        except AttributeError:
            raise web.notfound(render[theme].error(error_message = _('INVALID_ACTION'), help_context='error'))

    @util.error_catcher
    def read_get(self, theme, board_name, board_id, article_id):
        board_info = board.get_board_info(board_id)
        board_desc = board_info.bDescription
        a = article.get_article(board_id, article_id)
        comment = article.get_comment(article_id)

        #새글읽기 처리
        if web.ctx.session.has_key('uid'):
            uSerial = web.ctx.session.uid
            user.read_article(uSerial, article_id) 

        read_articles = web.cookies().get('read_articles')
        if read_articles:
            read_articles = [int(i) for i in read_articles.split(';')]
            if article_id not in read_articles:
                article.increase_read_count(article_id)
                read_articles.append(article_id)
        else:
            article.increase_read_count(article_id)
            read_articles = [article_id]
        read_articles.sort()
        read_articles = ';'.join(['%s' % i for i in read_articles])
        web.setcookie('read_articles', read_articles, 3600)

        prev_id = -1
        next_id = -1

        if not a:
            raise web.notfound(render[theme].error(error_message = _('NO_SUCH_ARTICLE'), help_context='error'))
        if a.aIndex > 1:
            prev_id = article.get_article_id_by_index(board_id, a.aIndex - 1)
        if a.aIndex < article._get_article_count(board_id):
            next_id = article.get_article_id_by_index(board_id, a.aIndex + 1)
        page_no = article.get_page_by_article_id(board_id, article_id, config.page_size)
        uploads = attachment.get_attachment(article_id)
        thumbs = attachment.get_thumbnail(article_id, theme)

        return render[theme].read_article(article = a,
            title = u"%s - %s" % (a.aIndex, a.aTitle),
            board_path = board_name, board_desc = board_desc,
            comments = comment, page_no = page_no,
            prev_id = prev_id, next_id = next_id, feed = True,
            attachment = uploads, thumbnail = thumbs,
            help_context = 'read_article')

    @util.error_catcher
    @util.session_helper
    def reply_get(self, theme, board_name, board_id, article_id, current_uid = -1):
        if not acl.is_allowed('board', board_id, current_uid, 'write'):
            return render[theme].error(error_message = _('NO_PERMISSION'), help_context='error')
        board_info = board.get_board_info(board_id)
        board_desc = board_info.bDescription
        user_info = user.get_user(current_uid)[1]
        article_ = article.get_article(board_id, article_id)
        quote_text = _('From %s\'s Article %s:') % (user._get_username_from_uid(article_.uSerial), util.remove_bracket(article_.aTitle))
        body = '\n\n\n[quote=%s]%s\n[/quote]\n\n%s' % (quote_text, article_.aContent, user_info.uSig)
        return render[theme].editor(title = _('Reply - /%s') % board_name,
                action='reply/%s' % article_id, action_name = _('Reply to the article'),
                board_path = board_name, board_desc = board_desc,
                body = body, article_title = article_.aTitle,
                help_context = 'editor')

    @util.error_catcher
    @util.session_helper
    def reply_post(self, theme, board_name, board_id, article_id, current_uid = -1):
        if not acl.is_allowed('board', board_id, current_uid, 'write'):
            return render[theme].error(error_message = _('NO_PERMISSION'), help_context = 'error')
        reply = dict(title = web.input().title, body = web.input().content)
        board_info = board.get_board_info(board_id)
        ret = article.reply_article(current_uid, board_id, article_id, reply)
        if ret[0] == True:
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
    @util.session_helper
    def modify_get(self, theme, board_name, board_id, article_id, current_uid = -1):
        if not acl.is_allowed('article', article_id, current_uid, 'modify'):
            return render[theme].error(error_message = _('NO_PERMISSION'), help_context='error')
        board_info = board.get_board_info(board_id)
        board_desc = board_info.bDescription
        article_ = article.get_article(board_id, article_id)
        uploads = attachment.get_attachment(article_id)
        return render[theme].editor(title = _('Modify - /%s')% board_name,
                action='modify/%s' % article_id, action_name = _('Modify article'),
                board_path = board_name, board_desc = board_desc,
                article_title = article_.aTitle, body = article_.aContent,
                attachment = uploads, help_context = 'editor')

    @util.error_catcher
    @util.session_helper
    def modify_post(self, theme, board_name, board_id, article_id, current_uid = -1):
        if not acl.is_allowed('article', article_id, current_uid, 'modify'):
            return render[theme].error(error_message = _('NO_PERMISSION'), help_context='error')
        data = web.input(new_attachment= {})
        fs = web.ctx.get('_fieldstorage')
        try:
            if fs.has_key('delete'):
                to_delete = fs['delete']
                if type(to_delete) == list:
                    for f in to_delete:
                        attachment.remove_attachment(article_id, f.value)
                else:
                    try:
                        attachment.remove_attachment(article_id, to_delete.value)
                    except:
                        pass
            if fs.has_key('new_attachment'):
                new_attachment = fs['new_attachment']
                if type(new_attachment) == list:
                    for f in new_attachment:
                        attachment.add_attachment(article_id, f.filename, f.value)
                else:
                    try:
                        attachment.add_attachment(article_id, new_attachment.filename, new_attachment.value)
                    except:
                        pass
        except:
            pass

        mark_as_unreaded = web.input().has_key('unreaded')

        a = dict(title = data.title, body = data.content)
        board_info = board.get_board_info(board_id)
        ret = article.modify_article(current_uid, board_id, article_id, a, mark_as_unreaded)
        if ret[0] == True:
            if theme == 'default':
                raise web.seeother('/%s/+read/%s' % (board_name, ret[1]))
            else:
                raise web.seeother('/%s/%s/+read/%s' % (theme, board_name, ret[1]))
        else:
            return render[theme].error(error_message = ret[1], help_context='error')

    @util.error_catcher
    @util.session_helper
    def delete_get(self, theme, board_name, board_id, article_id, current_uid = -1):
        if not acl.is_allowed('article', article_id, current_uid, 'delete'):
            return render[theme].error(error_message = _('NO_PERMISSION'), help_context='error')
        if theme == 'default':
            default_referer = os.path.join('/', board_name, '+read', str(article_id))
            action=os.path.join('/', board_name, '+delete', str(article_id))
        else:
            default_referer = os.path.join('/', theme, board_name, '+read', str(article_id))
            action=os.path.join('/', theme, board_name, '+delete', str(article_id))
        return render[theme].question(question=_('Do you want to delete the article?'),
                board_path = board_name, board_desc = _('Confirmation'), title=_('Confirmation'),
                action = action,
                referer=web.ctx.env.get('HTTP_REFERER', default_referer))

    @util.error_catcher
    @util.confirmation_helper
    @util.session_helper
    def delete_post(self, theme, board_name, board_id, article_id, current_uid = -1):
        if not acl.is_allowed('article', article_id, current_uid, 'delete'):
            return render[theme].error(error_message = _('NO_PERMISSION'), help_context='error')
        ret = article.delete_article(current_uid, article_id)
        attachment.remove_all_attachment(article_id)
        if ret[0] == True:
            if theme == 'default':
                raise web.seeother('/%s' % (board_name))
            else:
                raise web.seeother('/%s/%s' % (theme, board_name))
        else:
            return render[theme].error(error_message = ret[1], help_context='error')

    @util.error_catcher
    @util.session_helper
    def comment_post(self, theme, board_name, board_id, article_id, current_uid = -1):
        if not acl.is_allowed('board', board_id, current_uid, 'comment'):
            return render[theme].error(error_message=_('NO_PERMISSION'), help_context='error')
        comment = web.input().comment
        board_info = board.get_board_info(board_id)
        ret = article.write_comment(current_uid, board_id, article_id, comment)
        if ret[0] == True:
            user.update_unreaded_articles_board(current_uid, board_id)
            user.read_article(current_uid, ret[1])

            if theme == 'default':
                raise web.seeother('/%s/+read/%s' % (board_name, article_id))
            else:
                raise web.seeother('/%s/%s/+read/%s' % (theme, board_name, article_id))
        else:
            return render[theme].error(error_message = ret[1], help_context='error')

    @util.error_catcher
    @util.session_helper
    def comment_delete_get(self, theme, board_name, board_id, comment_id, current_uid = -1):
        ret = article.delete_comment(current_uid, comment_id)
        if ret[0] == True:
            if theme == 'default':
                raise web.seeother('/%s/+read/%s' % (board_name, ret[1]))
            else:
                raise web.seeother('/%s/%s/+read/%s' % (theme, board_name, ret[1]))
        else:
            return render[theme].error(error_message = ret[1], help_context='error')

    @util.error_catcher
    @util.session_helper
    def mark_get(self, theme, board_name, board_id, article_id, current_uid = -1):
        if not acl.is_allowed('board', board_id, current_uid, 'mark'):
            return render[theme].error(error_message=_('NO_PERMISSION'), help_context='error')
        article.mark_article(article_id)
        if theme == 'default':
            raise web.seeother('/%s/+read/%s' % (board_name, article_id))
        else:
            raise web.seeother('/%s/%s/+read/%s' % (theme, board_name, article_id))

    @util.error_catcher
    @util.session_helper
    def unmark_get(self, theme, board_name, board_id, article_id, current_uid = -1):
        if not acl.is_allowed('board', board_id, current_uid, 'mark'):
            return render[theme].error(error_message=_('NO_PERMISSION'), help_context='error')
        article.unmark_article(article_id)
        if theme == 'default':
            raise web.seeother('/%s/+read/%s' % (board_name, article_id))
        else:
            raise web.seeother('/%s/%s/+read/%s' % (theme, board_name, article_id))

