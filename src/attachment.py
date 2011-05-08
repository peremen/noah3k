#!/usr/bin/python
# -*- coding: utf-8 -*-

import config
import web
import user

import os, magic, StringIO, time

pil = True
try:
    from PIL import Image
except:
    pil = False

"""
첨부 파일 클래스. 디스크에 저장된 첨부 파일에 접근한다.
"""

# noah3k 첨부 파일 이름 형식: (uploads, thumbs_desktop, thumbs_mobile)/(article_id)/(attachment_filename)
 
def get_attachment(article_id):
    path = os.path.join(config.attachment_disk_path, str(article_id))
    file_list = []
    file_list_2 = []
    try:
        file_list = os.listdir(path)
    except OSError:
        return []
    for f in file_list:
        stats = os.stat(os.path.join(config.attachment_disk_path, str(article_id), f))
        lastmod_date = time.localtime(stats[8])
        file_list_2.append((lastmod_date, f))
        
    file_list_2.sort()
    return file_list_2

def get_thumbnail(article_id, mobile):
    if mobile:
        path = os.path.join(config.thumbnail_mobile_disk_path, str(article_id))
    else:
        path = os.path.join(config.thumbnail_desktop_disk_path, str(article_id))
    file_list = []
    file_list_2 = []
    try:
        file_list = os.listdir(path)
    except OSError:
        return []
    for f in file_list:
        stats = os.stat(os.path.join(config.attachment_disk_path, str(article_id), f))
        lastmod_date = time.localtime(stats[8])
        file_list_2.append((lastmod_date, f))
        
    file_list_2.sort()
    return file_list_2

def get_attachment_size(article_id, filename):
    path = os.path.join(config.attachment_disk_path, str(article_id), filename)
    if os.path.isfile(path):
        return os.path.getsize(path)
    else:
        return -1

def format_file_size(size):
    if size < 0:
        return u'잘못된 크기'
    suffixes = ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']
    if size < 1024:
        return u'%s B' % size
    for item in suffixes:
        rem = size % 1024
        val = size / 1024
        if val < 1024:
            return '%.2f %s' % (val+rem/1024., item)
        size = val
    return u'너무 큼'

def add_attachment(article_id, filename, content):
    # 첨부 파일을 디스크에 추가하고, 필요한 경우 썸네일을 생성함.
    # 같은 글에 같은 이름의 첨부 파일이 있는 경우, 새로운 파일에 _new를 덧붙임.

    # IE, bastard (파일 이름에 전체 경로가 올 때가 있음)
    filename = filename.replace('\\', '/')
    filename = os.path.basename(filename)
    # .htaccess 업로드하는 행위 방지
    if filename[0] == '.':
        filename = 'noah%s' % filename

    orig_path = os.path.join(config.attachment_disk_path, str(article_id))
    thumb_path = os.path.join(config.thumbnail_desktop_disk_path, str(article_id))
    thumb_m_path = os.path.join(config.thumbnail_mobile_disk_path, str(article_id))
    if not os.path.isdir(orig_path):
        os.mkdir(orig_path)
    if not os.path.isdir(thumb_path):
        os.mkdir(thumb_path)
    if not os.path.isdir(thumb_m_path):
        os.mkdir(thumb_m_path)

    while os.path.isfile(os.path.join(orig_path, filename)):
        ext_pos = filename.rfind(os.path.extsep)
        filename = '%s_new.%s' % (filename[0:ext_pos], filename[ext_pos+1:])

    m = magic.Magic(mime = True)
    mime_type = m.from_buffer(content)
    upload = open(os.path.join(orig_path, filename), 'wb')
    upload.write(content)
    upload.close()
    if mime_type.startswith('image'):
        image_file = StringIO.StringIO(content)
    if pil:
        thumb_desktop = Image.open(image_file)
        thumb_desktop.thumbnail(config.thumbnail_desktop_size, Image.ANTIALIAS)
        thumb_desktop.save(os.path.join(thumb_path, filename))

        image_file_2 = StringIO.StringIO(content)
        thumb_mobile = Image.open(image_file_2)
        thumb_mobile.thumbnail(config.thumbnail_mobile_size, Image.ANTIALIAS)
        thumb_mobile.save(os.path.join(thumb_m_path, filename))
    
def remove_attachment(article_id, filename):
    # 첨부 파일을 디스크에서 삭제함
    orig_path = os.path.join(config.attachment_disk_path, str(article_id))
    thumb_path = os.path.join(config.thumbnail_desktop_disk_path, str(article_id))
    thumb_m_path = os.path.join(config.thumbnail_mobile_disk_path, str(article_id))

    if os.path.isfile(os.path.join(orig_path, filename)):
        os.remove(os.path.join(orig_path, filename))
        if len(os.listdir(orig_path)) == 0:
            os.rmdir(orig_path)
    if os.path.isfile(os.path.join(thumb_path, filename)):
        os.remove(os.path.join(thumb_path, filename))
        if len(os.listdir(thumb_path)) == 0:
            os.rmdir(thumb_path)
    if os.path.isfile(os.path.join(thumb_m_path, filename)):
        os.remove(os.path.join(thumb_m_path, filename))
        if len(os.listdir(thumb_m_path)) == 0:
            os.rmdir(thumb_m_path)

def remove_all_attachment(article_id):
    # 모든 첨부 파일을 삭제함.
    orig_path = os.path.join(config.attachment_disk_path, str(article_id))
    thumb_path = os.path.join(config.thumbnail_desktop_disk_path, str(article_id))
    thumb_m_path = os.path.join(config.thumbnail_mobile_disk_path, str(article_id))

    if os.path.isdir(orig_path):
        for filename in os.listdir(orig_path):
            os.remove(os.path.join(orig_path, filename))
        os.rmdir(orig_path)
    if os.path.isdir(thumb_path):
        for filename in os.listdir(thumb_path):
            os.remove(os.path.join(thumb_path, filename))
        os.rmdir(thumb_path)
    if os.path.isdir(thumb_m_path):
        for filename in os.listdir(thumb_m_path):
            os.remove(os.path.join(thumb_m_path, filename))
        os.rmdir(thumb_m_path)
