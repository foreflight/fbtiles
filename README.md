
Flight Bag Tiles
================


Overview
--------

The Flight Bag Tiles ("FBTiles") database format is an open database
specification invented by [ForeFlight](http://www.foreflight.com) for packaging
geo-referenced chart tiles in SQLite databases within the
[ForeFlight App](https://itunes.apple.com/us/app/foreflight-mobile/id333252638?mt=8)
but also for use in other mobile, desktop, and web applications. The FBTiles
specification is free for app makers, website developers, and national
Aeronautical Information Publishers ("AIPs") to use in order to accelerate
digital charting initiatives.


Database Specification
----------------------

To ensure compatiblity with devices, you must adhere to the specification as
documented below.

While no formal relationship exists between the
[MBTiles](http://www.mbtiles.org) specification and FBTiles, the FBTiles format
can be viewed as a superset of MBTiles. This is primarily due to the addition
of of what we call "collared" data. Collared data is so-called because it
relates to additional/alternate tiles that appear around the edges of the
original tiles found in the 'tiles' table.


Collared Data Concept Explained
-------------------------------

![Collared Tiles Example](images/collared.png)\


While collared tiles may suggest a certain geometry, don't be confused about
their general application or uses. You can simply view the additional collared
tile as an alternative tile data to display or not. In the screenshot example
above, the chart legends are stored as collared data, to be turned on or off as
legend data in the application.

The possibilities really are limitless; you could have the original map tiles
appear and then have a secondary set of tiles stored in the tile_collar_data
column that are like the original, completely different, or with additional markup.

In future versions of FBTiles these general concepts may be further enhanced to
allow for effecient delivery of multiple tile versions and formats.

Tables
------

Initial steps towards creating your own data in the FBTiles format involves
creating three new tables: `bounds`, `datatypes`, and `tiles`. In addition to
these three tables are the corresponding indexes that may be of use in your
application as well, but are specifically tailored to meet the requirements for
ForeFlight's application if you intend on using your FBTiles therein.

Additionally, while the basic SQL is database agnostic, for compatibility with
ForeFlight, you should adhere to SQLite (as shown below) as you will be
required to upload SQLite files for use within ForeFlight.


###Bounds Table

This table is used to specify the minimum/maximum X (column) values and
minimum/maximum Y (row) values for a given pair of Zoom and Collared queries.
This table aids in efficient lookups, and is used by the ForeFlight
application.

```sql
CREATE TABLE bounds (zoom INTEGER,
                     collared INTEGER,
                     maxX INTEGER,
                     maxY INTEGER,
                     minX INTEGER,
                     minY INTEGER,
                     PRIMARY KEY (zoom, collared));
```

Columns:

 * `zoom`: zoom levels are integer values `0-17`
 * `collared`: `0` or `1`, corresponding to True/False, collared or not
 * `maxX`: maximum X value for zoom-collared key pair.
 * `maxY`: maximum Y value for zoom-collared key pair.
 * `minX`: minimum X value for zoom-collared key pair.
 * `minY`: minimum Y value for zoom-collared key pair.


###Data Types Table

This table specifies what the format of the tile BLOB columns in the `tiles`
table represent.  While the specification is open-ended enough to allow for
`tile_data` or `tile_collar_data` to contain any type of image format, at this
point in time only `PNG` or `JPG` will be recognized and supported within
ForeFlight's use of FBTiles spec.


```sql
CREATE TABLE [datatypes] (id INTEGER PRIMARY KEY,
                          datatype TEXT UNIQUE);

CREATE INDEX datatypes_idx ON datatypes(datatype);
```

Columns:

 * `id`: unique integer
 * `datatype`: unique text for image format (either `PNG`, or `JPG`)


###Tiles Table

The `tiles` table associates the BLOB data to the row, column, zoom levels
necessary for efficient retrieval from within an application.

```sql
CREATE TABLE tiles  (tilekey INTEGER PRIMARY KEY,
                     zoom_level INTEGER,
                     tile_row INTEGER,
                     tile_column INTEGER,
                     tile_data BLOB,
                     tile_datatypes_id INTEGER,
                     tile_collar_data BLOB,
                     tile_collar_datatypes_id INTEGER,
        FOREIGN KEY (tile_datatypes_id) REFERENCES datatypes(id),
        FOREIGN KEY (tile_collar_datatypes_id) REFERENCES datatypes(id));

CREATE INDEX tiles_idx ON tiles(zoom_level,
                                tile_row,
                                tile_column);

CREATE INDEX tiles_zoom_idx ON tiles(zoom_level);
```

Columns:

 * `tilekey`: unique integer
 * `zoom_level`: integer values from `0` (highest) - `17` (lowest) zoom
 * `tile_row`: row or Y-value for tile
 * `tile_column`: column or X-value for tile
 * `tile_data`: BLOB for image data (no format assumed)
 * `tile_datatypes_id`: refers to format of BLOB in separate table
 * `tile_collar_data`: BLOB for collared image data (no format assumed)
 * `tile_collar_datatypes_id`: refers to format of BLOB in separate table



Examples
--------

 * Requirements:
    + [Python 2.7+](http://python.org/download/)
 * Optional
    + [SQLite3](http://www.sqlite.org/download.html)

Included in this repository is an `examples` directory that currently contains
example code in Python that demonstrate how to create a basic FBTiles dataset.
The basic example, `examples/example1.py` refers to a `FBTiles` class found in
`examples/fbtiles.py`. This core class demonstrates how to create the initial
database schema, and also provides an example of the tasks associated with
adding a tile in the `FBTiles.add_tile()` method.

```python
    def add_tile(self, tile_filename, x, y, z, collared=False):
        [...]
```

If you are familiar with Python, or running things from the command line the
next steps will be familiar. These steps assume  you have access to a Unix
terminal, such as you would find on Mac OS X, or Linux environments although it
is certainly possible to execute these examples under other platforms such as
Windows. Python is a widely supported and the examples here are portable
assuming you have the minimum supported Python version.

### Running Python Example-1

Example 1 simply adds two versions of a tile at a single position to an FBTiles
dataset. The regular version is added and then the collared version.

To run the example, open a terminal to this repository directory (wherever you
have cloned it into).  Step into the examples directory with `cd examples`.
You'll then execute the example1.py script using the python interpretor `python
example1.py`, and if all goes well, you will see messages stating that the
dataset `example1.fbtiles` was created.

```bash
$ cd examples
$ python example1.py
connecting to: example1.fbtiles
creating schema
closing database: example1.fbtiles
Created example1.fbtiles
```

Afterwards, if you have installed the optional SQLite3 programs, and are
familiar with SQL, you can inspect the contents of the dataset.

```bash
$ sqlite3 example1.fbtiles
SQLite version 3.7.12 2012-04-03 19:43:07
Enter ".help" for instructions
Enter SQL statements terminated with a ";"
sqlite> select * from tiles;
536870913|0|2|1|����|1|����|1
```

### Running Python Tests

Within the `examples` directory is a `tests` directory that contains a test
script `fbtiles_test.py`. Following on the steps we already discussed for
running the example, you can simply type the following from a terminal if you
are within the `examples` directory. You should see something similar to the
output shown below with paths that are relative to your project.

```bash
$ python tests/fbtiles_test.py
connecting to: /Users/joe/fbtiles/examples/tests/test.db
creating schema
closing database: /Users/joe/fbtiles/examples/tests/test.db
.connecting to: /Users/joe/fbtiles/examples/tests/test.db
creating schema
closing database: /Users/joe/fbtiles/examples/tests/test.db
.connecting to: /Users/joe/fbtiles/examples/tests/test.db
creating schema
closing database: /Users/joe/fbtiles/examples/tests/test.db
.connecting to: /Users/joe/fbtiles/examples/tests/test.db
creating schema
closing database: /Users/joe/fbtiles/examples/tests/test.db
.connecting to: /Users/joe/fbtiles/examples/tests/test.db
creating schema
closing database: /Users/joe/fbtiles/examples/tests/test.db
.
----------------------------------------------------------------------
Ran 5 tests in 0.083s

OK
```

If you open `examples/tests/fbtiles_test.py` you'll find additional examples,
although from a testing point of view, of how to use the included FBTiles
object and what might be the expected behavior in odd situations (e.g. What's
the correct behavior if I add the same tile twice?).


Versions
--------

 * 1.0
    + Introduces FBTiles schema with collared data concepts.


References
----------

 * [ForeFlight App](https://itunes.apple.com/us/app/foreflight-mobile/id333252638?mt=8)
 * [ForeFlight (company website)](http://www.foreflight.com)
 * [MBTiles](http://www.mbtiles.org)
 * [MapBox](http://www.mapbox.com)
 * [Creative Commons Attribution 3.0 United States
License](http://creativecommons.org/licenses/by/3.0/us/).

License
-------

The text of this specification is licensed under a
[Creative Commons Attribution 3.0 United States
License](http://creativecommons.org/licenses/by/3.0/us/).
However, the use of this spec in products and code is entirely free: there are
no royalties, restrictions, or requirements.

Authors
-------

 * Adam Houghton
 * Kevin Turner (ksturner)
 * Matt Croydon (mcroydon)
