#!/bin/sh
LANGS="ko en"
pybabel extract -F babel.cfg . > i18n/messages.pot
for l in $LANGS
do
    msgmerge -U i18n/$l.po i18n/messages.pot
    msgfmt i18n/$l.po -o i18n/$l/LC_MESSAGES/message.mo
done

