#!/usr/bin/python
# -*- coding: utf-8 -*-

import datetime
import os, re
import random
import sys, traceback
import posixpath

import web
import board, article
import config
from config import render
import i18n
import bbcode
_ = i18n.custom_gettext

lang_map = { 'ko': u'한국어',
             'en': u'English',
             'ru': u'Русский', }

def session_helper(func):
    def _exec(*args, **kwargs):
        try:
            current_uid = web.ctx.session.uid
        except:
            raise web.seeother(link('/+login'))
            #raise web.unauthorized(render[mobile].error(error_message = _("NOT_LOGGED_IN"), help_context = 'error'))
        if current_uid < 1:
            web.ctx.session.uid = 0
            web.ctx.session.kill()
            raise web.internalerror(default_render.error(error_message = _("INVALID_UID"), help_context = 'error'))
        kwargs.update({'current_uid': current_uid})
        return func(*args, **kwargs)
    _exec.__name__ == func.__name__
    _exec.__doc__ == func.__doc__
    return _exec

def confirmation_helper(func):
    def _exec(*args, **kwargs):
        i = web.input()
        if i.has_key('ok'):
            return func(*args, **kwargs)
        else:
            raise web.seeother(i.referer)
    _exec.__name__ == func.__name__
    _exec.__doc__ == func.__doc__
    return _exec

def theme(func):
    def _exec(*args, **kwargs):
        arglist = [args[0]]
        theme = args[1]

        if theme is not None and theme.endswith('/'):
            theme = theme[:len(theme)-1]

        if theme is None or theme == '':
            web.config.theme = 'default'
        elif theme in config.render:
            web.config.theme = theme
        else:
            raise NameError('Invalid theme: ' + theme)

        for i in range(2, len(args)):
            arglist.append(args[i])

        return func(*tuple(arglist), **kwargs)
    return _exec

def error_catcher(func):
    def _exec(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (web.webapi.unauthorized, web.webapi._NotFound, web.webapi._InternalError, web.webapi.SeeOther): # 웹 프로그램의 오류. 대개 해결 가능.
            raise
        except Exception as e:
            current_ctx = web.ctx
            error_text = traceback.format_exc()
            store_error(current_ctx, error_text)
            raise web.internalerror(config.default_render.error(error_message = e,
                error_detail = error_text, help_context = 'error'))
    _exec.__name__ == func.__name__
    _exec.__doc__ == func.__doc__
    return _exec

def store_error(current_ctx, error_text):
    if not config.store_error_report:
        return
    today = datetime.datetime.today()
    filename = 'error_%s.txt' % today.strftime('%Y%m%d_%H%M%S')
    try:
        f = open(os.path.join(config.error_report_path, filename), 'w')
        f.write('Traceback:\n')
        f.write(error_text)
        f.write('\n')
        f.write('Context:\n')
        f.write(str(current_ctx))
        f.write('\n')
        f.close()
    except OSError:
        pass

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
    b = bbcode.parse
    try:
        return b(process_noah12k_quote(original))
    except:
        text = traceback.format_exc()
        #text = process_noah12k_quote(original)
        return text.replace(' ', '&nbsp;').replace('\n', '<br />\n')

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
        return _('INVALID_NOTICE_BOARD')
    for i in article.get_marked_article(board_id):
        articles.append(i)
    if len(articles) == 0:
        return _('NO_NOTICE')
    return articles[random.randint(0, len(articles)-1)].aContent


def lcode_to_name(lcode):
    return lang_map[lcode]

def get_lang_map():
    return lang_map

def traverse_board_path(path, theme=None):
    if path == '^root':
        path = '/'
    ret = ""
    id = board._get_board_id_from_path(path)
    while id != 1 and id > 0:
        i = board.get_board_info(id)
        if i.bType == 0:
            if theme:
                ret = '/<a class="dirlink" href="/%s%s">%s</a>' % (theme, i.bName, i.bName.split('/')[-1]) + ret
            else:
                ret = '/<a class="dirlink" href="%s">%s</a>' % (i.bName, i.bName.split('/')[-1]) + ret
        else:
            if theme:
                ret = '/<a class="boardlink" href="/%s%s">%s</a>' % (theme, i.bName, i.bName.split('/')[-1]) + ret
            else:
                ret = '/<a class="boardlink" href="%s">%s</a>' % (i.bName, i.bName.split('/')[-1]) + ret
        new_id = board.get_parent(id)
        if new_id == id:
            break
        id = new_id
#    ret = (u'<a class="dirlink" href="/">%s</a>' % _('Board')) + ret
    return ret

def get_type(path):
    if path == '^root':
        path = '/'
    id = board._get_board_id_from_path(path)
    if id < 0:
        return -1
    data = board.get_board_info(id)
    return data.bType

def choose_banner():
    banners = []
    try:
        f = open(config.banner_path, 'r')
        banners = f.readlines()
        f.close()
    except IOError:
        return ['default.png', '#']
    cumulative_list = []
    j = 0
    for b in banners:
        banners[j] = b.strip().split(' ')
        banners[j][2] = int(banners[j][2])
        if len(cumulative_list) == 0:
            cumulative_list.append(banners[j][2])
        else:
            cumulative_list.append(cumulative_list[-1] + banners[j][2])
        j = j + 1
    banner_id = random.randint(1, max(cumulative_list))
    j = 0
    ret = tuple()
    cond = False
    for i in cumulative_list:
        if j == 0:
            cond = (banner_id <= i)
        else:
            cond = (cumulative_list[j-1] < banner_id) and (banner_id <= i)
        if cond:
            ret = tuple((banners[j][0], banners[j][1]))
            break
        else:
            j = j + 1
    return ret

#always starts with traling /
def link(url):
    if web.config.theme is not 'default':
        if url.startswith('/'):
            url = '/' + web.config.theme + url
        else:
            url = web.config.theme + '/' + url
    return url


def render():
    return config.render[web.config.theme]
