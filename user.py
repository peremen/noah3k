#!/usr/bin/python
# -*- coding: utf-8 -*-

import config
import web
import crypt, hashlib, hmac

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
    pass1 = crypt.crypt(password, password)
    return to_verify == crypt.crypt(password, p1)

def _verify_noah2k_password(to_verify, password):
    # MySQL <4.1.1 password() 함수의 파이썬 구현.
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
    return to_verify == "%08x%08x" % (out_a, out_b)

def _generate_noah3k_password(to_verify, password):
    hm = hmac.new('tokigunbapsot', password, hashlib.sha1)
    return hm.hexdigest()

def _verify_noah3k_password(to_verify, password):
    return to_verify == _generate_noah3k_password(password)

password_set = {13: _verify_noah1k_password,
                16: _verify_noah2k_password,
                40: _verify_noah3k_password, }

def update_password(uid, password):
    val = dict(uid = uid)
    result = db.select('Users', val, where='uSerial = $uid')
    user = None
    try:
        user = result[0]
    except:
        return False
    return db.update('Users', where = 'uSerial = $uid', uPasswd = _generate_noah3k_password(password)) > 0

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
    print '"%s"' % username
    val = dict(username = username)
    result = db.select('Users', val, where='uId = $username')
    user = None
    try:
        user = result[0]
    except:
        return (False, 'NO_SUCH_USER')
    if not password_set[len(user.uPasswd)](user.uPasswd, password):
        return (False, 'WRONG_PASSWORD')
    #if len(user.uPassword) < 40:
    #    update_password(user.uSerial, password)
    return (True, 'LOGIN_SUCCESS')

def register(member):
    """
    회원 등록. 회원 정보를 포함하고 있는 딕셔너리를 던져 주면
    회원 등록을 시도한다. 실패했을 경우 상황에 따른 오류 코드를 반환한다.

    member에 오는 키와 값은 다음과 같다.

    - username: 사용자 ID
    - password: 사용자 암호. 두 번 입력받는 걸 검증하는 역할은 프론트엔드에서 담당한다.
    - nickname: 별명.
    - signature: 글 뒤에 붙는 시그.
    - introduction: 회원 정보 페이지에 뜨는 자기 소개.
    - avatar: 아바타 파일이 저장되어 있는 디스크 상 경로.

    @type member: dict
    @param member: 회원 정보 딕셔너리.
    @rtype tuple
    @return: 회원 등록 성공 여부(T/F)와 오류 코드(실패 시)를 포함하는 튜플.
    """
    pass

def get_user(uid):
    """
    사용자 정보를 가져온다. 사용자 UID를 사용하므로, 사용자
    이름이나 세션으로 조회하려면 L{_get_uid_from_username},
    L{_get_uid_from_session_key} 같은 함수를 써서 UID로 변환해야 한다.

    @type uid: int
    @param uid: 사용자 UID.
    @rtype tuple
    @return: 사용자 존재 여부(T/F)와 사용자 정보 딕셔너리(성공 시) 또는 오류 코드(실패 시)를 포함하는 튜플.
    """
    val = dict(uid = uid)
    result = db.select('Users', val, where="uSerial = $uid")
    try:
        retvalue = result[0]
    except:
        return (False, {})
    else:
        return (True, retvalue)

def modify_user(username, member):
    """
    회원 정보 수정. 세션 키를 통해서 현재 사용자를 확인하며,
    C{username}으로 지정한 사용자와 같아야 한다. 단 시삽은 임의
    회원의 정보를 수정할 수 있다. C{member} 딕셔너리는 수정할 정보로,
    형식은 L{register}를 참고한다. 빈 값이 들어오면 삭제를 의미하므로,
    기존 정보를 수정하려면 정보를 그대로 넘겨줘야 한다.

    @type session_key: string
    @param session_key: 세션 키.
    @type username: string
    @param username: 수정할 회원의 사용자 이름.
    @type member: dict
    @param member: 회원 정보 딕셔너리.
    @rtype tuple
    @return: 정보 수정 성공 여부(T/F)와 오류 코드(실패 시)를 포함하는 튜플.
    """
    pass

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
    except:
        return -1
    else:
        return retvalue
    pass

