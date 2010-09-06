#!/usr/bin/python
# -*- coding: utf-8 -*-

import config
import web
import crypt, hashlib, hmac
import util

"""
사용자 로그인, 로그아웃, 세션을 관리한다.
"""
if web.config.get('_database') is None:
    db = web.database(dbn=config.db_type, user=config.db_user,
            pw = config.db_password, db = config.db_name,
            host=config.db_host, port=int(config.db_port))
    web.config._database = db
else:
    db = web.config._database

def _verify_noah1k_password(to_verify, password):
    # UNIX crypt 함수. password가 seed, username이 텍스트.
    # 더 이상 생성할 필요도 이유도 없음.
    pass1 = crypt.crypt(password, password)
    return to_verify == crypt.crypt(password, pass1)

def _generate_noah2k_password(password):
    # MySQL <4.1.1 password() 함수의 파이썬 구현.
    # noah3k 런칭 이전까지는 생성할 필요가 있음.
    nr = 1345345333
    add = 7
    nr2 = 0x12345671
    t = 0
    for char in password:
        if (char == ' ' or char == '\t'):
            continue
        t = ord(char)
        nr ^= (((nr & 63)+add)*t) + ((nr << 8) & 0xFFFFFFFF)
        nr2 += ((nr2 << 8) & 0xFFFFFFFF) ^ nr
        add += t

    out_a = nr & ((1<<31)-1)
    out_b = nr2 & ((1<<31)-1)
    return "%08x%08x" % (out_a, out_b)

def _verify_noah2k_password(to_verify, password):
    return to_verify == _generate_noah2k_password(password)

def _generate_noah3k_password(password):
    hm = hmac.new(config.hmac_key, password, hashlib.sha256)
    return hm.hexdigest()

def generate_password(password):
    return _generate_noah2k_password(password)

def _verify_noah3k_password(to_verify, password):
    return to_verify == _generate_noah3k_password(password)

password_set = {13: _verify_noah1k_password,
                16: _verify_noah2k_password,
                64: _verify_noah3k_password, }

def _get_uid_from_username(username):
    """
    사용자 이름을 UID로 변환한다.

    @type username: string
    @param username: 사용자 이름
    @rtype int
    @return: 이름에 해당하는 사용자 ID. 
    """
    val = dict(username = username)
    result = db.select('Users', val, where="uId = $username")
    try:
        retvalue = int(result[0]['uSerial'])
    except IndexError:
        return -1
    else:
        return retvalue

def _get_username_from_uid(uid):
    u = get_user(uid)
    if not u[0]:
        return ''
    else:
        return u[1]['uId']

def update_password(uid, password):
    val = dict(uid = uid)
    result = db.select('Users', val, where='uSerial = $uid')
    user = None
    try:
        user = result[0]
    except IndexError:
        return False
    t = db.transaction()
    try:
        ret = db.update('Users', where = 'uSerial = $uid', uPasswd = _generate_noah3k_password(password)) 
    except:
        t.rollback()
        return False
    else:
        t.commit()
    return True

def verify_password(uid, password):
    user = get_user(uid)
    if not user[0]:
        return False
    if password_set[len(user[1].uPasswd)](user[1].uPasswd, password):
        return True
    return False

def get_password_strength(uid):
    strength = {13: 0, 16: 1, 64: 2}
    user = get_user(uid)
    if not user[0]:
        return -1
    return strength[len(user[1].uPasswd)]

def login(username, password):
    """
    로그인 처리. 사용자 ID와 암호를 평문으로 입력받은 다음,
    해당하는 사용자가 있는 지 확인하고 존재하면 세션 키,
    존재하지 않으면 오류 코드를 돌려 준다. 암호는 평문으로만 전송해야 하므로,
    암호를 보호하려면 별도의 보안 통신 채널을 열어야 한다.

    @type username: string
    @param username: 사용자 ID.
    @type password: string
    @param password: 암호. 평문으로 전송되어야 한다.
    @rtype tuple
    @return: 로그인 성공 여부(T/F)와 세션 키(성공 시) 또는 오류 코드(실패 시)를 포함하는 튜플.
    """
    val = dict(username = username)
    result = db.select('Users', val, where='uId = $username')
    user = None
    try:
        user = result[0]
    except IndexError:
        return (False, 'NO_SUCH_USER')
    if not password_set[len(user.uPasswd)](user.uPasswd, password):
        return (False, 'WRONG_PASSWORD')
    #if len(user.uPassword) < 64:
    #    update_password(user.uSerial, password)
    return (True, 'LOGIN_SUCCESS')

def get_owned_board(uid):
    # 모든 정보가 돌아옴.
    val = dict(uid = uid)
    result = db.select('Boards', val, where='uSerial = $uid', order = 'bName')
    return result

def get_favorite_board(uid):
    # bSerial만 돌아오므로 적절한 가공이 필요함.
    val = dict(uid = uid)
    result = db.select('Favorites', val, where='uSerial = $uid')
    return result

def is_favorite(uid, board_id):
    val = dict(uid = uid, board_id = board_id)
    result = db.query('SELECT COUNT(*) AS f FROM Favorites WHERE uSerial=$uid AND bSerial=$board_id', val);
    return result[0].f > 0

def add_favorite_board(uid, board_id):
    t = db.transaction()
    try:
        result = db.insert('Favorites', uSerial = uid, bSerial = board_id)
    except:
        t.rollback()
        return False
    else:
        t.commit()
    return result

def remove_favorite_board(uid, board_id):
    val = dict(uid = uid, board_id = board_id)
    t = db.transaction()
    try:
        result = db.delete('Favorites', vars=val, where='uSerial = $uid AND bSerial = $board_id')
    except:
        t.rollback()
    else:
        t.commit()
    return result

def get_favorite_board_feed(uid, feed_size):
    """
    사용자가 즐겨찾기로 추가한 게시판을 모아서 최신 글을 출력한다.

    @type uid: int
    @param uid: 사용자 UID.
    @type feed_size: int
    @param feed_size: 피드로 보여줄 글 갯수.
    @rtype list
    @return: 지정한 피드 크기보다 작거나 같은 전체 글 목록.
    """
    board_id_list = []
    for f in get_favorite_board(uid):
        board_id_list.append(str(f.bSerial))
    if len(board_id_list) == 0:
        return []
    in_clause = ','.join(board_id_list)
    val = dict(c = in_clause)

    result = db.query('SELECT * FROM Articles WHERE bSerial IN (%s) ORDER BY aSerial DESC LIMIT %s' % \
            (in_clause, feed_size))
    return result

def get_user(uid):
    """
    사용자 정보를 가져온다. 사용자 UID를 사용하므로, 사용자
    이름으로 조회하려면 L{_get_uid_from_username} 함수를 써서 UID로 변환해야 한다.

    @type uid: int
    @param uid: 사용자 UID.
    @rtype tuple
    @return: 사용자 존재 여부(T/F)와 사용자 정보 딕셔너리(성공 시) 또는 오류 코드(실패 시)를 포함하는 튜플.
    """
    val = dict(uid = uid)
    result = db.select('Users', val, where="uSerial = $uid")
    try:
        retvalue = result[0]
    except IndexError:
        return (False, 'NO_SUCH_USER')
    else:
        return (True, retvalue)

def get_post_count(uid):
    val = dict(uid = uid)
    result = db.query('SELECT COUNT(*) AS a FROM Articles WHERE uSerial=$uid', val);
    return result[0].a

def get_comment_count(uid):
    val = dict(uid = uid)
    result = db.query('SELECT COUNT(*) AS c FROM Comments WHERE uSerial=$uid', val);
    return result[0].c

def join(member):
    """
    회원 등록. 회원 정보를 포함하고 있는 딕셔너리를 던져 주면
    회원 등록을 시도한다. 실패했을 경우 상황에 따른 오류 코드를 반환한다.

    member에 오는 키와 값은 다음과 같다.

    - username: 사용자 ID
    - password: 사용자 암호. 두 번 입력받는 걸 검증하는 역할은 프론트엔드에서 담당한다. 암호화되지 않음.
    - nick: 별명.
    - email: 이메일 주소.
    - signature: 글 뒤에 붙는 시그.
    - introduction: 회원 정보 페이지에 뜨는 자기 소개.

    @type member: dict
    @param member: 회원 정보 딕셔너리.
    @rtype tuple
    @return: 회원 등록 성공 여부(T/F)와 오류 코드(실패 시)를 포함하는 튜플.
    """
    if not util.validate_username(member['username']):
        return (False, 'INVALID_USERNAME')
    if _get_uid_from_username(member['username']) > 0:
        return (False, 'ID_ALREADY_EXISTS')
    t = db.transaction()
    try:
        result = db.insert('Users', uNick = member['nick'], uEmail = member['email'],
                uId = member['username'], uPasswd = generate_password(member['password']),
                uDatetime = web.SQLLiteral('NOW()'), uSig = '', uPlan = '')
    except:
        t.rollback()
        return (False, 'DATABASE_ERROR')
    else:
        t.commit()
    return (True, '')


def modify_user(uid, member):
    """
    회원 정보 수정. frontend에서 접근 권한을 통제해야 한다. 시삽은 임의
    회원의 정보를 수정할 수 있다. C{member} 딕셔너리는 수정할 정보로,
    형식은 L{register}를 참고한다. 빈 값이 들어오면 삭제를 의미하므로,
    기존 정보를 수정하려면 정보를 그대로 넘겨줘야 한다.

    @type uid: int
    @param uid: 수정할 회원의 사용자 ID.
    @type member: dict
    @param member: 회원 정보 딕셔너리. (password: 암호, email: E-Mail,
    homepage: 홈페이지, sig: 시그, introduction: 자기 소개)
    @rtype tuple
    @return: 정보 수정 성공 여부(T/F)와 오류 코드(실패 시)를 포함하는 튜플.
    """
    t = db.transaction()
    try:
        result = db.update('Users', vars=member, where='uSerial = $user_id',
                uNick = member['nick'], uEmail = member['email'],
                uSig = member['sig'], uPlan = member['introduction'],
                uPasswd = generate_password(member['password']))
    except:
        t.rollback()
        return False
    else:
        t.commit()
    return result

def delete_user(uid):
    """
    회원 정보 삭제.
    """
    result = get_owned_board(uid)
    has_board = False
    for b in result:
        has_board = True
    if has_board:
        return (False, 'HAS_BOARD')

    # 즐겨찾는 보드 삭제
    result = get_favorite_board(uid)
    for b in result:
        remove_favorite_board(uid, b.bSerial)

    val = dict(user_id = uid)
    t = db.transaction()
    try:
        result = db.delete('Users', vars=val, where='uSerial = $user_id')
    except:
        t.rollback()
        return (False, 'DATABASE_ERROR')
    else:
        t.commit()
    return (True, 'SUCCESS')

def update_last_login(uid, ip_address):
    val = dict(uid = uid, ip_address = ip_address)
    t = db.transaction()
    try:
        result = db.update('Users', vars=val, where = 'uSerial = $uid',
                uNumLogin = web.SQLLiteral('uNumLogin + 1'),
                uLastLogin = web.SQLLiteral('NOW()'),
                uLastHost = ip_address)
    except:
        t.rollback()
        return False
    else:
        t.commit()
    return result
