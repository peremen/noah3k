#!/usr/bin/python
# -*- coding: utf-8 -*-

import re

_tags = {"b": {"argc":1, "tmpl":"<b>%s</b>", "nest":True},
		"i": {"argc":1, "tmpl":"<i>%s</i>", "nest":True},
		"u": {"argc":1, "tmpl":"<u>%s</u>", "nest":True},
		"s": {"argc":1, "tmpl":"<s>%s</s>", "nest":True},
		"center": {"argc":1, "tmpl":"<center>%s</center>", "nest":True},

		"link": {"argc":2, "tmpl":"<a href=\"%s\">%s</a>", "nest":True},
		"img": {"argc":2, "tmpl":"<img src=\"%s\" alt=\"image\">%s</img>", "nest":True},
		"color": {"argc":2, "tmpl":"<span style=\"color:%s;\">%s</span>", "nest":True},
		"code": {"argc":2, "tmpl":"<pre type=\"%s\">%s</pre>", "nest":False},
		"quote": {"argc":2, "tmpl":"<b>%s</b><br/><blockquote>%s</blockquote>", "nest":True},
		};

def getRegexStart(tags):
	re_text = '\[('
	for tag in tags:
		re_text += '%s|' % tag
	re_text = re_text[:len(re_text)-1] + ')=?([^\]]*)]'
	return re.compile(re_text)

_re_url = re.compile(r"((https?):((//)|(\\\\))+[\w\d:#@%/;$()~_?\+-=\\\.&]*)", re.MULTILINE|re.UNICODE)
_re_start = getRegexStart(_tags);

def _parse_text(text):
	html = ''
	while True:
		ro = _re_url.search(text)
		if(ro == None):
			break
		html, text, url = html + text[:ro.start()], text[ro.end():], ro.groups()[0]
		html += _tags["link"]["tmpl"] % (url, url)
	return html + text

def _parse(text, tags):
	html = ''
	while True:
		ro = _re_start.search(text)
		if(ro == None):
			break
		tag, arg = ro.groups()[0], ro.groups()[1]
		if arg == None:
			arg = ''
		html, text = html + _parse_text(text[:ro.start()]), text[ro.end():]
		innerText, text = text.split('[/%s]' % tag, 1)
		if tags[tag]["nest"]:
			innerHtml = _parse(innerText, tags)
		else:
			innerHtml = innerText

		if tags[tag]["argc"] == 1:
			html += tags[tag]["tmpl"] % innerHtml
		else:
			html += tags[tag]["tmpl"] % (arg, innerHtml)
	return html + _parse_text(text)

def parse(text):
	text = text.replace('\n', '<br/>')
	return _parse(text, _tags);
