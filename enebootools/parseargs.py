# encoding: UTF-8
import sys
import textwrap

class Action(object):
    def __init__(self, name, description, options, args = [], function = None):
        self.name = name
        self.description = description
        self.options = options
        self.args = args    
        self.help_args = {}
        self.function = function
        
    def set_help_arg(self, **kwargs):
        self.help_args = kwargs
    
    def get_arg_help(self,arg):
        if arg not in self.args: raise ValueError, "Argument not defined"
        help = self.help_args.get(arg, "Undocumented")
        return "%s - %s" % (arg, help)
        
        
    def get_help_args(self):
        return self.name + "".join([" $%s" % arg for arg in self.args])
        
    def get_help(self):
        return "%s - %s" % (self.get_help_args(), self.description)

    def help(self):
        print "%s %s [shortopts] [options] [-- files]" % (
            self.parse.name,
            self.get_help_args(),
            )
        if self.description: 
            tw1 = textwrap.TextWrapper(
                initial_indent='  ',  
                subsequent_indent='    ',  
                )
            print          
            print tw1.fill(self.description)
            
	tw2 = textwrap.TextWrapper(
	  initial_indent='  * ',  
	  subsequent_indent=' '*12,  
	  )
        print
        print " arguments:"
        for arg in self.args:
	    print tw2.fill( self.get_arg_help(arg) )
        print
        
      
    def parse(self, p, parse_count = 0):
	self.parse = p
        self.pcount = parse_count
        if 'help' in self.parse.options:
            self.help()
            return
        self.function(self.parse, self.pcount)
        

class Parse(object):
    def __init__(self):
        self.name = None
        self.shortopts = None
        self.options = None
        self.values = None
        self.actions = None
        self.files = None
    def __str__(self):
        import pprint
        return pprint.pformat(self.__dict__)

class ArgParser(object):
    def __init__(self, description = "", debug = False, function = None, cleanup_function = None):
        self.debug = debug
        self.description = description
        self.default_actions = []
        self.actions = {}
        self.known_actions = []
        self.function = function
        self.cleanup_function = cleanup_function
    
    def declare_action(self, *args, **kwargs):
        action = Action(*args, **kwargs)
        self.insert_action(action)
	return action
        
    def insert_action(self,action):
        name = action.name
        self.known_actions.append(name) # para conservar orden
        self.actions[name] = action
    
    def help(self):
        print "%s action [shortopts] [options] [-- files]" % (self.parse.name)
        if self.description: 
            tw1 = textwrap.TextWrapper(
                initial_indent='  ',  
                subsequent_indent='    ',  
                )
            print          
            print tw1.fill(self.description)
        print
        print " actions:"
	tw2 = textwrap.TextWrapper(
	  initial_indent='  * ',  
	  subsequent_indent=' '*12,  
	  )
        for name in self.known_actions:
            action = self.actions[name]
	    print tw2.fill(action.get_help() )
        print 
    
    def parse(self):
        self.parse = Parse()
        self.parse1()
        self.parse2(parse_count = 0)
        
    def parse1(self):
        p = parse_args()
        if self.debug: print str(self.parse)
        self.parse.name = p['name']
        self.parse.shortopts = p['short-options']
        self.parse.options = p['options']
        self.parse.values = p['values']
        self.parse.actions = p['actions']
        self.parse.files = p['files']
    
    def declare_option(self, **kwargs):
        # TODO: ?????
        return 
    
    def get_action(self, name = None):
        if name is None:
            name = self.parse.actions[self.parse_count]
        if name not in self.known_actions:
            print u"ERROR: Acción %s desconocida." % (repr(name))
            return
        action = self.actions[name]
        return action
    
    def parse2(self, parse_count = 0):
        self.parse_count = parse_count
        if 'help' in self.parse.options:
            if len(self.parse.actions) == self.parse_count:
                help_value = self.parse.values['help']
                if help_value:
                    action = self.get_action(help_value)
                    if action is None: return
                    action.parse(self.parse, parse_count=self.parse_count+1)
                else:
                    self.help()
            if len(self.parse.actions) == self.parse_count+1:
                action = self.get_action()
                if action is None: return
                action.parse(self.parse, parse_count=self.parse_count+1)
            return     
                           
        if len(self.parse.actions) == 0:
            self.parse.actions = self.default_actions
            if len(self.default_actions) == 0:
                print u"ERROR: No se ha pasado ninguna acción a realizar y se requiere una"
                return
        action = self.get_action()
        if action is None: return
        if self.function: self.function(self.parse)
	action.parse(self.parse, parse_count=self.parse_count+1)
        if self.cleanup_function: self.cleanup_function(self.parse)
        

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
        
                
    


