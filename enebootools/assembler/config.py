# encoding: UTF8
from enebootools.autoconfig.autoconfig import AutoConfigTemplate, ConfigReader
from enebootools import CONF_DIR
import sys, os.path
cfg = None
config_filelist = ['assembler-config.ini']


class ConfModule(AutoConfigTemplate):
    """
    modulefolders=stringList:
        - ~/git/eneboo-modules
    featurefolders=stringList:
        - ~/git/eneboo-features
    buildcache=string:~/.eneboo-tools/buildcache
    """
    
    def normalize_path(self, path):
        pathlist = path.split("/")
        return os.path.join( *[
            os.path.expanduser(p)
            for p in pathlist
        ] )
    
    def init(self):
        self.modulefolders = [ self.normalize_path(folder) 
                            for folder in self.modulefolders]
    
        self.featurefolders = [ self.normalize_path(folder) 
                            for folder in self.featurefolders]
    
        self.buildcache = self.normalize_path(self.buildcache) 
    
            
    
    
    



def reloadConfig(saveTemplate = False):
    import config as c # --> autoimportación.
    files = [ os.path.join(CONF_DIR, x) for x in c.config_filelist ]
    last_file = files[-1]
    if saveTemplate == "*template*":
        saveTemplate = last_file + ".template"
        files = []
    elif saveTemplate == "*update*":
        saveTemplate = last_file
    elif not os.path.exists(last_file):
        files = []
        saveTemplate = last_file
    
    c.cfg = ConfigReader(files=files, saveConfig = saveTemplate)
    c.cfg.module = ConfModule(c.cfg,section = "module")
    c.cfg.module.init()
    
    if saveTemplate:
        f1w = open(saveTemplate, 'wb')
        c.cfg.configini.write(f1w)
        f1w.close()
    return c.cfg


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == 'savetemplate':
            reloadConfig(saveTemplate = '*template*')
        elif sys.argv[1] == 'update':
            reloadConfig(saveTemplate = '*update*')
    else:
        reloadConfig()


if __name__ == "__main__": main()
else: reloadConfig()
