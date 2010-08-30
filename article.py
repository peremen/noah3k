#!/usr/bin/python
# -*- coding: utf-8 -*-

import config
import web

import user
import posixpath

"""
글 모듈. 글을 읽어오기 위하여 필요한 일부 게시판 기능과 글 및 댓글에 접근한다.
"""

if web.config.get('_database') is None:
    db = web.database(dbn=config.db_type, user=config.db_user,
            pw = config.db_password, db = config.db_name,
            host=config.db_host, port=int(config.db_port))
    web.config._database = db
else:
    db = web.config._database

def _get_article_count( board_id):
    val = dict(board_id = board_id)
    result = db.query('SELECT COUNT(*) AS article_count FROM Articles WHERE bSerial=$board_id', val);
    return result[0].article_count

def _get_total_page_count(board_id, page_size):
    total_article = _get_article_count(board_id)
    return  (total_article + page_size -1) / page_size

def get_article_list(board_id, page_size, page_number):
    total_article = _get_article_count(board_id)
    last_page = _get_total_page_count(board_id, page_size)
    if not (page_number >= 1 and page_number <= last_page):
        return []
    end_index = total_article - ((total_article + page_size - 1)/page_size - page_number) * page_size
    if(end_index > total_article):
        end_index = total_article
    begin_index = end_index - page_size + 1
    if(begin_index < 1):
        end_index += (1-begin_index)
        begin_index = 1
        if(end_index > total_article):
            end_index = total_article
    val = dict(board_id = board_id, begin_index = begin_index, end_index = end_index)
    result = db.select('Articles', val, where='bSerial = $board_id AND aIndex >= $begin_index AND aIndex <= $end_index',
            order = 'aIndex ASC')
    return result

def get_title(article_id):
    val = dict(article_id = int(article_id))
    result = db.select('Articles', val, where='aSerial = $article_id')
    try:
        retvalue = result[0]
    except:
        return None
    else:
        return retvalue.aTitle

def get_article_id_by_index(board_id, index):
    # 글 번호와 article_id(DB: aSerial) 매핑.
    # 없거나 오류가 난 경우 -1 돌려줌.
    val = dict(board_id = board_id, index = index)
    result = db.select('Articles', val, what='aSerial', where='bSerial = $board_id AND aIndex = $index')
    try:
        retvalue = result[0].aSerial
    except:
        return -1
    return retvalue

def get_page_by_article_id(board_id, article_id, page_size):
    article_count = _get_article_count(board_id)
    page_count = _get_total_page_count(board_id, page_size)
    if article_count < 0:
        return -1
    result = db.select('Articles', locals(), what='aIndex', where = 'bSerial = $board_id AND aSerial = $article_id')
    index = -1
    try:
        index = result[0].aIndex
    except:
        return -1
    return page_count - (article_count - index) / page_size

def get_article(board_id, article_id):
    val = dict(board_id = board_id, article_id = int(article_id))
    result = db.select('Articles', val, where='bSerial = $board_id AND aSerial = $article_id')
    try:
        retvalue = result[0]
    except:
        return None
    else:
        return retvalue

def write_article(uid, board_id, article):
    current_user = user.get_user(uid)
    if current_user[0] == False:
        return (False, 'NO_SUCH_USER')
    current_user = current_user[1]
    # check_acl(uid, board_id, 'WRITE')
    # if not acl: return (False, 'ACL_VIOLATION')
    if(article['title'].strip() == ""):
        return (False, 'EMPTY_TITLE')

    if(article['body'].strip() == ""):
        return (False, 'EMPTY_BODY')

    val = dict(board_id = board_id)
    result = db.select('Boards', val, where='bSerial = $board_id', what='bType, bWrite')
    board_info = None
    try:
        board_info = result[0]
    except:
        return (False, 'NO_SUCH_BOARD')
    if board_info.bType == 0:
        return (False, 'FOLDER')

    index = _get_article_count(board_id) + 1

    val = dict(index = index)
    ret = db.insert('Articles', bSerial = board_id, aIndex = index,
            aTitle = article['title'], aContent = article['body'],
            aId = current_user.uId, aNick = current_user.uNick, 
            aDatetime = web.SQLLiteral("NOW()"), uSerial = uid)

    val = dict(index = index)
    ret = db.update('Articles', vars = val, where = 'aIndex = $index',
            aRoot = web.SQLLiteral("aSerial"), _test = True)

    val = dict(uid = uid)
    ret = db.update('Users', vars = val, where='uSerial = $uid',
        uNumPost = web.SQLLiteral('uNumPost + 1'))

    val = dict(index = index, board_id = board_id)
    ret = db.select('Articles', val, where = 'bSerial = $board_id AND aIndex = $index',
            what = 'aSerial')
    ret = ret[0].aSerial

    return (True, ret)

def modify_article(uid, board_id, article_id, article):
    current_user = user.get_user(uid)
    if current_user[0] == False:
        return (False, 'NO_SUCH_USER')
    current_user = current_user[1]
    # check_acl(uid, board_id, 'MODIFY')
    # if not acl: return (False, 'ACL_VIOLATION')
    if(article['title'].strip() == ""):
        return (False, 'EMPTY_TITLE')

    if(article['body'].strip() == ""):
        return (False, 'EMPTY_BODY')

    val = dict(article_id = article_id)
    result = db.select('Articles', val, where='aSerial = $article_id',
            what='uSerial')
    article_info = None
    try:
        article_info = result[0]
    except:
        return (False, 'NO_SUCH_ARTICLE')
    if article_info.uSerial != uid:
        return (False, 'ACL_VIOLATION')

    val = dict(article_id = article_id, title = article['title'], body = article['body'])
    ret = db.update('Articles', vars = val, where = 'aSerial = $article_id',
            aTitle = article['title'], aContent = article['body'],
            aEditedDatetime = web.SQLLiteral('NOW()'))

    return (True, article_id)

def delete_article(uid, article_id):
    current_user = user.get_user(uid)
    if current_user[0] == False:
        return (False, 'NO_SUCH_USER')
    current_user = current_user[1]
    # check_acl(uid, board_id, 'MODIFY')
    # if not acl: return (False, 'ACL_VIOLATION')

    article_id = int(article_id)
    val = dict(article_id = article_id)
    result = db.select('Articles', val, where='aSerial = $article_id',
            what='uSerial, bSerial, aIndex')
    article_info = None
    try:
        article_info = result[0]
    except:
        return (False, 'NO_SUCH_ARTICLE')

    if article_info.uSerial != uid:
        return (False, 'ACL_VIOLATION')

    try:
        val = dict(article_id = article_id, board_id = article_info.bSerial,
                article_index = article_info.aIndex)
        result = db.query('SELECT COUNT(*) AS reply_count FROM Articles WHERE bSerial = $board_id AND aIndex = $article_index + 1 AND aParent = $article_id', val)
        reply_count = result[0].reply_count
        if reply_count > 0:
            return (False, 'HAS_REPLY')

        ret = db.delete('Articles', vars = val, where = 'aSerial = $article_id')
        ret = db.delete('Comments', vars=val, where='aSerial = $article_id')
        ret = db.update('Articles', vars = val, where='bSerial = $board_id AND aIndex > $article_index',
                aIndex = web.SQLLiteral('aIndex - 1'))
    except Exception as e:
        return ('False', e)

    return (True, 'SUCCESS')

def reply_article(uid, board_id, article_id, reply):
    current_user = user.get_user(uid)
    if current_user[0] == False:
        return (False, 'NO_SUCH_USER')
    current_user = current_user[1]
    # check_acl(uid, board_id, 'WRITE')
    # if not acl: return (False, 'ACL_VIOLATION')
    if(reply['title'].strip() == ""):
        return (False, 'EMPTY_TITLE')

    if(reply['body'].strip() == ""):
        return (False, 'EMPTY_BODY')

    val = dict(board_id = board_id)
    result = db.select('Boards', val, where='bSerial = $board_id', what='bType, bWrite')
    board_info = None
    try:
        board_info = result[0]
    except:
        return (False, 'NO_SUCH_BOARD')
    if board_info.bType == 0:
        return (False, 'FOLDER')

    val = dict(board_id = board_id, article_id = article_id)
    ret = db.select('Articles', val, where='bSerial = $board_id AND aSerial = $article_id',
            what = 'aIndex, aLevel, aRoot')
    ret = ret[0]
    parent_index = ret.aIndex
    level = ret.aLevel + 1
    root = ret.aRoot

    val = dict(board_id = board_id, root = root)
    ret = db.select('Articles', val, where='bSerial = $board_id AND aRoot = $root',
            what = 'aSerial, aIndex, aLevel', order = 'aIndex ASC')

    index = 0
    lastindex = 0
    for r in ret:
        # 원글보다 아래쪽에 있으면서 레벨이 더 낮은 글을 발견하면 그 위치에 답글이 들어간다.
        if r.aIndex > parent_index and r.aLevel < level:
            index = r.aIndex
            break
        lastindex = r.aIndex

    if index == 0:
        # 발견 못했다면 그 스레드의 가장 마지막 글 다음으로.
        index = lastindex + 1

    # 아래쪽 글들의 index를 뒤로 미룬다
    val = dict(board_id = board_id, index = index)
    ret = db.update('Articles', vars = val, where = 'bSerial = $board_id AND aIndex >= $index',
            aIndex = web.SQLLiteral('aIndex + 1'))#, order='aIndex DESC')

    ret = db.insert('Articles', bSerial = board_id, aIndex = index,
            aTitle = reply['title'], aContent = reply['body'],
            aId = current_user.uId, aNick = current_user.uNick, 
            aDatetime = web.SQLLiteral("NOW()"), uSerial = uid,
            aLevel = level, aParent = article_id, aRoot = root)

    val = dict(index = index)
    ret = db.update('Articles', vars = val, where = 'aIndex = $index',
            aRoot = web.SQLLiteral("aSerial"), _test = True)

    val = dict(uid = uid)
    ret = db.update('Users', vars = val, where='uSerial = $uid',
        uNumPost = web.SQLLiteral('uNumPost + 1'))

    val = dict(index = index, board_id = board_id)
    ret = db.select('Articles', val, where = 'bSerial = $board_id AND aIndex = $index',
            what = 'aSerial')
    ret = ret[0].aSerial

    return (True, ret)

def get_comment_count(article_id):
    val = dict(article_id = int(article_id))
    result = db.query('SELECT COUNT(*) AS comment_count FROM Comments WHERE aSerial=$article_id', val);
    return result[0].comment_count

def get_comment(article_id):
    val = dict(article_id = int(article_id))
    result = db.select('Comments', val, where='aSerial = $article_id',
            order = 'cDatetime ASC')
    return result

def write_comment(uid, board_id, article_id, comment):
    current_user = user.get_user(uid)
    if current_user[0] == False:
        return (False, 'NO_SUCH_USER')
    current_user = current_user[1]
    # check_acl(uid, board_id, 'COMMENT')
    # if not acl: return (False, 'ACL_VIOLATION')
    if(comment.strip() == ""):
        return (False, 'EMPTY_COMMENT')

    article_id = int(article_id)
    val = dict(article_id = article_id)
    result = db.select('Articles', val, where='aSerial = $article_id',
            what='uSerial')
    try:
        article_info = result[0]
    except:
        return (False, 'NO_SUCH_ARTICLE')

    result = db.insert('Comments', bSerial = board_id, aSerial = article_id, uSerial = uid,
            cId = current_user.uId, cContent = comment, cDatetime = web.SQLLiteral('NOW()'))
    return (True, article_id)

def delete_comment(uid, comment_id):
    #current_user = user.get_user(uid)
    #if current_user[0] == False:
    #    return (False, 'NO_SUCH_USER')
    #current_user = current_user[1]
    # check_acl(uid, board_id, 'COMMENT')
    # if not acl: return (False, 'ACL_VIOLATION')
    val = dict(comment_id = comment_id)
    result = db.select('Comments', vars=val, what='uSerial, aSerial', where = 'cSerial = $comment_id')
    try:
        comment_info = result[0]
    except:
        return (False, 'NO_SUCH_COMMENT')

    if uid != comment_info.uSerial:
        return (False, 'ACL_VIOLATION')
    try:
        result = db.delete('Comments', vars=val, where='cSerial = $comment_id')
    except:
        return (False, 'DATABASE_ERROR')

    return (True, comment_info.aSerial)
