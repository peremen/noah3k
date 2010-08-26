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

def session_helper(self, mobile):
    try:
        current_uid = web.ctx.session.uid
    except:
        raise web.unauthorized(desktop_render.error(lang="ko", error_message = u"NOT_LOGGED_IN"))
    if current_uid < 1:
        raise web.internalerror(desktop_render.error(lang="ko", error_message = u"INVALID_UID"))
    return current_uid

def confirmation_helper(func):
    def _exec(*args, **kwargs):
        i = web.input()
        if i.has_key('ok'):
            return func(*args, **kwargs)
        else:
            raise web.seeother(i.referer)
    return _exec

