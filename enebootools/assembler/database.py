# encoding: UTF-8
import os
import os.path
import sqlite3

from lxml import etree

from enebootools import CONF_DIR
from enebootools.assembler.config import cfg
from enebootools.lib.utils import one, find_files, get_max_mtime
import enebootools.lib.peewee as peewee
from enebootools.mergetool import projectbuilder
from enebootools.mergetool import MergeToolInterface    


from databasemodels import KnownObjects

from mypeewee import transactional
from kobjects import ObjectIndex

class Database(object):
    def __init__(self, filename):
        self.db = None
        self.dbtree = None
        self.dbfile = filename
    
    def ready(self):
        return bool(self.db)
        
    def setup(self):
        self.db = peewee.SqliteDatabase(self.dbfile)
        self.db.execute("PRAGMA synchronous = 1;")
        KnownObjects.setup(database.db)

    def init(self):
        if not database.ready():
            self.setup()
        
    def get_database(self):
        return self.db

database = Database(os.path.join(CONF_DIR, "assembler-database.sqlite"))


def init_database():
    global database
    database.init()
    return database



@transactional(database)
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
            obj.extradata = ""
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
            obj.extradata = ""
            obj.save()
        
        feature_root[path] = features


def list_objects(iface):
    db = init_database()
    oi = ObjectIndex(iface)
    oi.analyze_objects()
    iface.msg(u"\nMódulos cargados:")
    for obj in oi.modules():
        iface.msg(u" - %s" % obj.formal_name())

    iface.msg(u"\nFuncionalidades cargadas:")
    for obj in oi.features():
        iface.msg(u" - %s" % obj.formal_name())

def do_howto_build(iface,target, feat):
    db = init_database()
    oi = ObjectIndex(iface)
    oi.analyze_objects()
    build_instructions = oi.get_build_actions(target,feat)
    if build_instructions is None:
        iface.error("Error al buscar %s -> %s" % (feat,target))
        return False
    iface.info("Acciones para compilar funcionalidad %s %s:" % (feat, target))
    iface.msg(etree.tostring(build_instructions, pretty_print=True))
    buildpath = os.path.join(build_instructions.get("path"), "build")
    if not os.path.exists(buildpath):
        os.mkdir(buildpath)
    dstfile = os.path.join(buildpath, "%s.build.xml" % target)
    build_instructions.getroottree().write(dstfile, pretty_print=True)
    
    

def is_target_built(iface, target, feat):
    # TODO: Revisar si $target.build.xml existe
    # TODO: Si existe, preguntar a mergetool si cree que está construido.
    return False # Asumir que nunca una dependencia está cumplida

def do_build(iface,target, feat, rebuild=True):
    db = init_database()
    oi = ObjectIndex(iface)
    oi.analyze_objects()
    build_instructions = oi.get_build_actions(target,feat)
    if build_instructions is None: return False
    buildpath = os.path.join(build_instructions.get("path"), "build")
    if not os.path.exists(buildpath):
        os.mkdir(buildpath)
    dstfile = os.path.join(buildpath, "%s.build.xml" % target)
    build_instructions.getroottree().write(dstfile, pretty_print=True)
    depends = build_instructions.get("depends", "").split(" ")
    if depends:
        for dep in depends: 
            dep = dep.strip()
            if dep == "": continue
            if not is_target_built(iface, dep, feat):
                # Si tiene una dependencia, y no está cumplida, recompilarla:
                do_build(iface, dep, feat, rebuild = False)
                
    mtool_iface = MergeToolInterface()
    mtool_iface.verbosity = iface.verbosity
    projectbuilder.build_xml(mtool_iface,build_instructions,rebuild)
    
    


