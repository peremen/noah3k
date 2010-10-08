#!/usr/bin/python
# -*- coding: utf-8 -*-

import gettext
import config
import web

translations = web.storage()
supported_languages = ['ko', 'en',]
def get_translations(lang='ko'):
    if translations.has_key(lang):
        translation = translations[lang]
    elif lang is None:
        translation = gettext.NullTranslations()
    else:
        try:
            translation = gettext.translation('messages',
                    config.i18n_path, languages=[lang],)
        except IOError:
            translation = gettext.NullTranslations()
    return translation

def load_translations(lang):
    lang = str(lang)
    translation = translations.get(lang)
    if translation is None:
        translation = get_translations(lang)
        translations[lang] = translation

        for lk in translations.keys():
            if lk != lang:
                del translations[lk]
    return translation

def get_language():
    # 로그인한 경우에는 사용자가 선호하는 언어로 변경.
    # 로그인하지 않은 경우에는 Accept-Language 헤더의 가장 높은 q 언어를 사용.
    # 둘 다 해당하지 않으면 한국어.
    lang_header = ''
    lang = web.ctx.session.get('lang')
    if lang:
        return lang
    try:
        lang_header = web.ctx.environ.get('HTTP_ACCEPT_LANGUAGE')
        lang_header = [x.split(';q=') for x in lang_header.split(',')]
        for x in lang_header:
            if len(x) == 1:
                x.append(1)
            else:
                x[1] = float(x[1])
        lang_header.sort(key = lambda x: x[1], reverse = True)
        ret = lang_header[0][0]
        if ret in supported_languages:
            return ret
        if ret[0:ret.find('-')] in supported_languages:
            return ret[0:ret.find('-')]
        return lang
    except:
        pass
    return 'ko'

def custom_gettext(string):
    translation = load_translations(get_language())
    if translation is None:
        return unicode(string)
    return translation.ugettext(string)

