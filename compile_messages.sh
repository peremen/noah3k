#!/bin/sh
LANGS="ko en"
for l in $LANGS
do
    msgfmt i18n/$l.po -o i18n/$l/LC_MESSAGES/messages.mo
done

