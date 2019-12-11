import zlib, os, sys
from lxml import etree


def extpath(name):
    folder_ext = {
        '.ar': 'reports',
        '.csv': 'docs',
        '.doc': 'docs',
        '.jasper': 'ireports',
        '.jrxml': 'ireports',
        '.kut': 'reports',
        '.mtd': 'tables',
        '.odt': 'docs',
        '.pgsql': 'pgsql',
        '.qry': 'queries',
        '.qs': 'scripts',
        '.py': 'scripts',
        '.qso': 'binscripts',
        '.sql': 'pgsql',
        '.ts': 'translations',
        '.txt': 'docs',
        '.ui': 'forms',
        '.xml': '.'}
    if name in folder_ext: return folder_ext[name]
    return "other"


def areapath(name):
    folder_area = {
        'C': 'contabilidad',
        'CRM': 'crm',
        'D': 'direccion',
        'F': 'facturacion',
        'L': 'colaboracion',
        'R': 'rhumanos',
        'sys': 'sistema'}
    if name in folder_area: return folder_area[name]
    return "area_%s" % name.lower()

def modulepath(name):
    folder_module = {
        'fl_a3_nomi': 'nominas',
        'flar2kut': 'ar2kut',
        'flcolagedo': 'gesdoc',
        'flcolaproc': 'procesos',
        'flcolaproy': 'proyectos',
        'flcontacce': 'controlacceso',
        'flcontinfo': 'informes',
        'flcontmode': 'modelos',
        'flcontppal': 'principal',
        'flcrm_info': 'informes',
        'flcrm_mark': 'marketing',
        'flcrm_ppal': 'principal',
        'fldatosppal': 'datos',
        'fldireinne': 'analisis',
        'flfactalma': 'almacen',
        'flfactinfo': 'informes',
        'flfactppal': 'principal',
        'flfactteso': 'tesoreria',
        'flfacturac': 'facturacion',
        'flfacttpv': 'tpv',
        'flgraficos': 'graficos',
        'flrrhhppal': 'principal',
        'sys': 'administracion'}
    if name in folder_module: return folder_module[name]
    if name.endswith("ppal"): return "principal"
    if name.endswith("info"): return "informes"
    if name.endswith("tpv"): return "tpv"
    if name.endswith("proy"): return "proyectos"
    if name.endswith("proc"): return "procesos"
    
    if name.startswith("fl"): return name[2:]
    return name

        

def to_uint32(text):
    number = 0
    for i, ch in enumerate(list(text)):
        n = ord(ch)
        byte = 3-i
        n *= 2**(8*byte)
        number += n
    return number

def read_string(f1):
    txtsize = f1.read(4)
    if len(txtsize)==0: return None
    if len(txtsize)<4: raise AssertionError, "File Error"
    slen = to_uint32(txtsize)
    
    string = f1.read(slen)
    
    try: assert(len(string) == slen)
    except AssertionError:
        print "ASSERT: len(string) %d == slen %d  ... FAILED" % (len(string), slen)
        raise
    #print slen, repr(string[:32])
    return string
    
    
def uncompress(txt):
    
    slen = to_uint32(txt[0:4])
    try:
        txt_data = zlib.decompress(txt[4:])
    except zlib.error, e:
        return None
    if slen != len(txt_data):
        print "Uncompressed data size does not match the expected size"
    #print slen, len(txt_data), repr(txt_data[:256])
    return txt_data
    

def splitpkg(iface, packagefile):
    iface.info2("Separando paquete %s . . ." % packagefile)
    f1 = open(packagefile)
    version = read_string(f1)
    foldername = packagefile+".contents"
    try:
        os.mkdir(foldername)
    except OSError, e:
        pass
    
    sys.stdout.write("|")
    sys.stdout.flush()
    open(os.path.join(foldername, "0001.header"),"w").write(version[:-1]+"\n")
    n = 1
    while n<20000:
        n+=1
        text = read_string(f1)
        if text is None: break
        unzipped = uncompress(text)
        if unzipped:
            sys.stdout.write("*")
            sys.stdout.flush()
            open(os.path.join(foldername, "%04d.file" % n),"w").write(unzipped)
        else:            
            sys.stdout.write(".")
            sys.stdout.flush()
            open(os.path.join(foldername, "%04d.text" % n),"w").write(text[:-1]+"\n")
        #if n%50 == 0:
        #    sys.stdout.write("\n")
        #    sys.stdout.flush()
    f1.close()
        
    print
    print "Hecho. %d objetos extraidos en %s" % (n,foldername)
    
def unpackpkg(iface, packagefile):
    iface.info2("Desempaquetando %s . . ." % packagefile)

    f1 = open(packagefile)
    version = read_string(f1)
    foldername = packagefile+".unpacked"
    try:
        os.mkdir(foldername)
    except OSError, e:
        pass
    
    print "Header:", version[:-1]
    n = 1    
    modulos = UnpackerClass(foldername)
    while n<20000:
        text = read_string(f1)
        if text is None: break
        unzipped = uncompress(text)
        if unzipped:
            if n == 1: modulos.feed_module(unzipped)
            if n == 2: 
                modulos.feed_files(unzipped)
                break
                
            n+=1
        else:            
            print "..", text
    
    def get_next_file(f1=f1):
        text = read_string(f1)
        if text is None: return None
        sys.stdout.write(".")
        sys.stdout.flush()
        unzipped = uncompress(text)
        return unzipped
    modulos.process_files(next_file=get_next_file)
    print
    f1.close()
        

class UnpackerClass(object):
    def __init__(self, dest):
        self.dest = dest 
    
    def feed_module(self,xmlstring):
        parser = etree.XMLParser(
                        ns_clean=True,
                        encoding="UTF-8",
                        recover=True,
                        remove_blank_text=True,
                        )
        self.modules = etree.XML(xmlstring, parser)
        self.projectname=self.modules.get("projectname",None)
        self.projectversion=self.modules.get("projectversion",None)
        self.mod = {}
        self.modpath = {}
        for module in self.modules:
            name = module.xpath("name/text()")[0]
            area = module.xpath("area/text()")[0]
            path = os.path.join(areapath(area),modulepath(name))
            path1 = os.path.join(self.dest, areapath(area) )
            path2 = os.path.join(self.dest, path )
            
            if name in self.mod: print "WARN: Modulo redeclarado:", mod
            self.mod[name] = module
            
            self.modpath[name] = path
            if not os.path.exists(path1):
                os.mkdir(path1)
            if not os.path.exists(path2):
                os.mkdir(path2)
            l_description = module.xpath("description")
            if l_description:
                l_description[0].text = l_description[0].text.strip()
                
            open(os.path.join(path2,name+".mod"),"w").write(etree.tostring(module, pretty_print=True, encoding="iso-8859-15",xml_declaration=False))
        
    def feed_files(self,xmlstring):
        parser = etree.XMLParser(
                        ns_clean=True,
                        encoding="UTF-8",
                        recover=True,
                        remove_blank_text=True,
                        )
        self.files = etree.XML(xmlstring, parser)
    
    def process_files(self, next_file):
        for ofile in self.files:
            if ofile.tag != "file": continue
            modname = ofile.xpath("module/text()")[0]
            base_path = os.path.join(self.dest, self.modpath[modname] )
            try: f_text = ofile.xpath("text/text()")[0]
            except IndexError: f_text = None
            try: f_binary = ofile.xpath("binary/text()")[0]
            except IndexError: f_binary = None
            
            if f_text: 
                name, ext = os.path.splitext(f_text)
                path = os.path.join( base_path, extpath(ext) )
                if not os.path.exists(path):
                    os.mkdir(path)
                data = next_file()
                open(os.path.join(path,f_text),"w").write(data)
                
            if f_binary: 
                name, ext = os.path.splitext(f_binary)
                path = os.path.join( base_path, extpath(ext) )
                data = next_file()
                if not os.path.exists(path):
                    os.mkdir(path)
                open(os.path.join(path,f_binary),"w").write(data)
            
            
    
    
    

