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

desktop_render = render_mako(
    directories = [os.path.join(os.path.dirname(__file__), 'templates/desktop/').replace('\\','/'),],
    input_encoding = 'utf-8', output_encoding = 'utf-8',
)

mobile_render = render_mako(
    directories = [os.path.join(os.path.dirname(__file__), 'templates/mobile/').replace('\\','/'),],
    input_encoding = 'utf-8', output_encoding = 'utf-8',
)

def session_helper(func):
    def _exec(*args, **kwargs):
        is_mobile = args[1]
        try:
            current_uid = web.ctx.session.uid
        except:
            raise web.unauthorized(desktop_render.error(lang="ko", error_message = u"NOT_LOGGED_IN"))
        if current_uid < 1:
            raise web.internalerror(desktop_render.error(lang="ko", error_message = u"INVALID_UID"))
        kwargs.update({'current_uid': current_uid})
        return func(*args, **kwargs)
    return _exec

def confirmation_helper(func):
    def _exec(*args, **kwargs):
        i = web.input()
        if i.has_key('ok'):
            return func(*args, **kwargs)
        else:
            raise web.seeother(i.referer)
    return _exec

