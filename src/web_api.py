#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import web
from cgi import parse_qs
import posixpath
import sys, traceback
from config import render
import i18n
_ = i18n.custom_gettext
import json
import board, user

def json_header(func):
    def _exec(*args, **kwargs):
        web.header('Content-Type', 'application/json')
        return func(*args, **kwargs)
    return _exec

class api:
    def GET(self):
        try:
            if web.ctx.query == '':
                qs = dict()
            else:
                qs = parse_qs(web.ctx.query[1:], keep_blank_values = True)
            print qs['action']
            return eval('self.%s' % (qs['action'][0]))(qs)
        except AttributeError:
            return self.api_help()

    def POST(self):
        json_data = web.data()

    @json_header
    def api_help(self):
        help_string = ['Specify action to query string. Both GET and POST are supported, Supported actions are:',
                {'check_duplicate_user': 'Checks specified ID exists at NOAH. argument: username, string, user id to check'}]
        return json.dumps(help_string)

    @json_header
    def check_duplicate_user(self, qs):
        username = qs['username'][0]
        if user._get_uid_from_username(username) > 0:
            return json.dumps([True])
        else:
            return json.dumps([False])


