#!/bin/python3

import sqlite3

conn = sqlite3.connect('orgdb.sqlite')
cur = conn.cursor()

cur.execute('DROP TABLE IF EXISTS Counts')

cur.execute('''
CREATE TABLE Counts (org TEXT, count INTEGER)''')

# fname = input('Enter file name: ')
# if (len(fname) < 1): fname = 'mbox.txt'

fname = 'mbox.txt'
fh = open(fname)
for line in fh:
    # example of a From line in mbox.txt
    # From stephen.marquard@uct.ac.za Sat Jan  5 09:14:16 2008
    
    # Ignore lines that don't start with "From:"
    if not line.startswith('From: '): continue
    
    # Split the "From:" line by spaces and grab the second item, email address,
    #  then split on '@' and grab the second item, the organization
    org = line.split()[1].split('@')[1]
    
    # debug
    # print("org:",org)
    # junk = input("CTL+c to quit, RTN to continue")

    cur.execute('SELECT count FROM Counts WHERE org = ? ', (org,))
    row = cur.fetchone()
    
    if row is None:
        # The org address wasn;t in the table
        # add the org address with count set to 1
        cur.execute('''INSERT INTO Counts (org, count)
                VALUES (?, 1)''', (org,))
    else:
        cur.execute('UPDATE Counts SET count = count + 1 WHERE org = ?',
                    (org,))
    
# write all db changes to disk at once after the loop finsihes going through the ~6MB of text
conn.commit()

# https://www.sqlite.org/lang_select.html
sqlstr = 'SELECT org, count FROM Counts ORDER BY count DESC LIMIT 10'

for row in cur.execute(sqlstr):
    print(str(row[0]), row[1])

cur.close()
