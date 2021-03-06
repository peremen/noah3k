#!/usr/bin/python
# -*- coding: utf-8 -*-

import web
import config
from config import db
import user, util
import posixpath
import acl
import i18n
import article
_ = i18n.custom_gettext

"""
게시판 클래스. 데이터베이스 상에 저장된 게시판에 접근한다.
"""
def _get_board_id_from_path(path):
    if path == '' or path == '/':
        return 1
    if path != "":
        if not path.startswith('/'):
            path = '/%s' % path
        if path.endswith('/'):
            path = path[:-1]
    val = dict(board_path = path)
    result = db.select('Boards', val, where="bName = $board_path")
    try:
        retvalue = result[0]["bSerial"]
    except IndexError:
        return -1
    else:
        return retvalue

def _get_board_id_from_regex_path(path):
    if path != "":
        if path[0] == '/':
            path = path[1:]

    fronts = path.split('/')
    regex = ''
    for front in fronts:
        regex = regex + '/%s[[:alnum:]]*' % front
    regex = '^' + regex + '$'

    val = dict(board_regex = regex)
    result = db.query('select * from Boards where bName REGEXP $board_regex', val)
    try:
        retvalue = result[0]["bSerial"]
    except IndexError:
        return -1
    else:
        return retvalue

def _get_path_from_board_id(board_id):
    result = db.select('Boards', locals(), where='bSerial = $board_id')
    try:
        retvalue = result[0]['bName']
    except IndexError:
        return ''
    else:
        return retvalue

def get_parent(board_id):
    if board_id == 1: # 최상위 보드
        return -1
    val = dict(board_id = board_id)
    result = db.select('Boards', val, what='bParent', where='bSerial = $board_id')
    try:
        retvalue = result[0]
    except IndexError:
        return -1
    else:
        return retvalue['bParent']

def get_child(board_id):
    # board_id 보드의 자식 보드를 가져온다.
    val = dict(board_id = board_id)
    result = db.select('Boards', val, where='bParent = $board_id', order='bName ASC')
    return result

def get_board_info(board_id):
    # board_id 보드의 정보를 가져온다.
    val = dict(board_id = board_id)
    result = db.select('Boards', val, where="bSerial = $board_id")
    try:
        retvalue = result[0]
    except IndexError:
        return None
    else:
        return retvalue

def create_board(parent_id, settings):
    original_board_info = get_board_info(parent_id)
    if original_board_info == None:
        return (False, _('NO_SUCH_BOARD'))
    if not util.validate_boardname(settings['path']):
        return (False, _('INVALID_BOARDNAME'))
    check = _get_board_id_from_path(settings['path'])
    if check > 0:
        return (False, _('BOARD_ALREADY_EXIST'))
    if not acl.is_allowed('board', parent_id, settings['current_uid'], 'create'):
        return (False, _('NO_PERMISSION'))
    if settings['type'] == 2:
        if _get_board_id_from_path(settings['description']) < 0 or settings['description'].strip() == '':
            return (False, _('NO_SUCH_BOARD'))

    t = db.transaction()
    try:
        ret = db.insert('Boards', bName = settings['path'],
                uSerial = settings['board_owner'],
                bParent = parent_id, bDatetime = web.SQLLiteral('NOW()'),
                bInformation = settings['cover'],
                bDescription = settings['description'],
                bType = settings['type'],
                bReply = 1, bWrite = settings['guest_write'],
                bComment = settings['can_comment'],
                indexable = settings['indexable'], show_avatar = settings['show_avatar'])
    except:
        t.rollback()
    else:
        t.commit()

    return (True, 'SUCCESS')

def board_edit(current_uid, board_id, settings):
    # settings로 넘어오는 내용
    # path, name: 보드 전체 경로
    # description: 보드 짧은 설명
    # owner: 보대 ID. uid로 변환해야 함.
    # cover: 긴 설명, cover에 들어가는 내용
    # board_type: 0 - 폴더, 1 - 게시판
    # can_write_by_other: 쓰기 가능/불가능
    # can_comment: 0 - 불가능, 1 - 가능
    # indexable: 0 - 검색 제외, 1 - 검색 포함
    # show_avatar: 0 - 안 보임, 1 - 보임
    if not acl.is_allowed('board', board_id, current_uid, 'edit'):
        return (False, _('NO_PERMISSION'))
    original_board_info = get_board_info(board_id)
    if original_board_info == None:
        return (False, _('NO_SUCH_BOARD'))
    settings['board_id'] = board_id
    new_path = posixpath.join(settings['path'], settings['name'])
    if not util.validate_boardname(new_path):
        return (False, _('INVALID_BOARDNAME'))
    if settings['board_type'] == 2:
        if article._get_article_count(board_id) > 0:
            return (False, _('ALIAS_CANT_HAVE_ARTICLE'))
        if _get_board_id_from_path(settings['description']) < 0 or settings['description'].strip() == '':
            return (False, _('NO_SUCH_BOARD'))
    old_path = original_board_info.bName
    old_directory = posixpath.dirname(old_path)
    new_directory = settings['path']
    if _get_board_id_from_path(new_path) > 0 and old_path != new_path:
        return (False, _('BOARD_ALREADY_EXIST'))
    new_parent_id = _get_board_id_from_path(settings['path'])
    if new_parent_id < 0:
        return (False, _('INVALID_PARENT'))
    if new_parent_id != original_board_info.bParent:
        if not acl.is_allowed('board', new_parent_id, current_uid, 'create'):
            return (False, _('NO_PERMISSION_ON_NEW_PARENT'))

    t = db.transaction()
    try:
        result = db.update('Boards', vars=settings, where='bSerial = $board_id',
                bInformation = settings['cover'], bDescription = settings['description'],
                bType = settings['board_type'], 
                bReply = 1, bComment = settings['can_comment'],
                indexable = settings['indexable'], 
                stylesheet = settings['stylesheet'],
                show_avatar = settings['show_avatar'],
                bWrite = settings['can_write_by_other'], 
                uSerial = settings['owner'],
                bName = new_path, bParent = new_parent_id)
        result = move_child_boards(board_id, old_path, new_path)
    except:
        t.rollback()
    else:
        t.commit()
    return (True, new_path)

def move_child_boards(board_id, old_path, new_path):
    # board_id 보드의 자식 보드가 속해 있는 경로를 new_path로 이동한다.
    val = dict(old_path = old_path + r'%')
    result = db.select('Boards', val, where = 'bName LIKE $old_path')
    t = db.transaction()
    try:
        for r in result:
            if not r.bName.startswith(old_path):
                continue
            val2 = dict(board_id = r.bSerial)
            update = db.update('Boards', vars = val2, where = 'bSerial = $board_id',
                    bName = new_path + r.bName[len(old_path):])
    except:
        t.rollback()
    else:
        t.commit()

def delete_board(current_uid, board_id):
    original_board_info = get_board_info(board_id)
    old_path = original_board_info.bName
    if not acl.is_allowed('board', board_id, current_uid, 'delete'):
        return (False, _('NO_PERMISSION'))
    val = dict(old_path = old_path + r'/%')
    has_child = False
    result = db.select('Boards', val, where = 'bName LIKE $old_path')
    for r in result:
        if (r.bName == old_path) or (not r.bName.startswith(old_path)):
            continue
        has_child = True
    if has_child:
        return (False, _('HAS_CHILD'))
    val = dict(board_id = board_id)
    result = db.delete('Boards', vars=val, where='bSerial = $board_id')
    delete_all_article(board_id)
    return (True, posixpath.dirname(old_path))

def delete_all_article(board_id):
    val = dict(board_id = board_id)
    result = db.delete('Articles', vars=val, where='bSerial = $board_id')
    return result

def _board_search_comparator(b1, b2):
    year1 = int(b1.bDescription[3:5]) 
    year2 = int(b2.bDescription[3:5])
    if year1 / 10 == 9:
        year1 = year1-100
    if year2 / 10 == 9:
        year2 = year2-100
    return year2 - year1

def search_board(description):
    val = dict(desc = description)
    ret = []
    for row in db.select('Boards', val, where="bDescription LIKE $desc"):
        ret.append(row)

    ret.sort(_board_search_comparator)
    ret = ret[0:7]
    ret.reverse()
    
    return ret

def get_boardname_by_prefix(boardname, count=5):
    val = dict(boardname = boardname + '%')
    ret = []
    for row in db.select('Boards', val, what='bName', where="bName LIKE $boardname", order='bName', limit=count):
        ret.append(row.bName)
    return ret
