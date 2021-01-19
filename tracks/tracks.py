#!/bin/python3

import xml.etree.ElementTree as ET
import sqlite3

# Help on XML & ElementTree
# https://www.geeksforgeeks.org/xml-parsing-python/

conn = sqlite3.connect('trackdb.sqlite')
cur = conn.cursor()

# Make some fresh tables using executescript()
cur.executescript('''
DROP TABLE IF EXISTS Artist;
DROP TABLE IF EXISTS Genre;
DROP TABLE IF EXISTS Album;
DROP TABLE IF EXISTS Track;

CREATE TABLE Artist (
    id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    name    TEXT UNIQUE
);

CREATE TABLE Genre (
    id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    name    TEXT UNIQUE
);

CREATE TABLE Album (
    id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    artist_id  INTEGER,
    title   TEXT UNIQUE
);

CREATE TABLE Track (
    id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    title TEXT  UNIQUE,
    album_id  INTEGER,
    genre_id  INTEGER,
    len INTEGER, rating INTEGER, count INTEGER
);
''')

# fname = input('Enter file name: ')
# if ( len(fname) < 1 ) : fname = 'Library.xml'
fname = 'Library.xml'

#------------------------------------------
# lookup function
#
# Input: XML element as an ET object, a key tag's text (string)
# Output: the iTune's track value corresponding to the key tag's text (string)
#
# This finds the specific 'key' tag with matching text and then returns
#  its corresponding value from the following tag. Note that iTune's XML for
#  track data is odd. All of the track's attribute/values are broken up into
#  2 separate XML elements:
#
#    <key>Track ID</key><integer>369</integer>
#    <key>Name</key><string>Another One Bites The Dust</string>
#    <key>Artist</key><string>Queen</string>
#
# Typically we'd expect something like this instead
#
#    <Track ID>369</Track ID>
#    <Name>Another One Bites The Dust</Name>
#    <Artist>Queen</Artist>
#
# To find a value for a specific key
#   1. Find the 'key' tag containing the text we're interesed in, e.g. <key>Name</key>
#   2. Retrieve the text from the **following** tag, 
#        e.g. <string>Another One Bites The Dust</string>
#
def lookup(d, key):
    found = False

    # iterate over each XML "element" of 'dict/dict/dict'
    for child in d:

        # When 'found' is true, 'child.text' will be the text from the tag 
        #  **following** the "key" tag we're interested in
        if found : return child.text

        # debug
        # print("child:",child)
        # print("child.tag:",child.tag)
        # print("child.text:",child.text)
        # junk = input("CTL+C to quit, RTN to continue")
        # continue
    
        # child.tag is the name of the element; for iTune's track data, 
        #  we'll always be looking for the <key> tag
        # child.text is all the text inside that element, e.g. Track ID, Name, Artist
        if child.tag == 'key' and child.text == key :
            # The next iteration will be the XML element corresponding to this 'key' tag 
            found = True

    # Couldn't find a 'key' tag matching "key"
    return None
#------------------------------------------

# Use parse() to create an ElementTree object from fname
stuff = ET.parse(fname)

# Example XML from Library.xml
# <dict>
# 	. . .
# 	<key>Tracks</key>
# 	. . .
# 	<dict>
# 		<key>369</key>
#		<dict>
#			<key>Track ID</key><integer>369</integer>
#			<key>Name</key><string>Another One Bites The Dust</string>
#			<key>Artist</key><string>Queen</string>
#			<key>Album</key><string>Greatest Hits</string>
#			<key>Genre</key><string>Rock</string>
#			<key>Total Time</key><integer>217103</integer>
#			<key>Play Count</key><integer>55</integer>
#			<key>Rating</key><integer>100</integer>
#		</dict>
# 		<key>371</key>
# 		<dict>
# 			<key>Track ID</key><integer>371</integer>
# 	                . . .
# 	</dict>
# 

# put every track's XML elements into 'all'
all = stuff.findall('dict/dict/dict')

# not sure why this is here
# print('Dict count:', len(all))

# Loop through all track data - XML elements
for entry in all:
    
    # A track's first key-tag is always 'Track ID'
    # skip XML elements until we find the begining of a track
    if ( lookup(entry, 'Track ID') is None ) : continue
    
    # Use our 'lookup' function to get the values of these track attributes
    name = lookup(entry, 'Name') # i.e. track name
    artist = lookup(entry, 'Artist')
    album = lookup(entry, 'Album')
    genre = lookup(entry, 'Genre')
    count = lookup(entry, 'Play Count')
    rating = lookup(entry, 'Rating')
    length = lookup(entry, 'Total Time')

    # Skip tracks lacking good attributes
    if name is None or artist is None or album is None or genre is None : 
        continue
    
    # not sure why this is here
    # print(name, artist, album, count, rating, length)
    
    # This table's primary key, "id", is auto incremented
    cur.execute('''INSERT OR IGNORE INTO Artist (name) 
        VALUES ( ? )''', ( artist, ) )
    # retreive the auto-created "id"
    cur.execute('SELECT id FROM Artist WHERE name = ? ', (artist, ))
    artist_id = cur.fetchone()[0]
    
    # This table's primary key, "id", is auto incremented
    cur.execute('''INSERT OR IGNORE INTO Album (title, artist_id) 
        VALUES ( ?, ? )''', ( album, artist_id ) )
    # retreive the auto-created "id"
    cur.execute('SELECT id FROM Album WHERE title = ? ', (album, ))
    album_id = cur.fetchone()[0]
    
    # This table's primary key, "id", is auto incremented
    cur.execute('''INSERT OR IGNORE INTO Genre (name) 
        VALUES ( ? )''', ( genre, ) )
    # retreive the auto-created "id"
    cur.execute('SELECT id FROM Genre WHERE name = ? ', (genre, ))
    genre_id = cur.fetchone()[0]
    
    cur.execute('''INSERT OR REPLACE INTO Track
        (title, album_id, genre_id, len, rating, count)
        VALUES ( ?, ?, ?, ?, ?, ? )''', 
        ( name, album_id, genre_id, length, rating, count ) )
    
    conn.commit()

cur.execute('''
SELECT Track.title, Artist.name, Album.title, Genre.name 
    FROM Track JOIN Genre JOIN Album JOIN Artist 
    ON Track.genre_id = Genre.id and Track.album_id = Album.id 
        AND Album.artist_id = Artist.id
    ORDER BY Artist.name LIMIT 3
''')

# debug print( dir( cur ) )

print("Track, Artist, Album, Genre")
print("-----------------------------------")
for row in cur.fetchall():
    print(row)
