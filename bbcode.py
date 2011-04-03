#!/usr/bin/python
# -*- coding: utf-8 -*-

import re
import config

if "tmpl_video_width" not in dir(config):
    config.tmpl_video_width = 640
if "tmpl_video_height" not in dir(config):
    config.tmpl_video_height = 480

_re_url = re.compile(r"((https?):((//)|(\\\\))+[^\s]*)", re.MULTILINE|re.UNICODE)
_re_list = re.compile('\[\*\]([^[]*)')

def _fmt(tmpl):
    if(tmpl.count("%s") == 1):
        return lambda args: tmpl % args[1];
    return lambda args: tmpl % args;

def _fmt_video(args):
    tpl = (config.tmpl_video_width, config.tmpl_video_height, args[1])
    if(args[0] == "youtube"):
        url = '<iframe title="YouTube video player" class="youtube-player" type="text/html" width="%s" height="%s" src="http://www.youtube.com/embed/%s?rel=0" frameborder="0"></iframe>' % tpl
    elif(args[0] == "vimeo"):
        url = '<iframe width="%s" height="%s" src="http://player.vimeo.com/video/%s" frameborder="0"></iframe>' % tpl
    return url

def _fmt_list(args):
    style = "list-style-type:circle"
    if args[0] == "1":
        style = 'list-style-type:decimal'
    elif args[0] == 'a':
        style = 'list-style-type:lower-alpha'
    elif args[0] == 'A':
        style = 'list-style-type:upper-alpha'

    html = '<ol style="%s">' % style

    idx = args[1].find('[*]')
    html, text = html + args[1][:idx], args[1][idx+3:]
    text = text.replace('<br/>', '')
    while True:
        if len(text) == 0:
            break;
        html += '<li>';
        idx = text.find('[*]')

        if(idx == -1):
            innerText = text;
            text = '';
        else:
            innerText, text = text[:idx], text[idx+3:]
            
        html += _parse(innerText, _tags)
        html += '</li>';
        
    html += '</ol>'
    return html

def _fmt_code(args):
    if args[0]:
        html = "<pre class=\"brush: %s\">%s</pre>" % (args[0], args[1])
    else:
        html = "<pre class=\"brush: plain\">%s</pre>" % (args[1])
    return html

_tags = {"b": {"tmpl":_fmt("<b>%s</b>"), "nest":True},
        "i": {"tmpl":_fmt("<i>%s</i>"), "nest":True},
        "u": {"tmpl":_fmt("<u>%s</u>"), "nest":True},
        "s": {"tmpl":_fmt("<s>%s</s>"), "nest":True},
        "center": {"tmpl":_fmt("<center>%s</center>"), "nest":True},
        "size": {"tmpl":_fmt('<font size="%s">%s</font>'), "nest":True},

        "link": {"tmpl":_fmt("<a href=\"%s\">%s</a>"), "nest":True},
        "img": {"tmpl":_fmt("<img src=\"%s\" alt=\"%s\"/>"), "nest":False},
        "color": {"tmpl":_fmt("<span style=\"color:%s;\">%s</span>"), "nest":True},
        "code": {"tmpl":_fmt_code, "nest":False},
        "quote": {"tmpl":_fmt("<b>%s</b><br/><blockquote>%s</blockquote>"), "nest":True},

        "video": {"tmpl":_fmt_video, "nest":False},
        "list": {"tmpl":_fmt_list, "nest":False},

        "latex": {"tmpl":_fmt('<img src="http://l.wordpress.com/latex.php?bg=ffffff&fg=000000&latex=%s" alt="latex math"/>'), "nest":False},
        };

def getRegex(tags):
    re_text = '\[(/)?('
    for tag in tags:
        re_text += '%s|' % tag
    re_text = re_text[:len(re_text)-1] + ')=?([^\]]*)]'
    return re.compile(re_text)

_re = getRegex(_tags);

def _escape(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>');

def _parse_url(text):
    html = ''
    while True:
        ro = _re_url.search(text)
        if(ro == None):
            break
        html, text, url = html + text[:ro.start()], text[ro.end():], ro.groups()[0]
        html += _tags["link"]["tmpl"]((url, url))
    return html + text

def _fold(l):
    return reduce(lambda a, b: a + b, l)

def _parse(text, tags):
    html = ''
    root = []
    l = root
    stack = []
    stack.append(('root', '', root))

    while True:
        ro = _re.search(text)
        if(ro == None):
            break
        end, tag, arg = ro.groups()

        if arg == None:
            arg = ''

        t = _escape(text[:ro.start()])
        l.append(_parse_url(t))

        text = text[ro.end():]

        if end == None:
            l = []
            stack.append((tag, arg, l))
        elif stack[len(stack)-1][0] == tag:
            e = stack.pop()
            l = stack[len(stack)-1][2]
            l.append(tags[e[0]]["tmpl"]((e[1], _fold(e[2]))))

    root.append(_parse_url(_escape(text)))
    return _fold(root);

def parse(text):
    return _parse(text, _tags)
