# -*- coding: utf-8 -*-
import json

import sys

from database import Database
import config

class Exporter:
    """
    This class has many helpers to get the content from the DB
    """

    def __init__(self):
        self.db = Database()

    def close(self):
        self.db.stop_db()

    def get_feed(self, page = 1):
        """
        Returns the feed.
        """
        offset = (page - 1) * config.elements_per_page

        try:
            self.db.cursor.execute("SELECT * FROM Media ORDER BY timestamp DESC LIMIT ? OFFSET ?", (config.elements_per_page, offset,))
            return(self.db.cursor.fetchall())
        except:
            exit("Error: Getting the feed has failed.")

    def get_feed_count(self):
        """
        Returns the feed count.
        """
        try:
            self.db.cursor.execute("SELECT count(*) FROM Media")
            return(self.db.cursor.fetchone()[0])
        except:
            exit("Error: Getting the feed details has failed.")

    def get_memory_feed(self, memory_list, page = 1):
        """
        Returns the feed.
        """
        offset = (page - 1) * config.elements_per_page

        #try:
        query = "SELECT * FROM Media WHERE id IN (%s) ORDER BY timestamp DESC LIMIT ? OFFSET ?" % ','.join('?' for i in memory_list)
        self.db.cursor.execute(query, memory_list + (config.elements_per_page, offset))


        return(self.db.cursor.fetchall())
        #except:
            #exit("Error: Getting the feed has failed.")

    def get_user_feed(self, user_id, page = 1):
        """
        Returns the feed for an user.
        """

        try:
            user_id
        except:
            exit("Error : user ID not supplied")

        offset = (page - 1) * config.elements_per_page

        try:
            self.db.cursor.execute("SELECT * FROM Media WHERE owner = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?", (user_id, config.elements_per_page, offset,))
            return(self.db.cursor.fetchall())
        except:
            exit("Error: Getting the timestamp of %s has failed." % user_id)

    def get_user_feed_count(self, user_id):
        """
        Returns the feed count for an user.
        """

        try:
            user_id
        except:
            exit("Error : user ID not supplied")

        try:
            self.db.cursor.execute("SELECT count(*) FROM Media WHERE owner = ?", (user_id,))
            return(self.db.cursor.fetchone()[0])
        except:
            exit("Error: Getting the feed count for user %s has failed." % user_id)

    def get_user_profile(self, user_id):
        """
        Returns the feed for an user.
        """

        try:
            user_id
        except:
            exit("Error : user ID not supplied")

        try:
            self.db.cursor.execute("SELECT * FROM Accounts WHERE id = ?", (user_id,))
            return(self.db.cursor.fetchone())
        except:
            exit("Error: Getting the profile for user %s has failed." % user_id)

    def get_user_id_from_username(self, username):
        """
        Returns the id for an user's username.
        """

        try:
            username
        except:
            exit("Error : username not supplied")

        try:
            self.db.cursor.execute("SELECT * FROM Accounts WHERE username = ?", (username,))
            return(self.db.cursor.fetchone()[0])
        except:
            exit("Error: Getting the ID for %s has failed." % username)

    def get_username_from_user_id(self, user_id):
        """
        Returns the username for an user's id.
        """
        try:
            user_id
        except:
            exit("Error : user ID not supplied")

        try:
            self.db.cursor.execute("SELECT * FROM Accounts WHERE id = ?", (user_id,))
            return(self.db.cursor.fetchone()[1])
        except:
            exit("Error: Getting the ID for %s has failed." % user_id)

    def get_media_id_from_shortcode(self, shortcode):
        """
        Returns the id for the media shortcode.
        """

        try:
            shortcode
        except:
            exit("Error : user ID not supplied")

        try:
            self.db.cursor.execute("SELECT * FROM Media WHERE shortcode = ?", (shortcode,))
            return(self.db.cursor.fetchone()[0])
        except:
            exit("Error: Getting the ID for media %s has failed." % shortcode)

    def get_media_from_shortcode(self, media_shortcode):
        """
        Returns a media object from ID.
        """

        try:
            media_shortcode
        except:
            exit("Error : shortcode not supplied")

        try:
            self.db.cursor.execute("SELECT * FROM Media WHERE shortcode = ?", (media_shortcode,))
            return(self.db.cursor.fetchone())
        except:
            exit("Error: Getting the media for %s has failed." % media_shortcode)

