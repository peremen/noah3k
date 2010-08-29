#!/usr/bin/python
# -*- coding: utf-8 -*-

import web
from web.contrib.template import render_mako
import config
import os, re
import postmarkup
import sys, traceback

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

def validate_username(name):
    match = re.search(r'\W+', name)
    if match == None:
        return True
    else:
        return False

def validate_boardname(name):
    match = re.search(r'[^\w/]+', name)
    if match == None:
        return True
    else:
        return False

def format(original):
    b = postmarkup.create(annotate_links = False)
    return b(process_noah12k_quote(original))
    #return b(original)

def process_noah12k_quote(original):
    # noah 1k/2k의 인용구를 BBCode 형태로 바꿔 줌.
    # 반드시 HTML로 변환하기 전에 호출해야 함.
    header = [u'"에서: "',u'"에서 : ']
    lines = original.split('\n')
    levels = []
    ret = u''
    for i in range(0, len(lines)):
        last_q = lines[i].rfind('>')
        lines[i] = lines[i][last_q + 1:]
        if last_q < 0:
            last_q = 0
        else:
            last_q = last_q / 2 + 1
        levels.append(last_q)
    assert(len(levels) == len(lines))

    trimBegin = False
    for i in range(0, len(lines)):
        if i==0 or (levels[i-1] < levels[i]):
            trimBegin = True
        if trimBegin and lines[i].strip() == '':
            lines[i] = ''
        else:
            trimBegin = False

    trimEnd = False
    for i in range(len(lines)-1, -1, -1):
        if i==len(levels)-1 or levels[i] > levels[i+1]:
            trimEnd = True
        if trimEnd and lines[i] == '' and lines[i].strip() == '':
            lines[i] = ''
        else:
            trimEnd = False

    for i in range(0, len(lines)):
        prevLevel = 0
        if i>0:
            prevLevel = levels[i-1]
        while levels[i] != prevLevel:
            if levels[i] > prevLevel:
                ret += '[quote]\n'
                prevLevel = prevLevel + 1
            if levels[i] < prevLevel:
                ret +='[/quote]\n'
                prevLevel = prevLevel - 1
        if lines[i] != '':
            if lines[i].find(header[0]) > 0 or lines[i].find(header[1]) > 0:
                ret +=lines[i]
            else:
                ret +=lines[i]
        if i < len(lines)-1:
            ret +='\n'
    return ret

