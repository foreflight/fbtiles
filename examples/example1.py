#!/usr/bin/env python
"""
Example 1 - Create a basic FBTiles file with a single tile location that has
both a regular tile and an alternate tile for same location stored as the
"collared" version.

NOTE: This is a high-level example of adding a tile. You will need to consult
the fbtiles.py file (found alongside this example file) for the steps required
to add a tile.

"""
import os

from fbtiles import FBTiles


def main():
    '''
    Creates a dataset with a single tile entry but with both a regular and
    collared version of that tile.
    '''
    fbt_filename = 'example1.fbtiles'

    # Check that we don't already have an exmaple fbtiles on disk from a
    # previous run. If so, delete it.
    if os.path.exists(fbt_filename):
        print 'WARNING: deleting existing', fbt_filename
        os.unlink(fbt_filename)

    # Create an FBTiles object, which will also create the initial empty
    # database with the correct schema because we have connect=True.
    fbt = FBTiles(fbt_filename, connect=True)

    # Now we are going to add our tile image for zoom level 0, at row 1,
    # column 2. The terms 'row' and 'y' are synonymous, as are 'column' and
    # 'x'.
    fbt.add_tile('example1.jpg', x=2, y=1, z=0, collared=False)
    fbt.add_tile('example1b.jpg', x=2, y=1, z=0, collared=True) # collared
    fbt.close()

    # Now we have a newly created .fbtiles file called 'example1.fbtiles' on
    # disk. It should have 3 tables, with the following data (where the raw
    # BLOB bytes are replaced with <BLOB?> for readability).
    #
    #   datatypes:
    #       1, JPG
    #       2, PNG
    #   tiles:
    #       536870913, 0, 2, 1, <BLOB1>, 1, <BLOB1b>, 1
    #   bounds:
    #       0, 0, 2, 1, 2, 1
    #       0, 1, 2, 1, 2, 1
    #
    print 'Created', fbt_filename


if __name__ == '__main__':
    main()
