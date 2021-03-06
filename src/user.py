#!/usr/bin/python
# -*- coding: utf-8 -*-

import config
from config import db
import web
import crypt, hashlib, hmac
import util
import i18n
import datetime, time
import random, string
_ = i18n.custom_gettext

import os, magic, StringIO
pil = True
try:
    from PIL import Image
except:
    pil = False

"""
사용자 로그인, 로그아웃, 세션을 관리한다.
"""
def _verify_noah1k_password(to_verify, password):
    # UNIX crypt 함수. password가 seed, username이 텍스트.
    # 더 이상 생성할 필요도 이유도 없음.
    pass1 = crypt.crypt(password, password)
    return to_verify == crypt.crypt(password, pass1)

def _generate_noah2k_password(password):
    # MySQL <4.1.1 password() 함수의 파이썬 구현.
    # noah3k 런칭 이전까지는 생성할 필요가 있음.
    # noah2k의 웹 폼에는 암호 입력이 최대 16글자까지로 제한되어 있음.
    # 따라서 암호 검증 시에도 이를 고려하여야 함.
    if len(password) > 16:
        password = password[0:16]
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

def _verify_noah3k_password(to_verify, password):
    return to_verify == _generate_noah3k_password(password)

def generate_password(password):
    return _generate_noah3k_password(password)

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
    result = db.query('SELECT * FROM Users WHERE uId = $username COLLATE utf8_general_ci', vars = locals())
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
        ret = db.update('Users', vars=val, where = 'uSerial = $uid', uPasswd = generate_password(password)) 
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

def login(username, password, is_hash = False):
    """
    로그인 처리. 사용자 ID와 암호를 평문으로 입력받은 다음,
    해당하는 사용자가 있는 지 확인하고 존재하면 세션 키,
    존재하지 않으면 오류 코드를 돌려 준다.

    @type username: string
    @param username: 사용자 ID.
    @type password: string
    @param password: 암호. 평문으로 전송되어야 한다.
    @type is_hash: bool
    @param is_hash: 인자로 넘겨준 암호가 해시인지 여부.
    @rtype tuple
    @return: 로그인 성공 여부(T/F)와 사용자 또는 오류 코드(실패 시)를 포함하는 튜플.
    """
    val = dict(username = username)
    result = db.query('SELECT * FROM Users WHERE uId = $username COLLATE utf8_general_ci',
            vars = locals())
    user = None
    try:
        user = result[0]
    except IndexError:
        return (False, _('NO_SUCH_USER'))
    if is_hash:
        if user.uPasswd == password:
            return (True, user)
        else:
            return (False, _('INVALID_PASSWORD'))
    else:
        if not password_set[len(user.uPasswd)](user.uPasswd, password):
            return (False, _('INVALID_PASSWORD'))
        if len(user.uPasswd) < 64:
            update_password(user.uSerial, password)
        return (True, user)

def add_login_info(username, password_hash, referer, persistent):
    t = db.transaction()
    try:
        result = db.insert('login_temp', id=username, password_hash=password_hash,
                logintime = web.SQLLiteral('NOW()'), referer=referer,
                persistent = persistent)
    except:
        t.rollback()
        return -1
    else:
        t.commit()
    result = db.select('login_temp', locals(), where='id = $username')
    return int(time.mktime(result[0].logintime.timetuple()))

def get_login_info(username, timestamp):
    time = datetime.datetime.fromtimestamp(timestamp)
    val = dict(username=username, time=time)
    result = db.select('login_temp', val, where='logintime=$time AND id=$username')
    if len(result) <= 0:
        return None
    else:
        return result[0]

def remove_login_info(username, timestamp):
    time = datetime.datetime.fromtimestamp(timestamp)
    val = dict(username=username, time=time)
    t = db.transaction()
    try:
        result = db.delete('login_temp', vars=val, where='logintime=$time AND id=$username')
    except:
        t.rollback()
        return False
    else:
        t.commit()
        return True

def get_owned_board(uid):
    # 모든 정보가 돌아옴.
    val = dict(uid = uid)
    result = db.select('Boards', val, where='uSerial = $uid', order = 'bType, bName')
    return result

def get_favorite_board_with_detail(uid):
    val = dict(uid = uid)
    result = db.query('SELECT * FROM Boards INNER JOIN Favorites WHERE Favorites.uSerial = $uid AND Boards.bSerial = Favorites.bSerial ORDER BY bType, bName', val)
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
        return (False, _('NO_SUCH_USER'))
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
        return (False, _('INVALID_USERNAME'))
    if _get_uid_from_username(member['username']) > 0:
        return (False, _('ID_ALREADY_EXISTS'))
    t = db.transaction()
    try:
        result = db.insert('Users', uNick = member['nick'], uEmail = member['email'],
                uId = member['username'], uPasswd = generate_password(member['password']),
                uDatetime = web.SQLLiteral('NOW()'), uSig = '', uPlan = '')
    except:
        t.rollback()
        return (False, _('DATABASE_ERROR'))
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
    profile_image_path = os.path.join(config.pi_disk_path, '%s.png' % member['user_id'])
    m = magic.Magic(mime = True)
    mime_type = m.from_buffer(member['profile_image'])
    if member['delete_profile_image']:
        if os.path.exists(profile_image_path):
            os.remove(profile_image_path)
    else:
        if mime_type.startswith('image'):
            image_file = StringIO.StringIO(member['profile_image'])
            if pil:
                pi = Image.open(image_file)
                r = pi.resize(config.pi_size, Image.ANTIALIAS)
                r.save(profile_image_path)

    t = db.transaction()
    try:
        if member['password']:
            result = db.update('Users', vars=member, where='uSerial = $user_id',
                    uNick = member['nick'], uEmail = member['email'],
                    uSig = member['sig'], uPlan = member['introduction'],
                    uHomepage = member['homepage'],
                    language = member['language'],
                    theme = member['theme'],
                    uPasswd = generate_password(member['password']))
        else:
            result = db.update('Users', vars=member, where='uSerial = $user_id',
                    uNick = member['nick'], uEmail = member['email'],
                    uHomepage = member['homepage'],
                    uSig = member['sig'], uPlan = member['introduction'],
                    language = member['language'],
                    theme = member['theme'])
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
        return (False, _('HAS_BOARD'))

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
        return (False, _('DATABASE_ERROR'))
    else:
        t.commit()
    return (True, _('SUCCESS'))

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

def update_new_article_hit(uid):
    t = db.transaction()
    try:
        result = db.update('Users', vars=locals(), where = 'uSerial = $uid',
                new_article_hit = web.SQLLiteral('new_article_hit + 1'))
    except:
        t.rollback()
        return False
    else:
        t.commit()
    return result

def update_new_article_none_hit(uid):
    t = db.transaction()
    try:
        result = db.update('Users', vars=locals(), where = 'uSerial = $uid',
                new_article_none_hit = web.SQLLiteral('new_article_none_hit + 1'))
    except:
        t.rollback()
        return False
    else:
        t.commit()
    return result

###
def get_subscription_board_with_detail(uid):
    val = dict(uid = uid)
    result = db.query('SELECT * FROM Boards INNER JOIN Subscriptions WHERE Subscriptions.uSerial = $uid AND Boards.bSerial = Subscriptions.bSerial ORDER BY bType, bName', val)
    return result

def get_subscription_board(uid):
    # bSerial만 돌아오므로 적절한 가공이 필요함.
    val = dict(uid = uid)
    result = db.select('Subscriptions', val, where='uSerial = $uid')
    return result

def is_subscribed(uid, board_id):
    val = dict(uid = uid, board_id = board_id)
    result = db.query('SELECT COUNT(*) AS f FROM Subscriptions WHERE uSerial=$uid AND bSerial=$board_id', val);
    return result[0].f > 0

def add_subscription_board(uid, board_id):
    t = db.transaction()
    try:
        result = db.insert('Subscriptions', uSerial = uid, bSerial = board_id, lastSubscriptedDate=web.SQLLiteral('NOW()'))
    except:
        t.rollback()
        return False
    else:
        t.commit()
    return result

def remove_subscription_board(uid, board_id):
    val = dict(uid = uid, board_id = board_id)
    t = db.transaction()
    try:
        result = db.delete('Subscriptions', vars=val, where='uSerial = $uid AND bSerial = $board_id')
    except:
        t.rollback()
    else:
        t.commit()
    return result

def read_article(uid, aSerial):
    val = dict(uid = uid, aSerial = aSerial)
    db.delete('UserArticles', vars=val, where='uSerial = $uid and aSerial = $aSerial')

def read_all_articles(uid):
    val = dict(uid = uid)
    db.delete('UserArticles', vars=val, where='uSerial = $uid')

def is_unreaded_article(uid, aSerial):
    result = db.select('UserArticles', dict(uid=uid, aSerial=aSerial), where='uSerial = $uid and aSerial = $aSerial')
    return len(result)

def get_unreaded_articles(uid, limit = -1):
    update_unreaded_articles(uid)
    if limit < 0:
        result = db.query('SELECT * FROM Articles INNER JOIN UserArticles WHERE Articles.aSerial = UserArticles.aSerial AND UserArticles.uSerial = $uSerial', dict(uSerial = uid))
    else:
        result = db.query('SELECT * FROM Articles INNER JOIN UserArticles WHERE Articles.aSerial = UserArticles.aSerial AND UserArticles.uSerial = $uSerial LIMIT $limit', dict(uSerial = uid, limit = limit))
    return result

def update_unreaded_articles_board(uid, bSerial):
    subscription = db.select('Subscriptions', dict(uid=uid, bSerial=bSerial), where='uSerial=$uid and bSerial=$bSerial')
    if len(subscription) is not 0:
        sub = subscription[0]
        val = dict(uSerial = uid, bSerial = sub.bSerial, subscriptedDate = sub.lastSubscriptedDate)
        db.query('INSERT ignore INTO UserArticles (SELECT $uSerial, aSerial, NOW() FROM Articles WHERE bSerial = $bSerial AND aUpdatedDatetime > $subscriptedDate)', val)

        db.update('Subscriptions', vars=dict(uSerial=uid, bSerial=sub.bSerial), where='uSerial=$uSerial and bSerial = $bSerial', lastSubscriptedDate = web.SQLLiteral('NOW()'))

def update_unreaded_articles(uid):
    for subscription in get_subscription_board(uid):
        val = dict(uSerial = uid, bSerial = subscription.bSerial, subscriptedDate = subscription.lastSubscriptedDate)
        result = db.query('insert ignore into UserArticles (select $uSerial, aSerial, NOW() from Articles where bSerial = $bSerial and aUpdatedDatetime > $subscriptedDate)', val)

    db.update('Subscriptions', vars=dict(uSerial = uid), where = 'uSerial = $uSerial', lastSubscriptedDate = web.SQLLiteral('NOW()'))

def has_profile_image(uid):
    return os.path.exists(os.path.join(config.pi_disk_path, '%s.png' % uid))

def get_user_from_email(mail):
    result = db.select('Users', vars=locals(), where='uEmail = $mail')
    return result

def get_password_salt(uid):
    # 암호 찾기 명령 실행 시 나오는 것.
    # 마지막 로그인 시간과 사용자 ID의 조합이므로 로그인 한 번 하면 값이 변경됨.
    u = get_user(uid)
    if not u[0]:
        return None
    salt = str(int(time.mktime(u[1].uLastLogin.timetuple()))) + u[1].uId
    return _generate_noah3k_password(salt)

def generate_random_password(length = 8):
    chars = string.letters + string.digits
    return ''.join([random.choice(chars) for i in range(length)])

def get_article_list_by_user(uid, page_size, page_number):
    val = dict(uid = uid)
    total_article = get_post_count(uid)
    if total_article < 0:
        return []
    last_page = (total_article + page_size - 1) / page_size
    if not (page_number >= 1 and page_number <= last_page):
        return []
    begin = page_size * (page_number - 1)
    val = dict(uid = uid, begin = begin, page_size = page_size)
    result = db.query('''SELECT * FROM Articles
NATURAL LEFT JOIN (SELECT aSerial, COUNT(*) AS comment_count FROM Comments GROUP BY aSerial) AS comment_group
NATURAL LEFT JOIN (SELECT bSerial, bName AS board_name FROM Boards) AS board_group
WHERE uSerial=$uid
ORDER BY aDatetime DESC
LIMIT $begin, $page_size''', val)
    return result
