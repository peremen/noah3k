#!/usr/bin/python
# -*- coding: utf-8 -*-

import datetime
import os, re
import random
import sys, traceback

import web
from web.contrib.template import render_mako
import postmarkup
import board, article
import config

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

def error_catcher(func):
    def _exec(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (web.webapi._NotFound, web.webapi._InternalError, web.webapi.SeeOther): # 웹 프로그램의 오류. 대개 해결 가능.
            raise
        except Exception as e:
            current_ctx = web.ctx
            error_text = traceback.format_exc()
            store_error(current_ctx, error_text)
            raise web.internalerror(desktop_render.error(lang="ko", error_message = e,
                error_detail = error_text))
    return _exec

def store_error(current_ctx, error_text):
    if not config.store_error_report:
        return
    today = datetime.datetime.today()
    filename = 'error_%s.txt' % today.strftime('%Y%m%d_%H%M%S')
    f = open(os.path.join(config.error_report_path, filename), 'w')
    f.write('Traceback:\n')
    f.write(error_text)
    f.write('\n')
    f.write('Context:\n')
    f.write(str(current_ctx))
    f.write('\n')
    f.close()

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

def remove_bracket(original):
    # BBCode 파서 안에 [/]이 들어가면 파서가 헷갈리므로
    # 글 제목에 들어간 [/]을 (/)으로 바꿈.
    return original.replace('[', '(').replace(']', ')')

def process_noah12k_quote(original):
    # noah 1k/2k의 인용구를 BBCode 형태로 바꿔 줌.
    # 반드시 HTML로 변환하기 전에 호출해야 함.
    indent = '> '
    header = [u'"에서: ',u'"에서 : ']
    lines = original.split('\n')
    levels = []
    ret = u''
    for i in range(0, len(lines)):
        last_q = 0
        while lines[i].find(indent) == 0:
            last_q = last_q + 1
            lines[i] = lines[i][len(indent):]
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
                if lines[i-1].endswith(header[0]) or lines[i-1].endswith(header[1]):
                    ret += '[quote=%s]\n' % remove_bracket(lines[i-1])
                else:
                    ret += '[quote]\n'
                prevLevel = prevLevel + 1
            if levels[i] < prevLevel:
                ret +='[/quote]\n'
                prevLevel = prevLevel - 1
        if lines[i] != '':
            if not( lines[i].endswith(header[0]) or lines[i].endswith(header[1])):
                ret +=lines[i]
            else:
                continue
        if i < len(lines)-1:
            ret +='\n'
    return ret


def get_login_notice(notice_board = '/noah/welcome'):
    # /noah/welcome에서 공지 표시된 글 중 아무거나 하나를 랜덤으로 돌려 줌.
    # 공지 표시된 글이 없는 경우 '공지가 없습니다.'를 돌려 줌.
    articles = []
    board_id = board._get_board_id_from_path(notice_board)
    if board_id < 0:
        return 'INVALID_NOTICE_BOARD'
    for i in article.get_marked_article(board_id):
        articles.append(i)
    if len(articles) == 0:
        return 'NO_NOTICE'
    return articles[random.randint(0, len(articles)-1)].aContent

