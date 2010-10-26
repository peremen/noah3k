#!/usr/bin/python
# -*- coding: utf-8 -*-

import board, user, article
import config
import web

"""
Noah3K ACL 모듈. Noah3K 보안 설정의 가장 핵심을 이룬다.

ACL 정보는 누가(who) 무엇(what)에 어떤 동작을(how) 허용/거부할 지 저장한다.
'누가'는 사용자의 ID이며, 모든 사용자, 로그인 사용자, 비로그인 사용자를 위한 예약된
사용자 ID는 별도로 관리한다. '무엇'은 글과 게시판 둘 중 하나이며, 차후 확장을
위하여 개체를 더 추가할 수도 있다. '어떤 동작'은 글이냐 게시판이냐에 따라서
달라진다.

글의 경우에는 처음 글 쓴 사람 이외의 사람이 편집하는 것 자체가 넌센스이므로,
ACL을 통해 통제할 수 있는 권한은 읽기 권한과 커멘트 권한이다. 일부 글의 경우
커멘트 자체를 받고 싶지 않은 경우가 있을 것이다. 보드의 경우 ACL로 통제할
수 있는 권한이 더 많아진다. 보드 공개/비공개 여부, 공지 설정 가능 여부,
하위 보드 생성/삭제 가능 여부, 올라온 글 삭제 가능 여부를 생각해 볼 수 있다.
보드 시삽이라 할지라도 다른 사람의 글을 편집할 수는 없도록 할 것이다.
보드 시삽은 ACL을 통해서 지정하지 않아도 보드에 대한 모든 권한을 가질
수 있으므로, 이 기능은 보드 부시삽을 추가하는 데 유용하게 사용할 수
있다.

노아 시삽은 어떤 개체에도 ACL을 추가하거나 삭제할 수 있으며,
각 보드 대표는 자기 보드 및 하위 보드, 각 글쓴이는 자기 글에 ACL을
추가하거나 삭제할 수 있다..

상속 문제. ACL은 기본적으로 상속된다. 사용자 A가 보드의 특정 권한을 가지고
있다면, 그 보드의 하위 권한에도 ACL은 전파된다. 보드의 ACL 목록을 가져올
때에도 하위 보드에도 부모 보드의 권한은 전파된다. 상위 보드와 충돌하는 
권한이 있는 경우에는 하위 보드의 권한이 우선이다. ACL 목록은 상속된 권한과
가지고 있는 권한을 나눠서 표시한다.

ACL을 전혀 적용하지 않았을 때 권한은 다음과 같다.

- 글: 모두에게 공개, 로그인 사용자만 커멘트 가능
- 보드: 보드 시삽은 모든 권한을 가지며, 시삽이 아닌 사람은 보드 접근
  권한만 가진다. 기본적으로 모든 보드는 공개 보드라는 뜻이다.
"""

if web.config.get('_database') is None:
    db = web.database(dbn=config.db_type, user=config.db_user,
            pw = config.db_password, db = config.db_name,
            host=config.db_host, port=int(config.db_port))
    web.config._database = db
else:
    db = web.config._database

def add_acl(session_key, object_type, object_id, user_id, permission):
    """
    지정한 권한을 추가한다.

    @type session_key: string
    @param session_key: 세션 키.
    @type object_type: int
    @param object_type: 개체 종류. 글, 보드가 정의되어 있다.
    @type object_id: int
    @param object_id: 글이나 보드 ID. 이름이 아니다.
    @type user_id: int
    @param user_id: 사용자 UID.
    @type permission: string
    @param permission: 추가하고자 하는 권한.
    @rtype tuple
    @return 성공 여부와 오류 코드(실패 시)가 포함된 튜플.
    """
    pass

def remove_acl(session_key, object_type, object_id, user_id, permission):
    """
    지정한 권한을 삭제한다.

    @type session_key: string
    @param session_key: 세션 키.
    @type object_type: int
    @param object_type: 개체 종류. 글, 보드가 정의되어 있다.
    @type object_id: int
    @param object_id: 글이나 보드 ID. 이름이 아니다.
    @type user_id: int
    @param user_id: 사용자 UID.
    @type permission: string
    @param permission: 삭제하고자 하는 권한.
    @rtype tuple
    @return 성공 여부와 오류 코드(실패 시)가 포함된 튜플.
    """
    pass

def get_acl(object_type, object_id):
    """
    지정한 개체의 권한을 가져온다. 시삽은 모든 개체에 대해서 권한이 있으므로,
    이 목록에는 항상 시삽이 들어가야 한다. 표시 여부는 클라이언트에서 정한다.

    @type object_type: int
    @param object_type: 개체 종류. 글, 보드가 정의되어 있다.
    @type object_id: int
    @param object_id: 글이나 보드 ID. 이름이 아니다.
    @rtype list
    @return 사용자와 허용/거부된 권한, 상속 여부를 포함하는 튜플을 포함하는 목록.
    """
    pass

def get_board_admins(board_id):
    admin_uids = []
    current_board = board.get_board_info(board_id)
    if current_board == None:
        return None
    admin_uids.append(current_board.uSerial)
    board_id = board.get_parent(board_id)
    while board_id > 0:
        current_board = board.get_board_info(board_id)
        admin_uids.append(current_board.uSerial)
        board_id = current_board.bParent
    return list(set(admin_uids))

def is_allowed(object_type, object_id, user_id, permission):
    """
    지정한 개체에 지정한 사용자가 권한을 가지고 있는지 알려 준다.

    @type object_type: int
    @param object_type: 개체 종류. 'article', 'board', 'comment' 중 하나이다.
    @type object_id: int
    @param object_id: 글이나 보드 ID. 이름이 아니다.
    @type user_id: int
    @param user_id: 사용자 ID. 
    @type permission: string
    @param permission: 허용 여부를 알고자 하는 권한.
    @rtype bool
    @return 허용/금지 여부.
    """
    try:
        return eval('is_allowed_%s' % (object_type))(object_id, user_id, permission)
    except AttributeError:
        return False

def is_allowed_board(board_id, user_id, permission):
    # comment, write는 별도로 빼낼 필요가 있음.
    board_admins = get_board_admins(board_id)
    board_info = board.get_board_info(board_id)
    if permission == 'comment': # 댓글 허용/비허용은 모두에게 적용됨.
        return board_info.bComment == 1
    if user_id == 1: # 시삽
        return True
    if permission == 'write': # 모두에게 쓰기가 허용된 경우.
        if board_info.bWrite == 1:
            return True
    if user_id in board_admins:
        # 기타 모든 권한은 보대 및 상위 보드 보대에게 모두 적용됨.
        return True
    return False

def is_allowed_article(article_id, user_id, permission):
    if user_id == 1: # 시삽
        return True
    a = article.get_article_(article_id)
    writer = a.uSerial
    board_admins = get_board_admins(a.bSerial)
    if permission == 'modify':
        return user_id == a.uSerial
    return (user_id == a.uSerial) or (user_id in board_admins)
