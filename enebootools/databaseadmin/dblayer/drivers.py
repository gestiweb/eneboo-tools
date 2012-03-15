import re


def test_drivers():
    mysql, pgsql, sqlite = None, None, None
    try: import MySQLdb as mysql
    except ImportError: print "WARN: python-mysqldb was not found. MySQL support disabled."

    try: import psycopg2 as pgsql
    except ImportError: print "WARN: python-psycopg was not found. PostgreSQL support disabled."

    try: import sqlite3 as sqlite
    except ImportError: print "WARN: python-sqlite or sqlite3 was not found. SQLite support disabled."
    return mysql, pgsql, sqlite

class DBUrl(object):
    dialect = None
    driver = None
    username = None
    password = None
    hostname = None
    port = None
    dbname = None
    
    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)
    
    def __str__(self):
        return "\n".join(["DBUrl::"] + ["    %s = %s" % (k,repr(v)) for k,v in self.__dict__.items() ]) 


class DBAutoQuery(object):
    def use_connection(self, conn): raise NotImplementedError

    def database(self, dbname): return DBAutoQuery_Database(self, dbname)
    def databases(self, **kwargs): return DBAutoQuery_Database.list(self, **kwargs)
    
    def table(self, tablename): return DBAutoQuery_Table(self, tablename)
    def tables(self, **kwargs): return DBAutoQuery_Table.list(self, **kwargs)

    def tablefield(self, fieldname): return DBAutoQuery_TableField(self, fieldname)
    def tablefields(self, tablename): return DBAutoQuery_TableField(self, fieldname)

class DBAutoQuery_Database(object):
    def __init__(self, parent): self.parent = parent
    
    @classmethod 
    def list(self, **kwargs): raise NotImplementedError
    
    def create(self, **kwargs): raise NotImplementedError
    def drop(self, **kwargs): raise NotImplementedError
    def exists(self, **kwargs): raise NotImplementedError
    

class DBAutoQuery_Table(object):
    def __init__(self, parent): self.parent = parent

    @classmethod 
    def list(self, **kwargs): raise NotImplementedError
    
    def create(self, fields, **kwargs): raise NotImplementedError
    def drop(self, **kwargs): raise NotImplementedError
    def exist(self, **kwargs): raise NotImplementedError
    def rename(self,newname, **kwargs): raise NotImplementedError

    def field(self, fieldname): return DBAutoQuery_Field(self.parent, fieldname, self)
    def fields(self, **kwargs): return DBAutoQuery_Field.list(self.parent, self.name, **kwargs)
    
    

    
        

def parse_url(url):
    # protocol://destination/path
    main_url = re.match("^(?P<protocol>[^:]+)://(?P<destination>[^/]+)/(?P<path>.*)$", url)
    if not main_url: raise ValueError("Invalid URL: %s" % repr(url))
    murl_dict = main_url.groupdict()

    #dialect+driver://username:password@host:port/database
    
    protocol = murl_dict["protocol"].split("+")
    
    dialect, driver = None, None
    if len(protocol) == 1: dialect, = protocol
    elif len(protocol) == 2: dialect, driver = protocol
    else: raise ValueError("Invalid URL, too many parts in protocol: %s" % repr(protocol))
    
    destination = murl_dict["destination"].split("@")
    
    userpair, hostpair = None, None
    if len(destination) == 1: userpair, = destination
    elif len(destination) == 2: userpair, hostpair = destination
    else: raise ValueError("Invalid URL, too many parts in destination: %s" % repr(destination))
    
    username, password = None, None
    if userpair:
        userpair = userpair.split(":")
        if len(userpair) == 1: username, = userpair
        elif len(userpair) == 2: username, password = userpair
        else: raise ValueError("Invalid URL, too many parts in user: %s" % repr(userpair))
    
    hostname, port = None, None
    if hostpair:
        hostpair = hostpair.split(":")
        if len(hostpair) == 1: hostname, = hostpair
        elif len(hostpair) == 2: hostname, port = hostpair
        else: raise ValueError("Invalid URL, too many parts in host: %s" % repr(hostpair))
    
    try: port = int(port) if port else None
    except ValueError: raise ValueError("Invalid URL, port must be a number: %s" % repr(port))
    dbname = murl_dict["path"]
    
    return DBUrl(
        dialect = dialect, driver = driver, 
        username = username, password = password,
        hostname = hostname, port = port,
        dbname = dbname,
        )
    
    
    

if __name__ == "__main__": 
    import sys
    test_drivers()
    if len(sys.argv) > 1:
        url = parse_url(sys.argv[1])
        print url
        
    

