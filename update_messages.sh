#!/bin/sh
LANGS="ko en"
pybabel extract -F babel.cfg . > i18n/messages.pot
for l in $LANGS
do
    msgmerge -U i18n/$l.po i18n/messages.pot
done

