# encoding: UTF-8
import enebootools
from enebootools import EnebooToolsInterface
import sys, traceback

reload(sys)  
sys.setdefaultencoding('utf8')


class VCSInterface(EnebooToolsInterface):
    module_description = u"Herramientas para la integración con un VCS"

class GITInterface(VCSInterface):
    module_description = u"Herramientas para la integración con GIT"
