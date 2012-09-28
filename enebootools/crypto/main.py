# encoding: UTF-8
import hashlib
import re
import datetime
import os
import os.path
from StringIO import StringIO
from base64 import b64encode, b64decode

from lxml import etree
from M2Crypto import EVP, X509, RSA

def hash_file(hashobj, filepath):
    File = open(filepath)
    while True:
        buf = File.read(0x10000)
        if not buf:
            break
        hashobj.update(buf)
    return hashobj

def format_checksum_filename(modulename, serial):
    letters = list('abcdefghijklmnopqrstuvwxyz')
    strdate = datetime.date.today().isoformat()
    return '%s-%s%s.checksum' % (modulename, strdate, letters[serial])
    

def get_new_checksum_filename(iface, dirname, modulename):
    checksumfiles = [ entry for entry in os.listdir(dirname) if entry.endswith(".checksum") and entry.startswith(modulename) ]
    for serial in range(27):
        filename = format_checksum_filename(modulename, serial)
        if filename not in checksumfiles: break
    if checksumfiles:
        if filename < max(checksumfiles):
             print "WARN: Fichero de firma a generar es alfabeticamente menor a otro ya existente."
    return filename, checksumfiles
    

def module_checksum(iface):
    try:
        module = [ name for name in os.listdir(".") if name.endswith(".mod") ][0]
    except IndexError:
        raise ValueError, "La carpeta actual no contiene un fichero de modulo"
    print u"Module checksum for %s . . ." % repr(module)
    module = os.path.realpath(module)
    if not os.path.exists(module):
        raise AssertionError, "File does not exist: %s" % module
    if not module.endswith(".mod"):
        raise AssertionError, "File does not end in '.mod': %s" % module
        
    dirname = os.path.dirname(module)
    modulefile = os.path.basename(module)
    modulename = os.path.splitext(modulefile)[0]
    
    valid_ext = [
        ".xml", 
        ".qs",
        ".mtd",
        ".kut",
        ".qry",
        ".ui",
        ".ts",
        ".mod",
        ".xpm",
    ]
    checksumfile, olderfiles = get_new_checksum_filename(iface,dirname,modulename)
    checksum_format = "SHA-256:hex"
    checksum_version = "1.0"

    xmlroot = etree.Element("eneboo-checksums")
    xmlroot.set("file-scope","module:%s" % modulename)
    xmlroot.set("format",checksum_format)
    xmlroot.set("version",checksum_version)
    #print checksumfile
    file_keypairs = []
    for root, dirs, files in os.walk(dirname):
        for filename in files:
            name, ext = os.path.splitext(filename)
            if ext not in valid_ext: continue
            hashobj = hashlib.sha256()
            filepath = os.path.join(root, filename)
            hash_file(hashobj, filepath)
            file_keypairs.append( (filename, hashobj.hexdigest()) ) 
    
    for filename, digest in sorted(file_keypairs):
        xmlfile = etree.SubElement(xmlroot,"file")
        xmlfile.set("name",filename)
        xmlfile.text = digest
    
    xmlparser = etree.XMLParser(ns_clean=True, remove_blank_text=True,remove_comments=True,remove_pis=True)

    xmltext = etree.tostring(xmlroot, pretty_print=True)     
    
    # Comprobar si alguno de los que ya existe coincide semanticamente con lo que vamos a crear:    
    newtree = etree.parse(StringIO(xmltext), parser = xmlparser)
    xmlc14n_io = StringIO()
    xmlroot.getroottree().write_c14n(xmlc14n_io)  
    
    xmlc14n = xmlc14n_io.getvalue() # etree.tostring(xmlroot, method='c14n')         
    xmlc14n_digest = hashlib.sha256()
    xmlc14n_digest.update(xmlc14n)
    xmlc14n_digest = xmlc14n_digest.hexdigest()
    for oldfile in olderfiles:
        try:
            oldtree = etree.parse(oldfile, parser = xmlparser)
        except Exception, e:
            continue
        oldxmlc14n_io = StringIO()
        oldtree.write_c14n(oldxmlc14n_io)  
            
        oldxmlc14n =  oldxmlc14n_io.getvalue() # etree.tostring(oldtree.getroot(), method='c14n')         
        oldxmlc14n_digest = hashlib.sha256()
        oldxmlc14n_digest.update(oldxmlc14n)
        oldxmlc14n_digest = oldxmlc14n_digest.hexdigest()
        if xmlc14n_digest == oldxmlc14n_digest:
            print "INFO: El fichero de checksum %s ya era valido." % oldfile
            return oldfile
    # ---------------
    
    
    f1 = open(checksumfile, "w")
    f1.write(xmltext)
    f1.close()
    print "Se ha generado el fichero %s" % checksumfile
    return checksumfile


    

def new_certificates_file(iface):
    xmlroot = etree.Element("eneboo-certificates")
    xmlroot.set("version","1.0")
    return xmlroot
    
            
            
def add_certificate(iface, pemfile):
    try:
        module = [ name for name in os.listdir(".") if name.endswith(".mod") ][0]
    except IndexError:
        raise ValueError, "La carpeta actual no contiene un fichero de modulo"

    modulename, ext = os.path.splitext(module)
    certificates_file = modulename + ".certificates"
    cert1 = X509.load_cert(pemfile)
    
    if not os.path.exists(certificates_file):
        print "INFO: El fichero %s no existe, será creado." % certificates_file
        xmlcert_root = new_certificates_file(iface)
    else:
        # Parse certificates xml here:
        xmlparser = etree.XMLParser(ns_clean=True, remove_blank_text=True,remove_comments=False,remove_pis=True)
        newtree = etree.parse(certificates_file, parser = xmlparser)
        xmlcert_root = newtree.getroot()
        xmlcert_root.text = None

    for n in xmlcert_root.xpath("certificate[@fingerprint-sha256='%s']" % cert1.get_fingerprint('sha256').lower()):
        print "El certificado ya está insertado en el fichero."
        return cert1   

    xmlcertificate = etree.SubElement(xmlcert_root,"certificate")
    xmlcertificate.set("O",cert1.get_subject().O)
    xmlcertificate.set("CN",cert1.get_subject().CN)
    xmlcertificate.set("emailAddress",cert1.get_subject().emailAddress)
    xmlcertificate.set("fingerprint-sha256",cert1.get_fingerprint('sha256').lower())
    xmlcertificate.text = cert1.as_pem()
    xmlcertificate.text = "\n" + cert1.as_pem() + "  "
    
    
    xmltext = etree.tostring(xmlcert_root, pretty_print=True)     
    f1 = open(certificates_file, "w")
    f1.write(xmltext)
    f1.close()
    
    print "Se ha escrito el fichero %s" % certificates_file
    return cert1

def create_signature_options(iface):
    # Crea ociones de firma por defecto mirando opciones en iface
    # Intencionalidad por defecto de la firma:
    def_intention = [
        "signatory",       # El firmante
        #"code-author",    # El autor del código
        #"code-reviewer",  # El revisor del código
        #"code-guaranteed", # Código garantizado por
        #"code-generated",  # Código generado por
        
        ]
    # Extensiones analizadas por defecto:
    def_ext = [
            ".xml", 
            ".qs",
            ".mtd",
            ".kut",
            ".qry",
            ".ui",
            ]
    # Plazo de validez por defecto:
    today = datetime.date.today()
    delta = datetime.timedelta(days=30*9)
    def_since = today # .isoformat()
    def_until = (today + delta)
    
    # Comprobaciones por defecto
    def_additional_checks = [
            # "no-new-file-check", # <- se comenta para evitar colisiones con ficheros temporales
            "no-deleted-file-check",
            ]
            
    now = datetime.datetime.utcnow()

    xmlroot = etree.Element("eneboo-checksum-options")
    xmlroot.set("version","1.0")
    xmldt = etree.SubElement(xmlroot,"datetime", TZ="UTC")
    xmldt.text = now.isoformat()

    xmlvalid = etree.SubElement(xmlroot,"valid")
    xmlsince = etree.SubElement(xmlvalid,"since")
    xmluntil = etree.SubElement(xmlvalid,"until")
    xmlsince.text = def_since.isoformat()
    xmluntil.text = def_until.isoformat()
    
    xmlchecks = etree.SubElement(xmlroot,"checks")
    for ext in def_ext:
        xmlfiletype = etree.SubElement(xmlchecks,"filetype")
        xmlfiletype.text = ext

    for check in def_additional_checks:
        xmladdcheck = etree.SubElement(xmlchecks,"additional-check")
        xmladdcheck.text = check

    xmlmetadata = etree.SubElement(xmlroot,"metadata")
    for intention in def_intention:
        xmlintention = etree.SubElement(xmlmetadata,"intention")
        xmlintention.text = intention
    
    
    
    xmltext = etree.tostring(xmlroot, pretty_print=True)     
    
    return xmltext
    
    
def new_signatures_file(iface):
    xmlroot = etree.Element("eneboo-signatures")
    xmlroot.set("version","1.0")
    return xmlroot
    
            
                
        
def add_signature(iface,certpem,pkeypem):
    try:
        module = [ name for name in os.listdir(".") if name.endswith(".mod") ][0]
    except IndexError:
        raise ValueError, "La carpeta actual no contiene un fichero de modulo"

    modulename, ext = os.path.splitext(module)
    signatures_file = modulename + ".signatures"

    if not os.path.exists(signatures_file):
        print "INFO: El fichero %s no existe, será creado." % signatures_file
        xmlsign_root = new_signatures_file(iface)
    else:
        # Parse certificates xml here:
        xmlparser = etree.XMLParser(ns_clean=True, remove_blank_text=True,remove_comments=False,remove_pis=True)
        newtree = etree.parse(signatures_file, parser = xmlparser)
        xmlsign_root = newtree.getroot()
        xmlsign_root.text = None


    cert1 = add_certificate(iface,certpem)
    checksum_file = module_checksum(iface)
    check_opts = create_signature_options(iface)


    
    signed_document = etree.SubElement(xmlsign_root, "signed-document")
    signed_document.set("check","true")

    xmlcertificate = etree.SubElement(signed_document,"signer-certificate")
    xmlcertificate.set("O",cert1.get_subject().O)
    xmlcertificate.set("CN",cert1.get_subject().CN)
    xmlcertificate.set("emailAddress",cert1.get_subject().emailAddress)
    xmlcertificate.set("fingerprint-sha256",cert1.get_fingerprint('sha256').lower())

    xmldocument = etree.SubElement(signed_document,"document")
    xmldocument.set("format","tag:name:sha256")

    hashobj = hashlib.sha256()
    hash_file(hashobj, checksum_file)
    checksum_file_hash = hashobj.hexdigest()

    hashobj = hashlib.sha256()
    hashobj.update(check_opts)
    check_opts_hash = hashobj.hexdigest()

    xmlchecksumfile = etree.SubElement(xmldocument,"file")
    xmlchecksumfile.set("name","checksums.xml")
    xmlchecksumfile.set("href",checksum_file)
    xmlchecksumfile.set("sha256",checksum_file_hash)
    
    xmlchecksumoptions = etree.SubElement(xmldocument,"data")
    xmlchecksumoptions.set("name","checksum-options.xml")
    xmlchecksumoptions.set("format","base64")
    xmlchecksumoptions.set("sha256",check_opts_hash)
    xmlchecksumoptions.text = b64encode(check_opts)
    
    
    
    
    
    data = ""
    for node in xmldocument:
        data += "%s:%s:%s\n" % (node.tag, node.get("name"), node.get("sha256"))

    hashobj = hashlib.sha256()
    hashobj.update(data)
    data_hash = hashobj.hexdigest()
    xmldocument.set("sha256", data_hash)
    
    cert1 = X509.load_cert(certpem)
    cert1_pkey = cert1.get_pubkey()
    cert1_pkey.reset_context(md='sha256')
    
    rsa1 = RSA.load_key(pkeypem)    
    sevp = EVP.PKey(md='sha256')
    sevp.assign_rsa(rsa1)
    sevp.sign_init()
    sevp.sign_update(data)
    signature = sevp.sign_final()

    xmlsignature = etree.SubElement(signed_document,"signature",format="SHA-256:RSASSA-PKCS1v1.5:base64")
    xmlsignature.text = b64encode(signature)

    cert1_pkey.verify_init()
    cert1_pkey.verify_update(data)
    verification = cert1_pkey.verify_final(signature)
    if verification != 1:
        print "ERROR: Verificacion de firma erronea, devolvio %d. Compruebe que la firma corresponde al certificado." % verification
        return

    # Eliminar firmas previas que sean del mismo firmante.
    for signed_doc in xmlsign_root.xpath("signed-document[signer-certificate/@fingerprint-sha256='%s']" % cert1.get_fingerprint('sha256').lower()):
        doc_sha256 = signed_doc.xpath("document/@sha256")[0]
        if doc_sha256 == data_hash: continue
        print "INFO: Se elimina firma antigua del mismo certificado."
        xmlsign_root.remove(signed_doc)
        
        
    
    xmltext = etree.tostring(xmlsign_root, pretty_print=True)     
    f1 = open(signatures_file, "w")
    f1.write(xmltext)
    f1.close()
    
    print "Se ha escrito el fichero %s" % signatures_file
    
            
        
def check(iface):
    try:
        module = [ name for name in os.listdir(".") if name.endswith(".mod") ][0]
    except IndexError:
        raise ValueError, "La carpeta actual no contiene un fichero de modulo"

    modulename, ext = os.path.splitext(module)
    xmlparser = etree.XMLParser(ns_clean=True, remove_blank_text=True,remove_comments=True,remove_pis=True)

    print "Comprobacion general de los checksums en el modulo %s:" % modulename
    dirname = "."
    x, chk_list = get_new_checksum_filename(iface,dirname,modulename)
    
    valid_ext = [
        ".xml", 
        ".qs",
        ".mtd",
        ".kut",
        ".qry",
        ".ui",
        ".ts",
        ".mod",
        ".xpm",
    ]    
    file_hashes = {}
    for root, dirs, files in os.walk(dirname):
        for filename in files:
            name, ext = os.path.splitext(filename)
            if ext not in valid_ext: continue
            hashobj = hashlib.sha256()
            filepath = os.path.join(root, filename)
            hash_file(hashobj, filepath)
            file_hashes[filename] = hashobj.hexdigest()
    
    for checksumfile in chk_list:
        print "Analizando %s . . . " % checksumfile
        try:
            xmlchktree = etree.parse(checksumfile, parser = xmlparser)
        except Exception, e:
            continue
        xmlchkroot = xmlchktree.getroot()
        if xmlchkroot.tag != "eneboo-checksums": 
            print "WARN: Unknown checksum file with tag <%s>, probably is a wrong file!" % xmlchkroot.tag
            
        if xmlchkroot.get("format") != "SHA-256:hex": 
            print "WARN: Unexpected checksum format `%s`, probably checks will fail!" % xmlchkroot.get("format")
            
        if xmlchkroot.get("version") != "1.0": 
            print "WARN: Unexpected checksum file version `%s`, checks may fail." % xmlchkroot.get("version")
            
        chk_filenames = file_hashes.keys()
        for element in xmlchkroot:
            if element.tag == "file":
                name, fhash = element.get('name'), element.text
                if name in file_hashes: 
                    chk_filenames.remove(name)
                    if fhash != file_hashes[name]:
                        print "ERROR: Fichero '%s' modificado" % name
                else:
                    print "ERROR: Fichero '%s' borrado" % name
                
            else:
                print "WARN: Unknown and ignored tag:", element.tag
        
        if chk_filenames:
            print "ERROR: ficheros agregados: %s" % (", ".join(chk_filenames))
    

    print "Comprobacion general de los certificados en el modulo %s:" % modulename

    certificates_file = modulename + ".certificates"
    
    if os.path.exists(certificates_file):
        # Parse certificates xml here:
        newtree = etree.parse(certificates_file, parser = xmlparser)
        xmlcert_root = newtree.getroot()
        xmlcert_root.text = None
    else:
        print "INFO: El fichero de certificados %s no existe" % certificates_file
        xmlcert_root = new_certificates_file(iface)

    if xmlcert_root.tag != "eneboo-certificates":
            print "WARN: Unknown certificates file with tag <%s>, probably is a wrong file!" % xmlcert_root.tag
    if xmlcert_root.get("version") != "1.0": 
        print "WARN: Unexpected certificates file version `%s`, load may fail." % xmlcert_root.get("version")
    
    cert_dict = {}
    for element in xmlcert_root:
        if element.tag == "certificate":
            try:
                cert1 = X509.load_cert_string(element.text)
                
            except Exception, e:
                element.text = None
                print "ERROR: Error desconocido al cargar el certificado %s: %s" % (etree.tostring(element), repr(e))
                continue
            
            fingerprint = cert1.get_fingerprint('sha256').lower()
            cert_dict[fingerprint] = cert1
            if cert1.check_ca():
                print "WARN: Certificado CA cargado:", cert1.get_subject().as_text()
            else:
                print "INFO: Certificado cargado:", cert1.get_subject().as_text()
        else:
            print "WARN: Unknown and ignored tag:", element.tag
    
    
    print "Comprobacion general de los firmas en el modulo %s:" % modulename
    
    signatures_file = modulename + ".signatures"
    
    if os.path.exists(signatures_file):
        # Parse certificates xml here:
        newtree = etree.parse(signatures_file, parser = xmlparser)
        xmlsign_root = newtree.getroot()
        xmlsign_root.text = None
    else:
        print "INFO: El fichero de firmas %s no existe" % signatures_file
        xmlsign_root = new_signatures_file(iface)
        

    if xmlsign_root.tag != "eneboo-signatures":
            print "WARN: Unknown signatures file with tag <%s>, probably is a wrong file!" % xmlsign_root.tag
    if xmlsign_root.get("version") != "1.0": 
        print "WARN: Unexpected certificates file version `%s`, load may fail." % xmlsign_root.get("version")
    
    for element in xmlsign_root:
        if element.tag == "signed-document":
            signer_certificate, document, signature = None, None, None
            for subelement in element:
                if subelement.tag == "signer-certificate":
                    if signer_certificate is not None: print "WARN: signer-certificate duplicado."
                    signer_certificate = subelement
                elif subelement.tag == "document":
                    if document is not None: print "WARN: document duplicado."
                    document = subelement
                elif subelement.tag == "signature":
                    if signature is not None: print "WARN: signature duplicado."
                    signature = subelement
                else:                    
                    print "WARN: Unknown and ignored subtag:", subelement.tag
                    
            if signer_certificate is None: 
                print "ERROR: required signer-certificate tag not found."
                continue
            if document is None: 
                print "ERROR: required document tag not found."
                continue
            if signature is None: 
                print "ERROR: required signature tag not found."
                continue
            
            fingerprint = signer_certificate.get("fingerprint-sha256")
            if fingerprint not in cert_dict:
                print "ERROR: certificate not found."
                continue
            certificate = cert_dict[fingerprint]
            
            print "Signature valid??"
            
        else:
            print "WARN: Unknown and ignored tag:", element.tag
        
        

    
    
    
    
    
