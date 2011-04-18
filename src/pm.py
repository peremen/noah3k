#!/usr/bin/python
# -*- coding: utf-8 -*-

import config
from config import db
import web
import crypt, hashlib, hmac
import util
import i18n
import user
_ = i18n.custom_gettext

"""
사용자 개인 메시지를 관리한다. pm == Private Message
"""
def unread_count(uid):
    """
    UID로 지정한 사용자의 받은 편지함에 있는 읽지 않은 메일 갯수를 가져온다.

    @type uid: int
    @param uid: 사용자 ID.
    @rtype int
    @return: 읽지 않은 편지 갯수.
    """
    u = user.get_user(uid)
    if not u[0]:
        return -1
    result = db.query('SELECT COUNT(*) AS c FROM Mails WHERE mReceiverSerial=$uid AND mMark = 0', vars = locals());
    return result[0].c

def inbox(uid, page_no = 1, page_size = 20):
    """
    UID로 지정한 사용자의 받은 편지함을 가져온다.

    @type uid: int
    @param uid: 사용자 ID.
    @rtype list
    @return: 받은 편지 목록.
    """
    u = user.get_user(uid)
    if not u[0]:
        return u[1]
    result = db.select('Mails', locals(), where='mReceiverSerial = $uid',
            order = 'mDatetime DESC',
            limit = page_size, offset = (page_no - 1) * page_size)
    return result

def inbox_count(uid):
    u = user.get_user(uid)
    if not u[0]:
        return -1
    result = db.query('SELECT COUNT(*) AS c FROM Mails WHERE mReceiverSerial=$uid', vars = locals());
    return result[0].c

def outbox(uid, page_no = 1, page_size = 20):
    """
    UID로 지정한 사용자의 보낸 편지함을 가져온다.
    XXX: 현재의 DB 구조상 받은 사람이 지워 버리면 보낸 편지함에서도 사라진다.

    @type uid: int
    @param uid: 사용자 ID.
    @rtype list
    @return: 보낸 편지 목록.
    """
    u = user.get_user(uid)
    if not u[0]:
        return u[1]
    result = db.select('Mails', locals(), where='mSenderSerial = $uid',
            limit = page_size, offset = (page_no - 1) * page_size)
    return result

def get_mail(mail_id):
    # 지정한 편지를 가져온다.
    result = db.select('Mails', locals(), where='mSerial = $mail_id')
    try:
        retvalue = result[0]
    except IndexError:
        return None
    else:
        return retvalue

def mark_as_read(mail_id):
    t = db.transaction()
    try:
        result = db.update('Mails', vars=locals(), where='mSerial = $mail_id',
            mMark = 1)
    except:
        t.rollback()
        return False
    else:
        t.commit()
        return True

def send_mail(from_id, to_id, title, body):
    sender_info = user.get_user(from_id)
    receiver_info = user.get_user(to_id)
    if not sender_info[0]:
        return (False, _('INVALID_SENDER'))
    if not receiver_info[0]:
        return (False, _('INVALID_RECEIVER'))
    if title.strip() == '':
        return (False, _('EMPTY_TITLE'))
    if body.strip() == '':
        return (False, _('EMPTY_BODY'))

    t = db.transaction()
    try:
        db.insert('Mails', mSenderSerial = from_id,
                mReceiverSerial = to_id,
                mSenderId = sender_info[1].uId,
                mSenderNick = sender_info[1].uNick,
                mDatetime = web.SQLLiteral('NOW()'),
                mTitle = title,
                mContent = body)
    except:
        t.rollback()
        return (False, _('DATABASE_ERROR'))
    else:
        t.commit()
    return (True, _('SUCCESS'))

def delete_mail(mail_id):
    t = db.transaction()
    try:
        result = db.delete('Mails', vars=locals(), where='mSerial = $mail_id')
    except:
        t.rollback()
        return (False, _('DATABASE_ERROR'))
    else:
        t.commit()
        return (True, _('SUCCESS'))
