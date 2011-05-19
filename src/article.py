#!/usr/bin/python
# -*- coding: utf-8 -*-

import config
from config import db
import web
import math

import user, acl
import posixpath
import i18n
_ = i18n.custom_gettext

"""
글 모듈. 글을 읽어오기 위하여 필요한 일부 게시판 기능과 글 및 댓글에 접근한다.
"""
def _get_article_count(board_id):
    val = dict(board_id = board_id)
    result = db.query('SELECT COUNT(*) AS article_count FROM Articles WHERE bSerial=$board_id', val);
    return result[0].article_count

def _get_recurse_article_count(board_path):
    result = db.query('SELECT COUNT(*) AS article_count FROM Articles WHERE bSerial in (SELECT bSerial from Boards WHERE bName regexp "^' + board_path + '")')
    return result[0].article_count

def _get_all_article_count():
    result = db.query('SELECT COUNT(aSerial) AS a FROM Articles')
    return result[0].a

def _get_total_page_count(board_id, page_size):
    total_article = _get_article_count(board_id)
    return  (total_article + page_size -1) / page_size

def _get_recurse_page_count(board_path, page_size):
    total_article = _get_recurse_article_count(board_path)
    return  (total_article + page_size -1) / page_size

def get_recent_article_list(board_id, count):
    val = dict(board_id = board_id, limit = count)
    return db.query('select * from Articles natural left join (select aSerial, COUNT(*) as comment_count from Comments where bSerial = $board_id group by aSerial) as comment_group where bSerial = $board_id order by aIndex DESC limit $limit', val)

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
    result = db.query('SELECT * FROM Articles NATURAL LEFT JOIN (SELECT aSerial, COUNT(*) AS comment_count FROM Comments WHERE bSerial = $board_id GROUP BY aSerial) AS comment_group WHERE bSerial = $board_id AND aIndex BETWEEN $begin_index AND $end_index ORDER BY aIndex ASC', val)

    return result

def get_recurse_article_list(board_path, page_size, page_number):
    total_article = _get_recurse_article_count(board_path)
    last_page = _get_recurse_page_count(board_path, page_size)
    result = db.query('select * from Articles natural left join (select aSerial, COUNT(*) as comment_count from Comments where bSerial in (select bSerial from Boards where bName regexp "^' + board_path + '") group by aSerial) as comment_group where bSerial in (select bSerial from Boards where bName regexp "^' + board_path + '") order by aSerial DESC')
    l = []
    count = 0
    for row in result:
        count += 1
        if count <= (last_page - page_number) * page_size:
            continue;
        elif len(l) < page_size:
            l.append(row)
        else:
            break
    l.reverse()

    return l

def get_article_feed(board_id, feed_size):
    # 게시판의 피드로 사용할 수 있도록 aSerial 기준으로 글을 모아 줌.
    result = db.query('SELECT * FROM Articles WHERE bSerial = $board_id ORDER BY aSerial DESC LIMIT $feed_size',
            vars = locals())
    return result

def get_marked_article(board_id):
    # 현재 게시판의 강조된 글 목록을 반환함.
    result = db.query('select * from Articles natural left join (select aSerial, COUNT(*) as comment_count from Comments where bSerial = $board_id group by aSerial) as comment_group where bSerial = $board_id and aEmphasis = 1 order by aIndex ASC', dict(board_id = board_id))
    return result

def mark_article(article_id):
    # 강조함. 글이 존재하면 True, 존재하지 않으면 False를 반환함.
    t = db.transaction()
    try:
        ret = db.update('Articles', vars = locals(), where = 'aSerial = $article_id',
                aEmphasis = 1)
    except:
        t.rollback()
        return False
    else:
        t.commit()
    return ret > 0

def unmark_article(article_id):
    # 강조를 해제함. 글이 존재하면 True, 존재하지 않으면 False를 반환함.
    t = db.transaction()
    try:
        ret = db.update('Articles', vars = locals(), where = 'aSerial = $article_id',
                aEmphasis = 0)
    except:
        t.rollback()
        return False
    else:
        t.commit()
    return ret > 0

def toggle_marking(article_id):
    # 강조 상태를 변경한 다음, 변경 이후 강조 상태를 반환함.
    status = get_mark_status(article_id)
    if status:
        unmark_article(article_id)
        return False
    else:
        mark_article(article_id)
        return True

def get_mark_status(article_id):
    # 현재 글의 강조 여부를 반환함.
    ret = db.select('Articles', what='aEmphasis', vars=locals(),
            where = 'aSerial = $article_id')
    try:
        ret = ret[0]
    except IndexError:
        return False
    if ret.aEmphasis == 1:
        return True
    else:
        return False

def get_title(article_id):
    val = dict(article_id = int(article_id))
    result = db.select('Articles', val, where='aSerial = $article_id')
    try:
        retvalue = result[0]
    except IndexError:
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
    except IndexError:
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
    except IndexError:
        return -1
    return page_count - (article_count - index) / page_size

def get_article_(article_id):
    val = dict(article_id = int(article_id))
    result = db.select('Articles', val, where='aSerial = $article_id')
    try:
        retvalue = result[0]
    except IndexError:
        return None
    else:
        return retvalue

def get_article(board_id, article_id):
    val = dict(board_id = board_id, article_id = int(article_id))
    result = db.select('Articles', val, where='bSerial = $board_id AND aSerial = $article_id')
    try:
        retvalue = result[0]
    except IndexError:
        return None
    else:
        return retvalue

def increase_read_count(article_id):
    t = db.transaction()
    try:
        result = db.update('Articles', vars=locals(), where = 'aSerial = $article_id',
                aHit = web.SQLLiteral('aHit + 1'),)
    except:
        t.rollback()
    else:
        t.commit()
    return result > 0

def write_article(uid, board_id, article):
    if not acl.is_allowed('board', board_id, uid, 'write'):
        return (False, _('NO_PERMISSION'))
    current_user = user.get_user(uid)
    if current_user[0] == False:
        return (False, _('NO_SUCH_USER'))
    current_user = current_user[1]
    if(article['title'].strip() == ""):
        return (False, _('EMPTY_TITLE'))
    if(article['body'].strip() == ""):
        return (False, _('EMPTY_BODY'))

    val = dict(board_id = board_id)
    result = db.select('Boards', val, where='bSerial = $board_id', what='bType, bWrite')
    board_info = None
    try:
        board_info = result[0]
    except:
        return (False, _('NO_SUCH_BOARD'))
    if board_info.bType != 1:
        return (False, _('CANNOT_WRITE_ON_THIS_BOARD'))

    index = _get_article_count(board_id) + 1

    t = db.transaction()
    try:
        val = dict(index = index)
        ret = db.insert('Articles', bSerial = board_id, aIndex = index,
                aTitle = article['title'], aContent = article['body'],
                aId = current_user.uId, aNick = current_user.uNick, 
                aDatetime = web.SQLLiteral("NOW()"), uSerial = uid,
                aUpdatedDatetime = web.SQLLiteral("NOW()"),)

        val = dict(index = index)
        ret = db.update('Articles', vars = val, where = 'aIndex = $index',
                aRoot = web.SQLLiteral("aSerial"), _test = True)
    except:
        t.rollback()
        return (False, _('DATABASE_ERROR'))
    else:
        t.commit()

    val = dict(index = index, board_id = board_id)
    ret = db.select('Articles', val, where = 'bSerial = $board_id AND aIndex = $index',
            what = 'aSerial')
    ret = ret[0].aSerial

    return (True, ret)

def modify_article(uid, board_id, article_id, article, mark_as_unreaded):
    if not acl.is_allowed('article', article_id, uid, 'modify'):
        return (False, _('NO_PERMISSION'))
    current_user = user.get_user(uid)
    if current_user[0] == False:
        return (False, _('NO_SUCH_USER'))
    current_user = current_user[1]
    if(article['title'].strip() == ""):
        return (False, _('EMPTY_TITLE'))
    if(article['body'].strip() == ""):
        return (False, _('EMPTY_BODY'))

    val = dict(article_id = article_id)
    result = db.select('Articles', val, where='aSerial = $article_id',
            what='uSerial')
    article_info = None
    try:
        article_info = result[0]
    except IndexError:
        return (False, _('NO_SUCH_ARTICLE'))


    val = dict(article_id = article_id, title = article['title'], body = article['body'])
    t = db.transaction()
    try:
        ret = db.update('Articles', vars = val, where = 'aSerial = $article_id',
                aTitle = article['title'], aContent = article['body'],
                aEditedDatetime = web.SQLLiteral('NOW()'))

        if mark_as_unreaded:
            db.update('Articles', vars = dict(aSerial = article_id), where = 'aSerial = $aSerial',
                    aUpdatedDatetime= web.SQLLiteral('NOW()'))
    except:
        t.rollback()
        return (False, _('DATABASE_ERROR'))
    else:
        t.commit()

    return (True, article_id)

def delete_article(uid, article_id):
    if not acl.is_allowed('article', article_id, uid, 'delete'):
        return (False, _('NO_PERMISSION'))
    current_user = user.get_user(uid)
    if current_user[0] == False:
        return (False, _('NO_SUCH_USER'))
    current_user = current_user[1]

    article_id = int(article_id)
    val = dict(article_id = article_id)
    result = db.select('Articles', val, where='aSerial = $article_id',
            what='uSerial, bSerial, aIndex')
    article_info = None
    try:
        article_info = result[0]
    except IndexError:
        return (False, _('NO_SUCH_ARTICLE'))

    t = db.transaction()
    try:
        val = dict(article_id = article_id, board_id = article_info.bSerial,
                article_index = article_info.aIndex)
        result = db.query('SELECT COUNT(*) AS reply_count FROM Articles WHERE bSerial = $board_id AND aIndex = $article_index + 1 AND aParent = $article_id', val)
        reply_count = result[0].reply_count
        if reply_count > 0:
            return (False, _('HAS_REPLY'))

        ret = db.delete('Articles', vars = val, where = 'aSerial = $article_id')
        ret = db.delete('Comments', vars=val, where='aSerial = $article_id')
        ret = db.update('Articles', vars = val, where='bSerial = $board_id AND aIndex > $article_index',
                aIndex = web.SQLLiteral('aIndex - 1'))
    except:
        t.rollback()
        return (False, _('DATABASE_ERROR'))
    else:
        t.commit()

    return (True, _('SUCCESS'))

def reply_article(uid, board_id, article_id, reply):
    if not acl.is_allowed('board', board_id, uid, 'write'):
        return (False, _('NO_PERMISSION'))
    current_user = user.get_user(uid)
    if current_user[0] == False:
        return (False, _('NO_SUCH_USER'))
    current_user = current_user[1]
    if(reply['title'].strip() == ""):
        return (False, _('EMPTY_TITLE'))
    if(reply['body'].strip() == ""):
        return (False, _('EMPTY_BODY'))

    val = dict(board_id = board_id)
    result = db.select('Boards', val, where='bSerial = $board_id', what='bType, bWrite')
    board_info = None
    try:
        board_info = result[0]
    except IndexError:
        return (False, _('NO_SUCH_BOARD'))
    if board_info.bType != 1:
        return (False, _('CANNOT_WRITE_ON_THIS_BOARD'))

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

    t = db.transaction()
    try:
        # 아래쪽 글들의 index를 뒤로 미룬다
        val = dict(board_id = board_id, index = index)
        ret = db.update('Articles', vars = val, where = 'bSerial = $board_id AND aIndex >= $index',
                aIndex = web.SQLLiteral('aIndex + 1'))#, order='aIndex DESC')

        ret = db.insert('Articles', bSerial = board_id, aIndex = index,
                aTitle = reply['title'], aContent = reply['body'],
                aId = current_user.uId, aNick = current_user.uNick, 
                aDatetime = web.SQLLiteral("NOW()"), uSerial = uid,
                aLevel = level, aParent = article_id, aRoot = root,
                aUpdatedDatetime = web.SQLLiteral("NOW()"),)


        val = dict(index = index)
        ret = db.update('Articles', vars = val, where = 'aIndex = $index',
                aRoot = web.SQLLiteral("aSerial"), _test = True)
    except:
        t.rollback()
        return (False, _('DATABASE_ERROR'))
    else:
        t.commit()

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
    result = db.query('SELECT Comments.*, Users.uNick FROM Comments LEFT JOIN Users ON Comments.uSerial=Users.uSerial WHERE Comments.aSerial=$article_id ORDER BY cDatetime ASC', val);
    return result

def write_comment(uid, board_id, article_id, comment):
    if not acl.is_allowed('board', board_id, uid, 'comment'):
        return (False, _('NO_PERMISSION'))
    current_user = user.get_user(uid)
    if current_user[0] == False:
        return (False, _('NO_SUCH_USER'))
    current_user = current_user[1]
    if(comment.strip() == ""):
        return (False, _('EMPTY_COMMENT'))

    article_id = int(article_id)
    val = dict(article_id = article_id)
    result = db.select('Articles', val, where='aSerial = $article_id',
            what='uSerial')
    try:
        article_info = result[0]
    except IndexError:
        return (False, _('NO_SUCH_ARTICLE'))

    t = db.transaction()
    try:
        result = db.insert('Comments', bSerial = board_id, aSerial = article_id, uSerial = uid,
                cId = current_user.uId, cContent = comment, cDatetime = web.SQLLiteral('NOW()'))
        db.update('Articles', vars = dict(aSerial = article_id), where = 'aSerial = $aSerial',
                aUpdatedDatetime= web.SQLLiteral('NOW()'))
    except:
        t.rollback()
        return (False, _('DATABASE_ERROR'))
    else:
        t.commit()
    return (True, article_id)

def delete_comment(uid, comment_id):
    val = dict(comment_id = comment_id)
    result = db.select('Comments', vars=val, what='uSerial, aSerial', where = 'cSerial = $comment_id')
    try:
        comment_info = result[0]
    except IndexError:
        return (False, _('NO_SUCH_COMMENT'))

    if uid != comment_info.uSerial and not acl.is_allowed('article', comment_info.aSerial, uid, 'comment_delete'):
        return (False, _('NO_PERMISSION'))
    try:
        result = db.delete('Comments', vars=val, where='cSerial = $comment_id')
    except:
        return (False, _('DATABASE_ERROR'))

    return (True, comment_info.aSerial)

def search_article(board_id, keyword, page_size=20, page_no = 1, author=False, title=True, body=True):
    all_percent = True
    for ch in keyword:
        if ch == '%':
            all_percent = all_percent and True
        else:
            all_percent= all_percent and False
    if all_percent:
        return (False, _('NO_KEYWORD_SPECIFIED'))
    if len(keyword.strip()) == 0:
        return (False, _('NO_KEYWORD_SPECIFIED'))
    kw = '%' + keyword + '%'
    author_base = 'aId LIKE $kw'
    title_base = 'aTitle LIKE $kw'
    body_base = 'aContent LIKE $kw'
    cond_list = []

    if author:
        cond_list.append(author_base)
    if title:
        cond_list.append(title_base)
    if body:
        cond_list.append(body_base)
    cond = " OR ".join(cond_list)
    cond = 'bSerial = $board_id AND (' + cond + ')'
    offset = (page_no - 1) * page_size
    val = dict(board_id = board_id, kw = kw, page_size = page_size,
            offset = offset)

    ret = db.query('SELECT COUNT(*) AS result_count from Articles NATURAL LEFT JOIN (SELECT aSerial, COUNT(*) AS comment_count FROM Comments WHERE bSerial = $board_id GROUP BY aSerial) AS comment_group WHERE ' + cond + ' ORDER BY aIndex DESC', val)
    total_pages = int(math.ceil(int(ret[0].result_count) / float(page_size)))

    ret = db.query('SELECT * from Articles NATURAL LEFT JOIN (SELECT aSerial, COUNT(*) AS comment_count FROM Comments WHERE bSerial = $board_id GROUP BY aSerial) AS comment_group WHERE ' + cond + ' ORDER BY aIndex DESC LIMIT $offset, $page_size', val)
    return (True, total_pages, ret)

def get_all_articles(page_size, page_number):
    #total_article = _get_all_article_count()
    #if total_article < 0:
    #    return []
    #last_page = (total_article + page_size - 1) / page_size
    #if not (page_number >= 1 and page_number <= last_page):
    #    return []
    begin = page_size * (page_number - 1)
    val = dict(begin = begin, page_size = page_size)
    result = db.query('''SELECT * FROM Articles ORDER BY aDatetime DESC LIMIT $begin, $page_size''', val)
    return result
