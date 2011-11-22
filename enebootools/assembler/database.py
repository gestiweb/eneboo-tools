# encoding: UTF-8
from enebootools.assembler.config import cfg
import os.path, fnmatch, os
import sqlite3, json
from lxml import etree
from enebootools import CONF_DIR

import enebootools.lib.peewee as peewee

db = None
dbtree = None

dbfile = os.path.join(CONF_DIR, "assembler-database.sqlite")
db = peewee.SqliteDatabase(dbfile)
db.execute("PRAGMA synchronous = 1;")

class BaseModel(peewee.Model):
    
    just_created = False
    
    class Meta:
        database = db
    
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
    def setup(cls):
        if cls.validate_table(): return True
        cls.drop_table(True)
        cls.create_table()
        cls.just_created = True
        print "CacheSqlite:: Se ha recreado la tabla %s."  % cls._meta.db_table
        return False


class KnownObjects(BaseModel):
    objid = peewee.PrimaryKeyField()
    objtype = peewee.CharField()
    abspath = peewee.CharField()
    relpath = peewee.CharField()
    filename = peewee.CharField()
    timestamp = peewee.IntegerField()
    extradata = peewee.TextField()

KnownObjects.setup()

def find_files(basedir, glob_pattern = "*", abort_on_match = False):
    ignored_files = [
        "*~",
        ".*",
        "*.bak",
        "*.bakup",
        "*.tar.gz",
        "*.tar.bz2",
        "*.BASE.*",
        "*.LOCAL.*",
        "*.REMOTE.*",
        "*.*.rej",
        "*.*.orig",
    ]
    retfiles = []
    
    for root, dirs, files in os.walk(basedir):
        baseroot = os.path.relpath(root,basedir)
        for pattern in ignored_files:
            delfiles = fnmatch.filter(files, pattern)
            for f in delfiles: files.remove(f)
            deldirs = fnmatch.filter(dirs, pattern)
            for f in deldirs: dirs.remove(f)
        pass_files = [ os.path.join( baseroot, filename ) for filename in fnmatch.filter(files, glob_pattern) ]
        if pass_files and abort_on_match:
            dirs[:] = [] 
        retfiles += pass_files
    return retfiles

def get_max_mtime(path, filename):
    ignored_files = [
        "*~",
        ".*",
        "*.bak",
        "*.bakup",
        "*.tar.gz",
        "*.tar.bz2",
        "*.BASE.*",
        "*.LOCAL.*",
        "*.REMOTE.*",
        "*.*.rej",
        "*.*.orig",
    ]
    
    basedir = os.path.join(path, os.path.dirname(filename))
    max_mtime = 0
    for root, dirs, files in os.walk(basedir):
        for pattern in ignored_files:
            delfiles = fnmatch.filter(files, pattern)
            for f in delfiles: files.remove(f)
            deldirs = fnmatch.filter(dirs, pattern)
            for f in deldirs: dirs.remove(f)
        for filename in files:
            filepath = os.path.join(root,filename)
            file_stat = os.stat(filepath)
            if file_stat.st_mtime > max_mtime:
                max_mtime = file_stat.st_mtime
    return max_mtime

"""
    - índices:
        En la base de datos vamos a indexar los siguientes elementos:
        - módulos:
            Un listado de módulos, y dónde los hemos encontrado. Si un módulo se encuentra
            dos veces, se omite la segunda.
        - funcionalidades:
            Un listado de funcionalidades y dónde las hemos encontrado. Si una extensión
            aparece dos veces, la segunda vez se ignora.
        - fecha-hora última modificación:
            de los módulos y las funcionalidades, cual es la fecha-hora más reciente de los ficheros.
            Cuando este valor se actualiza, se lanzan disparadores de invalidación de cachés.
    - cachés:
        Vamos a hacer caché de los siguientes elementos:
        - builds parciales:
            qué variantes de los módulos se han compilado ya, dónde se han compilado 
            y qué versiones (fecha de modificación) se usaron para éstas.
                    
"""
            

def transactional(fn):
    def decorator(*args,**kwargs): 
        global db
        old_autocommit = db.autocommit 
        db.autocommit = False
        try:
            ret = fn(*args,**kwargs)
        except:
            db.rollback()
            raise
        db.commit()
        db.autocommit = old_autocommit
        return ret
    return decorator

def get_database():
    global db
    if db is not None: return db
    return db

@transactional
def update_database(iface):
    from datetime import datetime
    iface.info(u"Actualizando base de datos de módulos y funcionalidades . . . ")
    KnownObjects.delete().execute() # -- Borrar todos los objetos
    module_root = {}
    for path in cfg.module.modulefolders:
        if not os.path.exists(path):
            iface.debug(u"Se ignora directorio inexistente %s" % repr(path))
            continue
        modules = find_files(path,"*.mod", True)
        if not modules:
            iface.warn(u"Directorio no contiene módulos %s" % repr(path))
            continue
        iface.info(u"Se encontraron %d modulos en la carpeta %s" % (len(modules), repr(path)))
        for module in modules:
            iface.debug(u"Módulo %s" % module)
            mtime = get_max_mtime(path,module)
            dmtime = datetime.fromtimestamp(mtime)
            obj = KnownObjects()
            obj.objtype = "module"
            obj.abspath = path
            obj.relpath = os.path.dirname(module)
            obj.filename = os.path.basename(module)
            obj.timestamp = int(mtime)
            data = {}
            obj.extradata = json.dumps(data)
            obj.save()
            
            # print dmtime.strftime("%a %d %B %Y @ %H:%M:%S %z")
        module_root[path] = modules

    feature_root = {}
    for path in cfg.module.featurefolders:
        if not os.path.exists(path):
            iface.debug(u"Se ignora directorio inexistente %s" % repr(path))
            continue
        features = find_files(path,"*.feature.ini", True)
        if not features:
            iface.warn("Directorio no contiene funcionalidades %s" % repr(path))
            continue
        iface.info(u"Se encontraron %d funcionalidades en la carpeta %s" % (len(features), repr(path)))
        for feature in features:
            iface.debug(u"Funcionalidad %s" % feature)
            mtime = get_max_mtime(path,feature)
            dmtime = datetime.fromtimestamp(mtime)
            # print dmtime.strftime("%a %d %B %Y @ %H:%M:%S %z")
            obj = KnownObjects()
            obj.objtype = "feature"
            obj.abspath = path
            obj.relpath = os.path.dirname(feature)
            obj.filename = os.path.basename(feature)
            obj.timestamp = int(mtime)
            data = {}
            obj.extradata = json.dumps(data)
            obj.save()
        
        feature_root[path] = features
        




