#!/usr/bin/python
# -*- coding: utf-8 -*-

import config
import web
import user, util
import posixpath

"""
게시판 클래스. 데이터베이스 상에 저장된 게시판에 접근한다.
"""


if web.config.get('_database') is None:
    db = web.database(dbn=config.db_type, user=config.db_user,
            pw = config.db_password, db = config.db_name,
            host=config.db_host, port=int(config.db_port))
    web.config._database = db
else:
    db = web.config._database

def _get_board_id_from_path(path):
    if path != "":
        if path[0] != '/':
            path = '/%s' % path
    val = dict(board_path = path)
    result = db.select('Boards', val, where="bName = $board_path")
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
    val = dict(board_id = board_id)
    result = db.select('Boards', val, what='bParent', where='bSerial = $board_id')
    try:
        retvalue = result[0]
    except IndexError:
        return None
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
        return (False, 'NO_SUCH_BOARD')
    if not util.validate_boardname(settings['path']):
        return (False, 'INVALID_BOARDNAME')
    check = _get_board_id_from_path(settings['path'])
    if check > 0:
        return (False, 'BOARD_ALREADY_EXIST')
    if original_board_info.uSerial != settings['current_uid']:
        return (False, 'NO_PERMISSION')

    ret = db.insert('Boards', bName = settings['path'],
            uSerial = settings['board_owner'],
            bParent = parent_id, bDatetime = web.SQLLiteral('NOW()'),
            bInformation = settings['cover'],
            bDescription = settings['description'],
            bType = settings['type'],
            bReply = 1, bWrite = settings['guest_write'],
            bComment = settings['can_comment'])

    return (True, 'SUCCESS')

def edit_board(board_id, settings):
    # settings로 넘어오는 내용
    # path, name: 보드 전체 경로
    # description: 보드 짧은 설명
    # owner: 보대 ID. uid로 변환해야 함.
    # cover: 긴 설명, cover에 들어가는 내용
    # board_type: 0 - 폴더, 1 - 게시판
    # can_write_by_other: 쓰기 가능/불가능
    # can_comment: 0 - 불가능, 1 - 가능
    original_board_info = get_board_info(board_id)
    if original_board_info == None:
        return (False, 'NO_SUCH_BOARD')
    settings['board_id'] = board_id
    new_path = posixpath.join(settings['path'], settings['name'])
    if not util.validate_boardname(new_path):
        return (False, 'INVALID_BOARDNAME')
    old_path = original_board_info.bName
    old_directory = posixpath.dirname(old_path)
    new_directory = settings['path']
    if _get_board_id_from_path(new_path) > 0 and old_path != new_path:
        return (False, 'BOARD_ALREADY_EXIST')
    new_parent_id = _get_board_id_from_path(settings['path'])
    result = db.update('Boards', vars=settings, where='bSerial = $board_id',
            bInformation = settings['cover'], bDescription = settings['description'],
            bType = settings['board_type'], bReply = 1, bComment = settings['can_comment'],
            bWrite = settings['can_write_by_other'], uSerial = settings['owner'],
            bName = new_path, bParent = new_parent_id)
    result = move_child_boards(board_id, old_path, new_path)
    return (True, new_path)

def move_child_boards(board_id, old_path, new_path):
    # board_id 보드의 자식 보드가 속해 있는 경로를 new_path로 이동한다.
    val = dict(old_path = old_path + r'%')
    result = db.select('Boards', val, where = 'bName LIKE $old_path')
    for r in result:
        if not r.bName.startswith(old_path):
            continue
        val2 = dict(board_id = r.bSerial)
        update = db.update('Boards', vars = val2, where = 'bSerial = $board_id',
                bName = new_path + r.bName[len(old_path):])

def delete_board(current_uid, board_id):
    original_board_info = get_board_info(board_id)
    old_path = original_board_info.bName
    if current_uid != original_board_info.uSerial:
        return (False, 'NO_PERMISSION')
    val = dict(old_path = old_path + r'/%')
    has_child = False
    result = db.select('Boards', val, where = 'bName LIKE $old_path')
    for r in result:
        if not r.bName.startswith(old_path):
            continue
        has_child = True
    if has_child:
        return (False, 'HAS_CHILD')
    val = dict(board_id = board_id)
    result = db.delete('Boards', vars=val, where='bSerial = $board_id')
    delete_all_article(board_id)
    return (True, posixpath.dirname(old_path))

def delete_all_article(board_id):
    val = dict(board_id = board_id)
    result = db.delete('Articles', vars=val, where='bSerial = $board_id')
    return result

def search_board(description):
    # 사이드바의 학번별 보드를 검색하기 위해서 만들어졌음.
    # 타 용도로 사용 금지!
    val = dict(desc = description)
    result = db.select('Boards', val, where="bDescription LIKE $desc")
    try:
        retvalue = result
    except:
        return None
    else:
        return retvalue
