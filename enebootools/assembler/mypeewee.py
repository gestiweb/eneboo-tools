# encoding: UTF8
import enebootools.lib.peewee as peewee

def transactional(db):
    def transactional1(fn):
        def decorator(*args,**kwargs): 
            db.init()
            old_autocommit = db.db.autocommit 
            db.db.autocommit = False
            try:
                ret = fn(*args,**kwargs)
            except:
                db.db.rollback()
                raise
            db.db.commit()
            db.db.autocommit = old_autocommit
            return ret
        return decorator
    return transactional1
    
class BaseModel(peewee.Model):
    just_created = False
    class Meta:
        database = None
    
    @classmethod
    def validate_table(cls):
        tablename = cls._meta.db_table
        query = cls._meta.database.execute("PRAGMA table_info( %s )" % tablename)
        if query.description is None: return False
        field_names = [ x[0] for x in query.description ]
        not_found_fields = cls._meta.fields.keys()
        update_fields = {}
        for rowtuple in query:
            row = dict(zip(field_names, rowtuple))
            if row['name'] not in cls._meta.fields: continue
            not_found_fields.remove(row['name'])
            field = cls._meta.fields[row['name']]
            tpl1 = u"%(name)s %(type)s" % row
            if row['notnull'] == 1: tpl1 += ' NOT NULL'
            if row['pk'] == 1: tpl1 += ' PRIMARY KEY'
            tpl2 = unicode(field.to_sql())
            if tpl1 != tpl2:
                update_fields[row['name']] = (tpl1 , tpl2)
        
        if not_found_fields:
            return False
        if update_fields:
            return False
        return True
            
    @classmethod
    def setup(cls,db):
        cls.set_database(db)
        if cls.validate_table(): return True
        cls.drop_table(True)
        cls.create_table()
        cls.just_created = True
        print "CacheSqlite:: Se ha recreado la tabla %s."  % cls._meta.db_table
        return False
    
    def format(self):
        field_list = self._meta.fields.values()
        field_list.sort(key=lambda x: x._order)
        fields = " ".join( [ "%s=%s" % (f.name,repr(getattr(self,f.name,None))) for f in field_list ] )
        return "<%s %s>" % (self.__class__.__name__, fields)
