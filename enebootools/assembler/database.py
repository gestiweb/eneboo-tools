# encoding: UTF-8
from enebootools.assembler.config import cfg
import os.path, fnmatch, os
from lxml import etree
from enebootools import CONF_DIR

db = None
dbtree = None

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

def get_database():
    global db
    if db is not None: return db
    
    dbfile = os.path.join(CONF_DIR, "assembler-database.xml")
    if os.path.exists(dbfile):
        parser = etree.XMLParser(
                        ns_clean=False,
                        encoding="UTF-8",
                        recover=True,
                        remove_blank_text=True,
                        )
        dbtree = etree.parse(dbfile, parser)
        db = dbtree.getroot()
    else:
        db = etree.Element("assemberdb", version="1.0")
        dbtree = db.getroottree()
    return db

def update_database(iface):
    from datetime import datetime
    db = get_database()
    iface.info(u"Actualizando base de datos de módulos y funcionalidades . . . ")
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
            print dmtime.strftime("%a %d %B %Y @ %H:%M:%S %z")
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
            print dmtime.strftime("%a %d %B %Y @ %H:%M:%S %z")
        
        feature_root[path] = features
        




