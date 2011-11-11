# encoding: UTF-8
import sys
import textwrap

class Action(object):
    def __init__(self, name, description, options, args = [], 
                call_function = None, min_file_list = 0, max_file_list = 0, min_argcount = -1):
        self.name = name
        self.description = description
        self.options = options
        self.args = args    
        self.help_args = {}
        self.call_function = call_function
        self.min_file_list = min_file_list # Mínima cantidad de ficheros a entregar
        self.max_file_list = max_file_list # Máxima cantidad de ficheros. -1 significa sin límnite.
        self.min_argcount = min_argcount # Mínima cantidad de argumentos a pedir, -1 significa pedirlos todos.
        self.parent = None
        if self.min_argcount == -1: self.min_argcount = len(self.args)
        assert(self.min_argcount <= len(self.args))
        assert(self.min_argcount > 0)
        assert(self.min_file_list >= 0)
        assert(self.max_file_list >= -1)
        if self.max_file_list >= 0:
            assert(self.min_file_list <= self.max_file_list)
        
        
    def set_help_arg(self, **kwargs):
        self.help_args = kwargs
        
    def get_arg_var(self, arg):
        idx = self.args.index(arg)
        if idx >= self.min_argcount: 
            # Optional:
            return "?%s" % arg
        else:
            # Required:
            return "$%s" % arg
    
    def get_arg_help(self,arg):
        if arg not in self.args: raise ValueError, "Argument not defined"
        optional = False
        help = self.help_args.get(arg, "Undocumented")
        return "%s - %s" % (self.get_arg_var(arg), help)
        
        
    def get_help_args(self):
        return self.name + "".join([" %s" % self.get_arg_var(arg) for arg in self.args])
        
    def get_help(self):
        return "%s - %s" % (self.get_help_args(), self.description)

    def help(self):
    
        if self.max_file_list == 0: files = ""
        else:
            files = "-- files"
            if self.min_file_list == 0:
                files = "[ %s ]" % files
        
        print "%s %s [shortopts] [options] %s" % (
            self.parse.name,
            self.get_help_args(),
            files,
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
        if not self.parent: return
        tw2.initial_indent = '    '
        print " options:"
        for name in self.options:
            option = self.parent.options[name]
            if option.level != "action": continue
            text_parts = ["-%s" % c for c in option.short] + ["--%s" % c for c in option.aliases]
            text_parts.append(option.get_help())
            print tw2.fill(", ".join(text_parts))
        print

        
        
      
    def parse(self, p, parse_count = 0):
	self.parse = p
        self.pcount = parse_count
        if 'help' in self.parse.options:
            self.help()
            return
        
        args = []
        kwargs = {}
        refargs = self.args[:]
        
        if self.max_file_list == 0 and len(self.parse.files):
            print u"ERROR: La acción %s no soporta el uso de argumentos finales y se han recibido %d" % (
                self.name,
                len(self.parse.files),
            )
            return
        
        if self.max_file_list > 0 and len(self.parse.files) > self.max_file_list:
            print u"ERROR: La acción %s recibe como máximo %d argumentos finales y se han recibido %d" % (
                self.name,
                self.max_file_list,
                len(self.parse.files),
            )
            return
        
        if len(self.parse.files) < self.min_file_list:
            print u"ERROR: La acción %s recibe como mínimo %d argumentos finales y se han recibido %d" % (
                self.name,
                self.min_file_list,
                len(self.parse.files),
            )
            return
        
        if len(self.parse.actions[parse_count:]) < self.min_argcount:
            print u"ERROR: La acción %s espera como mínimo %d argumentos y se han recibido %d" % (
                self.name,
                self.min_argcount,
                len(self.parse.actions[parse_count:]),
            )
            return
            
        if len(self.parse.actions[parse_count:]) > len(refargs):
            print u"ERROR: La acción %s espera %d argumentos y se han recibido %d" % (
                self.name,
                len(refargs),
                len(self.parse.actions[parse_count:]),
            )
            return
        for action in self.parse.actions[parse_count:]:
            argname = refargs.pop(0)
            value = action
            # print argname, value
            kwargs[argname] = value
        return (self.call_function, args, kwargs)
        

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

class Option(object):
    def __init__(self, name, description="(not-documented-yet)", 
                    level="parser", aliases=[],
                    variable=None, short="", call_function=None):
        assert(level in ['parser','action'])
        self.name = name
        self.description = description
        self.level = level
        self.aliases = aliases
        self.variable = variable
        self.short = short
        self.call_function = call_function
        if self.variable:
            assert(self.short == "")
    
    def execute_option(self, value):
        if self.variable is None:
            if value is not None:
                print u"ERROR: La opción '%s' no acepta valores." % (self.name)
                return False
            if self.call_function is None: return True
            return self.call_function()
        else:
            if value is None:
                print u"ERROR: La opción '%s' requiere un valor." % (self.name)
                return False
            if self.call_function is None: return True
            return self.call_function(value)
        
    def get_help_args(self):
        if self.variable:
            return self.name + " " + self.variable
        else:
            return self.name 
        
    def get_help(self):
        return "--%s - %s" % (self.get_help_args(), self.description)
        
    
        


class ArgParser(object):
    def __init__(self, description = "", debug = False):
        self.debug = debug
        self.description = description
        self.actions = {}
        self.known_actions = []
        self.known_options = []
        self.options = {}
        self.short_options = {}
        
    
    def declare_option(self, *args, **kwargs):
        option = Option(*args, **kwargs)
        self.insert_option(option)
        return 

    def insert_option(self,option):
        name = option.name
        self.known_options.append(name) # para conservar orden
        self.options[name] = option
        for alias in option.aliases:
            assert( alias not in self.options)
            self.options[alias] = option
        for short in list(option.short):
            self.short_options[short] = option
        

    def declare_action(self, *args, **kwargs):
        action = Action(*args, **kwargs)
        self.insert_action(action)
	return action
        
    def insert_action(self,action):
        name = action.name
        action.parent = self
        self.known_actions.append(name) # para conservar orden
        self.actions[name] = action
    
    def help(self):
        print "%s action [options] [-- files]" % (self.parse.name)
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
        tw2.initial_indent = '    '
        print " options:"
        for name in self.known_options:
            option = self.options[name]
            if option.level != "parser": continue
            text_parts = ["-%s" % c for c in option.short] + ["--%s" % c for c in option.aliases]
            text_parts.append(option.get_help())
            print tw2.fill(", ".join(text_parts))

        print
    
    def parse_args(self, argv = None):
        self.parse = Parse()
        if self.parse1(argv) == False: return
        action_list = self.parse2(parse_count = 0)
        return action_list
        
    def parse1(self, argv):
        p = parse_args(argv)
        if not p: return False
        self.parse.name = p['name']
        self.parse.shortopts = p['short-options']
        self.parse.options = p['options']
        self.parse.values = p['values']
        self.parse.actions = p['actions']
        self.parse.files = p['files']
        if self.debug or 'debug-parseargs' in self.parse.options: print str(self.parse)
    
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
        if 'h' in self.parse.shortopts: 
            self.parse.options.append("help")
            self.parse.values["help"] = None
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
                           
        if len(self.parse.actions) == self.parse_count:
            print u"ERROR: No se ha indicado  ninguna acción a realizar y se requiere una"
            return
        action_list = []
        action = self.get_action()
        if action is None: return
        
        call_action = action.parse(self.parse, parse_count=self.parse_count+1)
        if not call_action: return

        for name in self.parse.options:
            if name not in self.options:
                print u"ERROR: Opción '%s' desconocida." % name
                return
            option = self.options[name]
            if option.execute_option(self.parse.values[name]) == False:
                print u"Hubo un error procesando la opción '%s'." % (name)
                return
        
        for name in self.parse.shortopts:
            if name not in self.short_options:
                print u"ERROR: Opción corta '%s' desconocida." % name
                return
            option = self.short_options[name]
            if option.execute_option(None) == False:
                print u"Hubo un error procesando la opción '%s'." % (name)
                return
            
        
        action_list.append(call_action)
        return action_list
        

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
                #if len(options):
                #    print u"ERROR: Las opciones cortas deben ser indicadas entre las acciones y las opciones largas."
                #    return None
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
        
                
    


