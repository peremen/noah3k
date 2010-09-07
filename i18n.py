#!/usr/bin/python
# -*- coding: utf-8 -*-

import gettext
import config
import web

translations = web.storage()

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

def custom_gettext(string):
    translation = load_translations('ko') #web.ctx.session.get('lang'))
    if translation is None:
        return unicode(string)
    return translation.ugettext(string)

