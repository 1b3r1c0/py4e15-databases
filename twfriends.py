import urllib.request, urllib.parse, urllib.error
import twurl
import json
import sqlite3
import ssl

# This will return a JSON formatted list of 'acct's friends
# It requires twurl.augment()
TWITTER_URL = 'https://api.twitter.com/1.1/friends/list.json'

# Create the DB file if it doesn;t exist, and either way connect to it
conn = sqlite3.connect('friends.sqlite')
# cursor() is used to execute commands on the DB
# This should be closed analogous to a file handle (see last line of script)
cur = conn.cursor()

# execute a single command on the DB
cur.execute('''CREATE TABLE IF NOT EXISTS People
            (id INTEGER PRIMARY KEY, name TEXT UNIQUE, retrieved INTEGER)''')
# This has a contraint stating that the combinations of the IDs must be unique
cur.execute('''CREATE TABLE IF NOT EXISTS Follows
            (from_id INTEGER, to_id INTEGER, UNIQUE(from_id, to_id))''')

# Ignore SSL certificate errors
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

while True:
    acct = input('Enter a Twitter account, or quit: ')
    if (acct == 'quit'): break
    if (len(acct) < 1):
        # Perform a DB lookup and store the resulting rows in a magical place (see fecthone() below)
        cur.execute('SELECT id, name FROM People WHERE retrieved=0 LIMIT 1')
        try:
            # retrieves a single row from the magical place 
            (id, acct) = cur.fetchone()
        except:
            print('No unretrieved Twitter accounts found')
            continue
    else:
        # Perform a DB lookup and store the resulting rows in a magical place (see fecthone below)
        # The question mark and tuple work together to prevent SQLi
        # Note that python doesn't throw an exception when a DB query doesn't return something 
        # However, python *will* throw an exception when you try to 'fetch' something from the
        #  magical place but there weren't any results to put into the magical place
        cur.execute('SELECT id FROM People WHERE name = ? LIMIT 1',
                    (acct, ))
        try:
            # When the name already exists, retrieve it's ID
            # If the specified name doesn't already exist then an exception will be thrown
            # that's why we must use try/except instead of if/then
            id = cur.fetchone()[0]
        except:
            # The name must not already exist
            # SQL automagically assigns the primary key, aka "the row ID". I guess SQL does this 
            #  because the table was created like this?: (id INTEGER PRIMARY KEY, ...)
            # Remember that values in the 'name' column must be unique.
            # 'OR IGNORE' prevents inserting a duplicate value into the name column 
            # Note that the DB insert isn't written to disk until the commit() below
            cur.execute('''INSERT OR IGNORE INTO People
                        (name, retrieved) VALUES (?, 0)''', (acct, ))
            # This writes the inserted values to disk
            conn.commit()
            # Returns the number of rows affected by the last commit
            if cur.rowcount != 1:
                print('Error inserting account:', acct)
                continue
            # returns the ID of the row that was just commited
            id = cur.lastrowid

    
    # This will return a JSON formatted list of 'acct's friends
    # It will be used in twurl.augment()
    # TWITTER_URL = 'https://api.twitter.com/1.1/friends/list.json'
    url = twurl.augment(TWITTER_URL, {'screen_name': acct, 'count': '100'})
    print('Retrieving account', acct)
    try:
        # Connect to twitter's API
        # store the HTTP response, both the body & headers, in 'connection' (not the best var name)
        connection = urllib.request.urlopen(url, context=ctx)
    # Exception as err - captures the exception, an HTTP error in this case, 
    #  and puts it into the varible 'err'  
    except Exception as err:
        print('Failed to Retrieve', err)
        # this would break the main loop essentialy ending the script
        break

    # read() the body of the HTTP response
    # decode() from UTF-8 into unicode
    data = connection.read().decode()

    # twitter provides an experimental HTTP header that advises the user of the remaining API calls they have
    # not 100% sure how dict() works here ...
    # getheaders() from the response stored in 'connection'
    headers = dict(connection.getheaders())
    print('Remaining', headers['x-rate-limit-remaining'])

    try:
        # Verify JSON syntax in the HTTP body (now unicode)
        # pronounce as load-ess, not 'loads'
        # Remember, loads() returns a dictionary of nested lists and/or dictionaries
        js = json.loads(data)
    except:
        print('Unable to parse json')
        print(data)
        # this would break the main loop essentialy ending the script
        break

    # Debugging
    # print(json.dumps(js, indent=4))

    # Skip to next iteration if the JSON doesn't at least have a key named 'users'
    if 'users' not in js:
        print('Incorrect JSON received')
        print(json.dumps(js, indent=4))
        # this would skip to the next iteration of the main loop
        continue

    cur.execute('UPDATE People SET retrieved=1 WHERE name = ?', (acct, ))

    countnew = 0
    countold = 0

# This is hard to follow without an example of the JSON returned from twitter's API
# Here's my best guess what the resulting py dictionary looks like:
#   js = {
#       'users' : [
#           {
#               'user1' : {
#                   'screen_name' : 'ScreenName1',
#                   . . .
#                }
#           },
#           {
#               'user2' : {
#                   'screen_name' : 'ScreenName2',
#                   . . .
#                }
#           },
#           . . .
#        ],
#       . . .
#   } 
 
    for u in js['users']:
        friend = u['screen_name']
        print(friend)
        cur.execute('SELECT id FROM People WHERE name = ? LIMIT 1',
                    (friend, ))
        try:
            friend_id = cur.fetchone()[0]
            countold = countold + 1
        except:
            
            # Add the friend to the People table
            # Initalize 'retrieved' as zero
            cur.execute('''INSERT OR IGNORE INTO People (name, retrieved)
                        VALUES (?, 0)''', (friend, ))
            
            # write DB changes to disk
            conn.commit()
            
            # Verify something was done during last DB commit
            if cur.rowcount != 1:
                print('Error inserting account:', friend)
                continue
            
            # Get SQL's automagically assigned ID for the friend that was just added to the People table
            # AKA primary key, row ID, friend ID
            friend_id = cur.lastrowid

            countnew = countnew + 1

        # Add an entry to the Many-to-Many table
        # 'id' is for the user that was entered at the start of the main loop
        cur.execute('''INSERT OR IGNORE INTO Follows (from_id, to_id)
                    VALUES (?, ?)''', (id, friend_id))
    
    print('New accounts=', countnew, ' revisited=', countold)
    print('Remaining', headers['x-rate-limit-remaining'])
    
    # write DB changes to disk
    conn.commit()

# Close the DB "cursor", analogous to closing a file handle
cur.close()

