# encoding: UTF-8
import sys

class Action(object):
    def __init__(self, name, description, options, args):
        self.name = name
        self.help = description
        self.options = options
        self.args = args    
        
    def set_help(self, desc):
        self.help = desc
    
    def get_help(self):
        help_args = self.name + "".join([" $%s" % arg for arg in self.args])
        
        return "%s - %s " % (help_args, self.help)

class Parse(object):
    def __init__(self):
        self.name = None
        self.shortopts = None
        self.options = None
        self.values = None
        self.actions = None
        self.files = None

class ArgParser(object):
    def __init__(self, debug = False):
        self.debug = debug
        self.default_actions = []
        self.actions = {}
        self.known_actions = []
    
    def declare_action(self, *args, **kwargs):
        action = Action(*args, **kwargs)
        self.insert_action(action)
        
    def insert_action(self,action):
        name = action.name
        self.known_actions.append(name) # para conservar orden
        self.actions[name] = action
    
    def help(self):
        print "%s action [shortopts] [options] [-- files]" % (self.parse.name)
        print
        print " actions:"
        for name in self.known_actions:
            action = self.actions[name]
            print "    ", action.get_help() 
        print 
    
    def parse(self):
        self.parse = Parse()
        self.parse1()
        self.parse2()
        
    def parse1(self):
        p = parse_args()
        if self.debug: print repr(p)
        self.parse.name = p['name']
        self.parse.shortopts = p['short-options']
        self.parse.options = p['options']
        self.parse.values = p['values']
        self.parse.actions = p['actions']
        self.parse.files = p['files']
    
    def parse2(self):
        if len(self.parse.actions) == 0:
            if 'help' in self.parse.options:
                self.help()
                return
            self.parse.actions = self.default_actions
            if len(self.default_actions) == 0:
                print u"ERROR: No se ha pasado ninguna acción a realizar y se requiere una"
                return
        if self.parse.actions[0] not in self.known_actions:
            print u"ERROR: Acción %s desconocida." % (repr(self.parse.actions[0]))
            return

def parse_args(args = None):
    if args is None: args = list(sys.argv)
    name = args[0]
    args = args[1:]
    actions = []
    short_options = []
    options = []
    files = []
    mode = "actions"
    invalid_chars = list("_=-<>'\"")
    curr_option = [None,None]
    for i,arg in enumerate(args):
        if mode == "actions":
            if len(arg) and arg[0] == "-": mode = "options-key"
            else:
                actions.append(arg)
                continue
                
        if mode == "options-value":
            if len(arg) and arg[0] == "-": mode = "options-key"
            else:
                curr_option[1] = arg
                mode = "options-key"
                continue

        if mode == "options-key":
            if arg == "--": 
                mode = "files"
                continue
            if arg[0] != "-":
                print u"ERROR: Se esperaba una opción parseando la linea de comando %d y encontramos un valor o fichero %s." % (i,repr(arg))
                return None
            if arg[0:2] == "--":
                curr_option = [arg[2:],None]
                options.append(curr_option)
                if '=' in arg:
                    print u"ERROR: En el parametro %d se realiza una asignación (%s), y no está permitido. Use parámetros distintos." % (i,repr(arg))
                    return None
                mode = "options-value"
                continue
            else:
                if len(options):
                    print u"ERROR: Las opciones cortas deben ser indicadas entre las acciones y las opciones largas."
                    return None
                short_options += list(arg[1:])
                continue
        if mode == "files":
            files.append(arg)
            continue
        print u"ERROR: Error no esperado en modo %s analizando parámetro %d %s" % (mode, i, repr(arg))
        return None
                
    for ichar in invalid_chars:
        if ichar in short_options: 
            print u"ERROR: encontramos carácteres no válidos %s en las opciones cortas %s" % (repr(ichar), repr(short_options))               
            return None
    kopts = []
    vopts = {}
    for key, val in options:
        kopts.append(key)
        vopts[key] = val
    return {
        'name' : name,
        'actions' : actions,
        'short-options' : short_options,
        'options' : kopts,
        'values' : vopts,
        'files' : files
    }
        
                
    


