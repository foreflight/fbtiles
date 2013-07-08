#!/usr/bin/env python
import os
import sqlite3
import sys
import unittest


from .. fbtiles import FBTiles


CWD = os.path.abspath(os.path.dirname(__file__))


class FBTilesTestCase(unittest.TestCase):
    ''' Test cases for FBTiles object. '''

    def setUp(self):
        ''' Default database path for these test cases. '''
        self.db_abspath = os.path.join(CWD,'test.db')
        if os.path.exists(self.db_abspath):
            os.unlink(self.db_abspath)

    def tearDown(self):
        ''' Clean up any left over database files. '''
        if os.path.exists(self.db_abspath):
            os.unlink(self.db_abspath)

    def test_basic_connection(self):
        ''' Test that a basic, empty FBTiles database can be created. '''
        self.assertFalse(os.path.exists(self.db_abspath))

        fbt = FBTiles(self.db_abspath, connect=True)
        # verify that the db file is created
        self.assertTrue(os.path.exists(self.db_abspath))
        fbt.close()
        self.assertTrue(os.path.exists(self.db_abspath))

        # TODO: add tests to verify that the tables were created but have no
        # rows.

    def test_adding_tile(self):
        '''
        Tests adding a row with a basic tile and no collared counterpart tile.
        '''
        fbt = FBTiles(self.db_abspath, connect=True)
        where = { 'x': 293, 'y': 200, 'z': 7 }
        tile_fn = 'tile.jpg'
        fbt.add_tile(tile_fn, where['x'], where['y'], where['z'])
        fbt.close()

        # Verify that we have a single row in the tiles database and an entry
        # in the bounds table.
        conn = sqlite3.connect(self.db_abspath)
        cur = conn.cursor()

        # verify tiles
        cur.execute("SELECT * FROM tiles")
        data = cur.fetchone()
        self.assertNotEqual(data, None)
        self.assertEqual(len(data), 8)
        self.assertEqual(data[0], 504403236917084360L)
        self.assertEqual(data[1], 7)
        self.assertEqual(data[2], 293)
        self.assertEqual(data[3], 200)
        # index 4 is BLOB object instance; can't just compare value
        self.assertEqual(data[5], 1)    # datatype index id (for jpg)
        self.assertEqual(data[6], None)
        self.assertEqual(data[7], None)

        # verify bounds
        cur.execute("SELECT * FROM bounds")
        data = cur.fetchone()
        expected = (7, 0, 293, 200, 293, 200)
        self.assertEqual(data, expected)

    def test_adding_duplicate(self):
        ''' Verify you can't add same tile multiple times. '''
        fbt = FBTiles(self.db_abspath, connect=True)
        where = { 'x': 293, 'y': 200, 'z': 7 }
        tile_fn = 'tile.jpg'
        # attempt to add the same tile (same x, y, z) multiple times
        fbt.add_tile(tile_fn, where['x'], where['y'], where['z'])
        fbt.add_tile(tile_fn, where['x'], where['y'], where['z'])
        fbt.add_tile(tile_fn, where['x'], where['y'], where['z'])
        fbt.add_tile(tile_fn, where['x'], where['y'], where['z'])
        fbt.close()

        # Verify that we have a single row in the tiles database and an entry
        # in the bounds table.
        conn = sqlite3.connect(self.db_abspath)
        cur = conn.cursor()

        # verify tiles
        cur.execute("SELECT * FROM tiles")
        rows = cur.fetchall()
        self.assertEqual(len(rows), 1)
        cur.execute("SELECT * FROM bounds")
        rows = cur.fetchall()
        self.assertEqual(len(rows), 1)

    def test_bounds(self):
        ''' Test that max X/Y and min X/Y values are correct. '''

        # We add a bunch of random values for x, y at various zooms
        bounds = {
            2: {
                'x': [19, 2, 94, 63, 66, 37, 51],
                'y': [66, 62, 12, 48, 77, 0, 73],
            },
            5: {
                'x': [40, 42, 62, 46, 30, 66, 57],
                'y': [96, 24, 50, 31, 93, 92, 89],
            },
        }
        fbt = FBTiles(self.db_abspath, connect=True)
        tile_fn = 'tile.jpg' # reuse same blob each time; doesn't matter
        for z,zdata in bounds.iteritems():
            for i in range(0,7):
                fbt.add_tile(tile_fn, zdata['x'][i], zdata['y'][i], z)
        fbt.close()

        # Now verify that the database has what we expect
        conn = sqlite3.connect(self.db_abspath)
        cur = conn.cursor()

        # verify tiles table
        cur.execute("SELECT * FROM tiles")
        rows = cur.fetchall()
        self.assertEqual(len(rows), len(bounds[2]['x'])*len(bounds.keys()))

        # verify bounds table
        cur.execute("SELECT * FROM bounds")
        rows = cur.fetchall()
        self.assertEqual(len(rows), len(bounds.keys()))

        for z in bounds.keys():
            cur.execute("""SELECT minX,maxX,minY,maxY
                        FROM bounds WHERE zoom=? AND collared=?""",
                        (z, 0))
            row = cur.fetchone()
            print 'test row =', row
            self.assertEqual(min(bounds[z]['x']), row[0])
            self.assertEqual(max(bounds[z]['x']), row[1])
            self.assertEqual(min(bounds[z]['y']), row[2])
            self.assertEqual(max(bounds[z]['y']), row[3])


    def test_adding_collared_tile(self):
        '''
        Tests adding both a regular tile and collared tile.
        '''
        fbt = FBTiles(self.db_abspath, connect=True)
        where = { 'x': 293, 'y': 200, 'z': 7 }
        tile_fn = 'tile.jpg'
        fbt.add_tile(tile_fn, where['x'], where['y'], where['z'])
        fbt.add_tile(tile_fn, where['x'], where['y'], where['z'],collared=True)
        fbt.close()

        # Verify that we have a single row in the tiles database and an entry
        # in the bounds table.
        conn = sqlite3.connect(self.db_abspath)
        cur = conn.cursor()

        # verify tiles
        cur.execute("SELECT * FROM tiles")
        rows = cur.fetchall()
        self.assertEqual(len(rows), 1)      # single row for both
        row = rows[0]
        self.assertNotIn(None, row) # verify no None values present

        # verify bounds
        cur.execute("SELECT * FROM bounds")
        rows = cur.fetchall()
        self.assertEqual(len(rows), 2)      # two bounds rows, however
