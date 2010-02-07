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
        result = self.db.select('Boards', val, where="bParent = $board_id", order="bName ASC")
        return result

    def get_parent(self, board_id):
        pass

    def get_article_list(self, session_key, board_id, page_size, page_number):
        pass

    def get_article(self, session_key, board_id, article_id):
        pass

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

