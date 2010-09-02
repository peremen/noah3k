#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import web
import board
from web.contrib.template import render_mako
from cgi import parse_qs
import posixpath
import sys, traceback

desktop_render = render_mako(
    directories = [os.path.join(os.path.dirname(__file__), 'templates/desktop/').replace('\\','/'),],
    input_encoding = 'utf-8', output_encoding = 'utf-8',
)

class noah2k_support:
    def GET(self, jsp_name):
        try:
            if web.ctx.query == '':
                qs = dict()
            else:
                qs = parse_qs(web.ctx.query[1:], keep_blank_values = True)
            return eval('self.%s' % (jsp_name))(qs)
        except AttributeError:
            raise web.notfound(desktop_render.error(lang='ko', error_message = 'INVALID_NOAH2K_ACTION'))

    def list(self, query_string):
        board_id = -1
        if query_string.has_key('board'):
            board_id = int(query_string['board'][0])
        else:
            raise web.notfound(desktop_render.error(lang='ko', error_message = 'NO_BOARD_SPECIFIED'))
        if query_string.has_key('page'):
            page_no = int(query_string['page'][0])
        else:
            page_no = 0

        path = board._get_path_from_board_id(board_id)
        if path == '':
            raise web.notfound(desktop_render.error(lang='ko', error_message = 'NO_SUCH_BOARD'))

        if page_no > 0:
            raise web.redirect('%s?page=%s' % (path, page_no))
        else:
            raise web.redirect('%s' % path)

    def view(self, query_string):
        board_id = -1
        article_id = -1
        if query_string.has_key('board'):
            board_id = int(query_string['board'][0])
        else:
            raise web.notfound(desktop_render.error(lang='ko', error_message = 'NO_BOARD_SPECIFIED'))
        if query_string.has_key('serial'):
            article_id = query_string['serial'][0]
        else:
            raise web.notfound(desktop_render.error(lang='ko', error_message = 'NO_ARTICLE_SPECIFIED'))
        path = board._get_path_from_board_id(board_id)
        if path == '':
            raise web.notfound(desktop_render.error(lang='ko', error_message = 'NO_SUCH_BOARD'))

        raise web.redirect(posixpath.join(path, '+read', article_id))

    def select(self, query_string):
        board_id = -1
        if query_string.has_key('board'):
            board_id = int(query_string['board'][0])
        else:
            raise web.redirect('/*')
        path = board._get_path_from_board_id(board_id)
        if path == '':
            raise web.notfound(desktop_render.error(lang='ko', error_message = 'NO_SUCH_BOARD'))

        raise web.redirect(posixpath.join(path, '*'))

    def feed(self, query_string):
        board_id = -1
        if query_string.has_key('board'):
            board_id = int(query_string['board'][0])
        else:
            raise web.notfound(desktop_render.error(lang='ko', error_message = 'NO_ARTICLE_SPECIFIED'))
        feed_size = 20
        if query_string.has_key('numentries'):
            feed_size = int(query_string['numentries'][0])
        feed_type = 'atom'
        if query_string.has_key('rss'):
            feed_type = 'rss'
        path = board._get_path_from_board_id(board_id)
        if path == '':
            raise web.notfound(desktop_render.error(lang='ko', error_message = 'NO_SUCH_BOARD'))

        raise web.redirect(posixpath.join(path, '+%s?size=%s' % (feed_type, numentries)))

    def download(self, query_string):
        attachment = -1
        if query_string.has_key('serial'):
            board_id = int(query_string['serial'][0])
        else:
            raise web.notfound(desktop_render.error(lang='ko', error_message = 'NO_ATTACHMENT_SPECIFIED'))
        return # TODO: 첨부 파일 URL scheme 정할 것

    def index(self, query_string):
        raise web.redirect('/')
