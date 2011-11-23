# encoding: UTF-8
import os

from lxml import etree

from enebootools.lib.utils import one, find_files, get_max_mtime, read_file_list

from featureconfig import loadFeatureConfig
from databasemodels import KnownObjects

class BaseObject(object):
    _by_name = {}
    _by_relpath = {}
    _by_formal_name = {}
    def __init__(self, iface, obj):
        self.iface = iface
        self.obj = obj
        self.fullpath = os.path.join(obj.abspath, obj.relpath)
        self.fullfilename = os.path.join(obj.abspath, obj.relpath, obj.filename)
        self.setup()
        self.__class__._by_name[ ( self.__class__.__name__ , unicode(self.name)) ] = self
        self.__class__._by_relpath[ ( self.__class__.__name__ , unicode(obj.relpath)) ] = self
        self.__class__._by_formal_name[ ( self.__class__.__name__ , self.formal_name()) ] = self
    
    def formal_name(self):
        return unicode(self.obj.relpath)
    
    @classmethod 
    def by_name(self, name):
        return self._by_name.get(( self.__name__ , unicode(name)), None)
        
    @classmethod 
    def by_formal_name(self, name):
        return self._by_formal_name.get(( self.__name__ , unicode(name)), None)
        
    @classmethod 
    def by_relpath(self, relpath):
        return self._by_relpath.get(( self.__name__ , unicode(relpath)), None)
        
    @classmethod 
    def items(self):
        return [ v for k,v in self._by_name.items() if k[0] == self.__name__ ]
        
    @classmethod 
    def find(self, name):
        return self.by_formal_name(name) or self.by_name(name) or self.by_relpath(name)
    
    def setup(self):
        pass
        
    @classmethod 
    def cls_finish_setup(self):
        for k,obj in self._by_name.items():
            cname, name = k
            if cname != self.__name__: continue
            obj.finish_setup()
        
    def _get_full_required_modules(self):
        req = []
        myreq = []
        for modname in self.required_modules:
            obj = ModuleObject.find(modname)
            if obj is None:
                self.iface.warn("Modulo con nombre %s no encontrado" % modname)
                continue
            req += [ modulename for modulename in obj._get_full_required_modules() if modulename not in req  ]
            myreq.append(obj.formal_name())
        req += [ modulename for modulename in myreq if modulename not in req ]
        return req
        
    def _get_full_required_features(self):
        req = []
        myreq = []
        for featname in self.required_features:
            obj = FeatureObject.find(featname)
            if obj is None:
                self.iface.warn("Funcionalidad con nombre %s no encontrado" % featname)
                continue
            req += [ featurename for featurename in obj._get_full_required_features() if featurename not in req  ]
            myreq.append(obj.formal_name())
        req += [ featurename for featurename in myreq if featurename not in req ]
        return req
        
    def finish_setup(self):
        self.all_required_modules = self._get_full_required_modules()
        self.all_required_fatures = self._get_full_required_features()
    
    
class ModuleObject(BaseObject):
    def setup(self):
        self.encoding = "ISO-8859-15"
        self.parser = etree.XMLParser(
                        ns_clean=False,
                        encoding=self.encoding,
                        recover=True, # .. recover funciona y parsea cuasi cualquier cosa.
                        remove_blank_text=True,
                        )
        self.tree = etree.parse(self.fullfilename, self.parser)
        self.root = self.tree.getroot()
        
        self.name = one(self.root.xpath("name/text()"))
        self.description = one(self.root.xpath("description/text()"))
        self.type = "mod"
        self.module_area = one(self.root.xpath("area/text()"))
        self.module_areaname = one(self.root.xpath("areaname/text()"))
        self.required_modules = self.root.xpath("dependencies/dependency/text()")
        self.required_features = []
        self.iface.debug2(u"Se ha parseado el módulo %s" % self.name)

class FeatureObject(BaseObject):
    def setup(self):
        cfg = loadFeatureConfig(self.fullfilename)
        self.cfg = cfg
        self.name = cfg.feature.name
        self.code = cfg.feature.code
        self.description = cfg.feature.description
        self.type = cfg.feature.type
        
        self.required_modules = read_file_list(self.fullpath, "conf/required_modules", errlog = self.iface.warn)
        self.required_features = read_file_list(self.fullpath, "conf/required_features", errlog = self.iface.warn)

        self.patch_series = read_file_list(self.fullpath, "conf/patch_series", errlog = self.iface.warn)
        
        self.iface.debug2(u"Se ha parseado la funcionalidad %s" % self.name)

class ObjectIndex(object):
    def __init__(self, iface):
        self.iface = iface
        
    def analyze_objects(self):
        for kobj in KnownObjects.select():
            if kobj.objtype == "module": self.load_module(kobj)
            elif kobj.objtype == "feature": self.load_feature(kobj)
            else: 
                self.iface.warn("Unknown object type %s" % kobj.objtype)
                self.iface.warn(kobj.format())
        ModuleObject.cls_finish_setup()
        FeatureObject.cls_finish_setup()
                
    def load_module(self, obj):
        mod = ModuleObject(self.iface, obj)

    def load_feature(self, obj):
        ftr = FeatureObject(self.iface, obj)

    def modules(self): 
        return ModuleObject.items()
        
    def features(self): 
        return FeatureObject.items()
        
