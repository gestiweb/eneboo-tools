# coding: UTF8
import ConfigParser
import parsers


import traceback
 
import os.path
import sys

def apppath(): return os.path.abspath(os.path.dirname(sys.argv[0]))
def filepath(): return os.path.abspath(os.path.join(os.path.dirname(__file__),".."))

def appdir(x):
    if os.path.isabs(x): return x
    else: return os.path.join(filepath(),x)


    
class ConfigReader:
    def __init__(self, parserslist = {}, files = None, saveConfig = False):
        parserslist_new = parsers.parsers()    
        parserslist_new.update(parserslist)
        if files is None: files = ['config.ini']
        self.saveConfig = saveConfig 
        self.parser_list = parserslist_new
        self.filename_list = [appdir(x) for x in files]
        self.configini = None
        self.errors = False
        self.fatalErrors = False
        self.do_reload()
        
    def do_reload(self):
        self.configini = ConfigParser.RawConfigParser()
        ok_list = self.configini.read(self.filename_list)
        if set(ok_list) != set(self.filename_list):
            print "WARN: Uno o mas ficheros no se pudieron leer:", ", ".join([str(filename) for filename in set(self.filename_list) - set(ok_list)])

            if len(ok_list) == 0: 
                print "FATAL: No se ha podido leer ningún fichero de configuracion!"
                sys.exit(1)
            
    def loadSection(self,section):
        options = []
        if not self.configini.has_section(section) and self.saveConfig:
            print "INFO: agregando la seccion %s" % repr(section)
            self.configini.add_section(section)
            
        if self.configini.has_section(section):            
            options = self.configini.options(section)
        else:                
            print "WARN: No se encontró la seccion %s" % repr(section)
            self.errors = True
    
        opvalues = {}
        for option in options:
            opvalues[option] = self.configini.get(section,option)
        return opvalues




class Parameter:
    def __init__(self, parent = None, name = None, default = None, parser = None, required = False):
        if name in parent._params: raise AttributeError, "Parameter %s already included" % name
        if hasattr(self,name): raise AttributeError, "Parameter %s already exists in class" % name
        parent._params[name] = self
        self.name = name
        self.default = default
        self.parser = parser
        self.parent = parent
        self.required = required
        self.defined = False
        
    
    def setDefault(self):
        self.setValue(self.default)
        
    def setValue(self,v):
        configreader = self.parent.configReader
        if configreader.saveConfig:
            section = self.parent._sectionname
            configini = configreader.configini 
            configini.set(section,self.name,v)
        
        x = self.parser(v)
        setattr(self.parent,self.name,x)
        self.defined = True
    
    def getValue(self):
        return getattr(self.parent,self.name,None)

    def parseValue(self):
        #print self.name, self.defined, self.required
        if self.defined == False:
            configreader = self.parent.configReader
            if not configreader.saveConfig and self.required: 
                raise ValueError, "Parameter '%s' requires a value" % self.name
            else:
                self.setDefault()
                if not configreader.saveConfig:
                    configreader.errors = True
                    print "WARN: Asumiendo valor %s para parametro %s (seccion %s)" % (repr(self.getValue()),repr(self.name), repr(self.parent._sectionname))
                else:
                    print "INFO: Escribiendo valor %s para parametro %s (seccion %s)" % (repr(self.getValue()),repr(self.name), repr(self.parent._sectionname))

        x = getattr(self.parent,self.name)
        px = self.parser(x)
        if x != px:
            raise ValueError, "Parameter '%s' value %s parses to a different value %s!" % (self.name,repr(x),repr(px))
        
    

class AutoConfigTemplate:
    def __init__(self,configreader = None, section = None):
        self._params = {}
        self._sectionname = None
        self.configReader = configreader
        self.debug = False
        self.autoConfig()
        if section:
            self.loadSection(section)
        
    def autoConfig(self,config = None):
        if config is None: config = self.__doc__
        configLines = [ cline.strip() for cline in config.split("\n") if len(cline.strip()) > 0]
        cfg2 = []
        for cline in configLines:
            if cline[0] == '-' and len(cfg2):
                cline=cline[1:].strip()
                cfg2[-1] = cfg2[-1] + "\n" + cline 
            else:
                cfg2.append(cline)
        #print cfg2
        
        for cline in cfg2:
            try:
                required = False
                name = None
                parser = "string"
                default = ""
                if cline[0]=="*": 
                    required = True
                    cline = cline[1:]
                name = cline.split("=")[0]
                cline = cline[len(name)+1:]
            
                parser = cline.split(":")[0]
                cline = cline[len(parser)+1:]
            
                default = cline
                if parser not in self.configReader.parser_list:
                    raise NameError, "Parser type %s unknown" % repr(parser)
                self.addParam( name = name, default = default, parser = self.configReader.parser_list[parser], required = required)
            except Exception:
                print traceback.format_exc()
            
            
                
        
    
    def addParam(self,**kwargs): 
        param = Parameter(self,**kwargs)
        
    
    def setParam(self,name,value):
        if name not in self._params:
            if self.debug:
                print "WARN: Opcion %s en seccion %s no reconocida" % (repr(name),repr(self._sectionname))
            return False
        try:
            self._params[name].setValue(value)
        except Exception:
            print "ERROR: Opcion %s en seccion %s ocurrio el siguiente error:" % (repr(name),repr(self._sectionname))
            print traceback.format_exc(0)
            return False
            
        
                
    def loadSection(self,section, autoParse = True):
        self._sectionname = section
        opvalues = self.configReader.loadSection(section)
        for option,value in opvalues.iteritems():
            self.setParam(option,value)
        if autoParse: 
            pv = self.parseValues()
            if not pv:
                self.configReader.fatalErrors = True
                raise ValueError, "FATAL: Unable to load section %s" % repr(section)
                
    
    def parseValues(self):
        returnValue = True
        for name, param in self._params.iteritems():
            try:
                param.parseValue()
            except Exception:
                print "ERROR: Opcion %s en seccion %s ocurrio el siguiente error:" % (repr(name),repr(self._sectionname))
                print traceback.format_exc(0)
                returnValue = False
        return returnValue 
    
    
