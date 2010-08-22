#!/usr/bin/python
# -*- coding: utf-8 -*-

import config
import web

import user
import posixpath

"""
첨부 파일 클래스. 데이터베이스 및 디스크에 저장된 첨부 파일에 접근한다.
"""


if web.config.get('_database') is None:
    db = web.database(dbn=config.db_type, user=config.db_user,
            pw = config.db_password, db = config.db_name,
            host=config.db_host, port=int(config.db_port))
    web.config._database = db
else:
    db = web.config._database

prefix = web.config.attachment_path

 
def get_attachment(article_id):
    # 데이터베이스: Supplement
    # sSerial: 파일 ID
    # aSerial: article_id
    # sFilename: 첨부파일 이름
    val = dict(article_id = int(article_id))
    result = db.select('Supplement', val, where='aSerial = $article_id')
    return result
