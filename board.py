#!/usr/bin/python
# -*- coding: utf-8 -*-

import config
import web

class board:
    """
    게시판 클래스. 데이터베이스 상에 저장된 게시판에 접근한다.
    """
    def __init__(self):
        self.db = web.database(dbn=config.db_type, user=config.db_user,
                pw = config.db_password, db = config.db_name,
                host=config.db_host, port=int(config.db_port))

    def _get_board_id_from_path(self, path):
        if path != "":
            path = '/%s' % path
        val = dict(board_path = path)
        result = self.db.select('Boards', val, where="bName = $board_path")
        try:
            retvalue = result[0]["bSerial"]
        except:
            return -1
        else:
            return retvalue

    def _get_article_count(self, board_id):
        val = dict(board_id = board_id)
        result = self.db.query('SELECT COUNT(*) AS article_count FROM Articles WHERE bSerial=$board_id', val);
        return result[0].article_count

    def _get_total_page_count(self, board_id, page_size):
        total_article = self._get_article_count(board_id)
        return  (total_article + page_size -1) / page_size

    def create_board(self, session_key, parent, settings):
        pass

    def edit_board(self, session_key, board_id, settings):
        pass

    def delete_board(self, session_key, board_id):
        pass

    def get_board_info(self, board_id):
        # board_id 보드의 정보를 가져온다.
        val = dict(board_id = board_id)
        result = self.db.select('Boards', val, where="bSerial = $board_id")
        try:
            retvalue = result[0]
        except:
            return None
        else:
            return retvalue

    def get_child(self, board_id):
        # board_id 보드의 자식 보드를 가져온다.
        val = dict(board_id = board_id)
        result = self.db.select('Boards', val, where='bParent = $board_id', order='bName ASC')
        return result

    def get_parent(self, board_id):
        val = dict(board_id = board_id)
        result = self.db.select('Boards', val, what='bParent', where='bSerial = $board_id')
        try:
            retvalue = result[0]
        except:
            return None
        else:
            return retvalue['bParent']

    def get_article_list(self, session_key, board_id, page_size, page_number):
        total_article = self._get_article_count(board_id)
        last_page = self._get_total_page_count(board_id, page_size)
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
        result = self.db.select('Articles', val, where='bSerial = $board_id AND aIndex >= $begin_index AND aIndex <= $end_index')
        return result


    def get_article(self, session_key, board_id, article_id):
        val = dict(board_id = board_id, article_id = article_id)
        result = self.db.select('Articles', val, where='bSerial = $board_id AND aSerial = $article_id')
        return result

    def write_article(self, session_key, board_id, article):
        pass

    def edit_article(self, session_key, article_id, article):
        pass

    def delete_article(self, session_key, article_id):
        pass

    def write_comment(self, session_key, article_id, comment):
        pass

    def delete_comment(self, session_key, comment_id):
        pass

