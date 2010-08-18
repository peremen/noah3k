#!/usr/bin/python
# -*- coding: utf-8 -*-

import config
import web

import user
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
    except:
        return -1
    else:
        return retvalue

def _get_article_count( board_id):
    val = dict(board_id = board_id)
    result = db.query('SELECT COUNT(*) AS article_count FROM Articles WHERE bSerial=$board_id', val);
    return result[0].article_count

def _get_total_page_count(board_id, page_size):
    total_article = _get_article_count(board_id)
    return  (total_article + page_size -1) / page_size

def create_board(parent, settings):
    # bName: 보드 전체 경로
    # uSerial: 보대
    # bParent: 부모 보드 ID
    # bDescription: 보드 짧은 설명
    # bDatetime: 생성 시간. NOW()
    # bInformation: 긴 설명, cover에 들어가는 내용
    # bType: 0 - 폴더, 1 - 게시판
    # bReply: 0 - 답글이 평면으로, 1 - 답글이 스레드로
    # bWrite: 쓰기 가능/불가능
    # bComment: 0 - 불가능, 1 - 가능
    # bSerial: 자동 증가
    pass

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
    if settings['path'] != posixpath.dirname(original_board_info.bName):
        return (False, 'NOT_IMPLEMENTED')
    new_path = posixpath.join(settings['path'], settings['name'])
    result = db.update('Boards', vars=settings, where='bSerial = $board_id',
            bInformation = settings['cover'], bDescription = settings['description'],
            bType = settings['board_type'], bReply = 1, bComment = settings['can_comment'],
            bWrite = settings['can_write_by_other'], uSerial = settings['owner'],
            bName = new_path)
    return (True, new_path)

def move_child_boards(board_id, new_path):
    # board_id 보드의 자식 보드가 속해 있는 경로를 new_path로 이동한다.
    pass

def delete_board(board_id):
    pass

def get_board_info(board_id):
    # board_id 보드의 정보를 가져온다.
    val = dict(board_id = board_id)
    result = db.select('Boards', val, where="bSerial = $board_id")
    try:
        retvalue = result[0]
    except:
        return None
    else:
        return retvalue

def get_child(board_id):
    # board_id 보드의 자식 보드를 가져온다.
    val = dict(board_id = board_id)
    result = db.select('Boards', val, where='bParent = $board_id', order='bName ASC')
    return result

def get_parent(board_id):
    val = dict(board_id = board_id)
    result = db.select('Boards', val, what='bParent', where='bSerial = $board_id')
    try:
        retvalue = result[0]
    except:
        return None
    else:
        return retvalue['bParent']

def get_article_list(board_id, page_size, page_number):
    total_article = _get_article_count(board_id)
    last_page = _get_total_page_count(board_id, page_size)
    assert(page_number >= 1 and page_number <= last_page)
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

def get_title(article_id):
    print 'a'
    val = dict(article_id = int(article_id))
    result = db.select('Articles', val, where='aSerial = $article_id')
    try:
        retvalue = result[0]
    except:
        return None
    else:
        return retvalue.aTitle

def get_article(board_id, article_id):
    # aSerial: 글 UID bSerial: 글이 있는 보드 aIndex: 게시판에 보이는 가상 글 번호 aTitle: 제목
    # aId: 글쓴이 ID aNick: 글쓴이의 당시 닉네임 
    # uSerial: 글쓴이의 UID (여기서 aId/aNick 유도 가능)
    # aContent: 본문 aLastGuest: 모름 aHit: 조회 수
    # aEmphasis: 강조 여부 aDatetime: 최초 작성 시간 aEditedDatetime: 수정 시간, 없으면 NULL
    # aLevel: 글 깊이 aParent: aLevel > 0의 경우 바로 윗 부모 글. assert(aLevel == 0 && aParent == NULL)
    # aRoot: 깊이가 계속 깊어져 갔을 때 최종적인 부모. aParent == NULL인 경우 자기 자신.
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
    print ret

    return (True, ret)

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
    print ret

    return (True, ret)
    pass


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
        print val

        result = db.query('SELECT COUNT(*) AS reply_count FROM Articles WHERE bSerial = $board_id AND aIndex = $article_index + 1 AND aParent = $article_id', val)
        reply_count = result[0].reply_count
        if reply_count > 0:
            return (False, 'HAS_REPLY')

        ret = db.delete('Articles', vars = val, where = 'aSerial = $article_id')

        ret = db.update('Articles', vars = val, where='bSerial = $board_id AND aIndex > $article_index',
                aIndex = web.SQLLiteral('aIndex - 1'))
    except Exception as e:
        return ('False', e)

    return (True, 'SUCCESS')

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

def get_attachment(article_id):
    # 데이터베이스: Supplement
    # sSerial: 파일 ID
    # aSerial: article_id
    # sFilename: 첨부파일 이름
    val = dict(article_id = int(article_id))
    result = db.select('Supplement', val, where='aSerial = $article_id')
    return result

def get_comment(article_id):
    # 데이터베이스: Comments
    # cSerial: 커멘트 ID (삭제할 때 사용)
    # bSerial: 게시판 ID
    # aSerial: 글 ID
    # uSerial: 커멘트 남긴 사람 ID (NULL이면 게스트 모드)
    # cId: 커멘트 남긴 사람 ID (이름으로 저장됨)
    # cContent: 커멘트 내용
    # cDatetime: 날짜 및 시간
    # cPasswd: 게스트로 남길 때 암호
    # cHomepage: 게스트로 남길 때 홈페이지
    # 더 이상 게스트로 커멘트 남기기는 지원하지 않으나, 과거 DB 파싱은 필요함
    # NULL인 레코드 총 58개
    val = dict(article_id = int(article_id))
    result = db.select('Comments', val, where='aSerial = $article_id',
            order = 'cDatetime ASC')
    return result

def get_comment_count(article_id):
    val = dict(article_id = int(article_id))
    result = db.query('SELECT COUNT(*) AS comment_count FROM Comments WHERE aSerial=$article_id', val);
    return result[0].comment_count
