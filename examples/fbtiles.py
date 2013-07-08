#!/usr/bin/env python
'''
Example FBTiles Object that will _WRITE_ an FBTiles database.

Implementing operations that READ the FBTiles format is left as an exercise
for the reader.
'''
import os
from os.path import splitext
import re
import sqlite3
import subprocess
import sys


class FBTiles(object):
    ''' Object to help Write FBTiles format to SQLite database. '''

    db_file = 'db.fbtiles'  # default fbtiles file name
    _connection = None      # sqlite db connection object
    _cursor = None          # sqlite db cursor

    datatypes = ['JPG', 'PNG']  # NOTE: in database, 0 position equals 1 for id

    def __init__(self, filename, connect=True):
        if connect:
            self.connect(sqlite_file=filename)
        super(FBTiles, self).__init__()

    def connect(self, sqlite_file=None):
        ''' Connect to sqlite db file and return cursor '''
        if sqlite_file:
            self.db_file = sqlite_file
        dbf = self.db_file

        print "connecting to:", dbf
        init_schema = not os.path.exists(dbf) # check before connect
        self._connection = sqlite3.connect(dbf)
        self._cursor = self._connection.cursor()
        if init_schema:
            print "creating schema"
            self.db_create_schema()
        return self._cursor

    def close(self):
        ''' Perform action of closing the database. '''
        if not self.closed():
            self._connection.commit()
            self._connection.close()
            self._cursor = None
            self._connection = None
            print "closing database:", self.db_file
        else:
            print "WARNING: close not necessary; database already closed"

    def closed(self):
        ''' Returns boolean of whether database is currently closed or not. '''
        return self._connection is None and self._cursor is None

    @classmethod
    def get_tile_key(cls, tileX, tileY, tileZoom):
        zoom = int(tileZoom) & 0xff # 8bits, 256 levels
        x = int(tileX) & 0xfffffff # 28 bits
        y = int(tileY) & 0xfffffff # 28 bits
        return (zoom << 56) | (x << 28) | (y << 0)

    def db_create_schema(self):
        ''' Create database tables for FBTiles database. '''

        self._cursor.execute("""CREATE TABLE [datatypes] (id INTEGER PRIMARY KEY,
                                              datatype TEXT UNIQUE)""")
        self._connection.commit()
        for id in range(0,len(self.datatypes)):
            # NOTE: ids in database are +1 as compared to python list index.
            # Really, IDs can be any unique integer value, but for simplicity
            # we manually set them here and then because we know the ID values,
            # we simply refer to them later rather than running a query on the
            # datatypes table to determine what ID corresponds to the format we
            # are going to insert.
            self._cursor.execute("""INSERT INTO [datatypes] VALUES (?,?)""",
                            (id+1, self.datatypes[id]))
        self._connection.commit()
        self._cursor.execute("""CREATE TABLE tiles  (tilekey INTEGER PRIMARY KEY,
                                          zoom_level INTEGER,
                                          tile_row INTEGER,
                                          tile_column INTEGER,
                                          tile_data BLOB,
                                          tile_datatypes_id INTEGER,
                                          tile_collar_data BLOB,
                                          tile_collar_datatypes_id INTEGER,
                FOREIGN KEY (tile_datatypes_id) REFERENCES datatypes(id),
                FOREIGN KEY (tile_collar_datatypes_id) REFERENCES datatypes(id))""")
        # NOTE: the collared column is integer type but should be treated as
        # boolean, where 0=false, 1=true.
        self._cursor.execute("""CREATE TABLE bounds (zoom INTEGER,
                                                collared INTEGER,
                                                maxX INTEGER,
                                                maxY INTEGER,
                                                minX INTEGER,
                                                minY INTEGER,
                                                PRIMARY KEY (zoom, collared))""")
        # Create Indexes
        self._cursor.execute("""CREATE INDEX tiles_idx ON tiles(zoom_level,
                                                     tile_row,
                                                     tile_column)""")
        self._cursor.execute("""CREATE INDEX tiles_zoom_idx ON tiles(zoom_level)""")
        self._cursor.execute("""CREATE INDEX datatypes_idx ON datatypes(datatype)""")

    def get_datatype_id(self, datatype_str_value):
        ''' Return the ID for the value in datatypes table. '''

        # NOTE: for the given context, the in-memory mapping is equal to the
        # database, so we just use it instead of issuing a database query here
        # to find the ID for the datatypes format we are interested in. That's
        # primarily because we are using FBTiles to WRITE a database and can
        # guarantee that it's identical. If we ever get into a situation where
        # we are READing a database, this routine will need to issue a query
        # rather than rely on python values because the ultimate authority
        # would be the database we are reading, not this internal variable.

        # NOTE: database ids are +1 compared to python list indexes
        return self.datatypes.index(datatype_str_value)+1

    def add_tile(self, tile_filename, x, y, z, collared=False):
        # Get index for value of datatype using uppercase file suffix
        # NOTE: Assumes either .jpg or .png suffix.
        dt_id = self.get_datatype_id(splitext(tile_filename)[1][1:].upper())

        # Read the tile data for blob
        f = open(tile_filename, 'rb')
        data = f.read()
        f.close()

        collared = bool(collared)

        if collared:
            if self._has_row(x,y,z):
                self._cursor.execute("""UPDATE tiles SET tile_collar_data=?,
                                tile_collar_datatypes_id=? WHERE zoom_level=?
                                AND tile_row=? AND tile_column=?""",
                                (buffer(data), dt_id, z, x, y) )
            else:
                sql = "INSERT INTO tiles VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
                key = FBTiles.get_tile_key(x,y,z)
                self._cursor.execute(sql, (key, z, x, y, None, None,
                                      buffer(data), dt_id))
        else:
            if self._has_row(x,y,z):
                self._cursor.execute("""UPDATE tiles SET tile_data=?,
                                tile_datatypes_id=? WHERE zoom_level=?
                                AND tile_row=? AND tile_column=?""",
                                (buffer(data), dt_id, z, x, y) )
            else:
                sql = "INSERT INTO tiles VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
                key = FBTiles.get_tile_key(x,y,z)
                self._cursor.execute(sql, (key, z, x, y, buffer(data),
                                      dt_id, None, None))
        self._connection.commit()

        # determine if we are to update or create a new bounds entry for tile
        k = (z, int(collared))
        self._cursor.execute("""SELECT minX,maxX,minY,maxY
                        FROM bounds WHERE zoom=? AND collared=?""",
                        k)
        row = self._cursor.fetchone()
        if row:
            # we have one; need to update ONLY IF NEEDED
            x_range = range(row[0], row[1]+1)
            y_range = range(row[2], row[3]+1)

            if not x in x_range:
                # x is outside of existing range; update bounds for x
                if x < x_range[0]:
                    x_range.insert(0,x)
                if x > x_range[-1]:
                    x_range.append(x)
                self._cursor.execute("""UPDATE [bounds] SET minX=?, maxX=?
                                WHERE zoom=? AND collared=?""",
                                (x_range[0], x_range[-1], k[0], k[1]))
                self._connection.commit()

            if not y in y_range:
                # y is outside of eyisting range; update bounds for y
                if y < y_range[0]:
                    y_range.insert(0,y)
                if y > y_range[-1]:
                    y_range.append(y)
                self._cursor.execute("""UPDATE [bounds] SET minY=?, maxY=?
                                WHERE zoom=? AND collared=?""",
                                (y_range[0], y_range[-1], k[0], k[1]))
                self._connection.commit()
        else:
            # no existing row; create one
            v = (k[0], k[1], x, y, x, y)
            self._cursor.execute("INSERT INTO bounds VALUES (?, ?, ?, ?, ?, ?)", v)
            self._connection.commit()

    def _has_row(self, x, y, z):
        ''' Is there a row in the fbtiles for this x/y/z coord ? '''
        k = FBTiles.get_tile_key(x,y,z)
        self._cursor.execute("SELECT tilekey FROM tiles WHERE tilekey = ?", (k,))
        data = self._cursor.fetchone()
        return data is not None

