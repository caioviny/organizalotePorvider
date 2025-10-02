from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import QgsProcessingAlgorithm
from .Organizadorlotes import OrganizadorDeLotes
from qgis.utils import iface as global_iface

class aAlgorithm(QgsProcessingAlgorithm):
    def __init__(self, iface=None):
        super().__init__()
        # Se não receber iface, tenta pegar o global
        self.iface = iface if iface else global_iface

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source. It can have any kind of
        # geometry.
      

        # We add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
    pass

    def processAlgorithm(self, parameters, context, feedback):
        dlg = OrganizadorDeLotes(self.iface)
        dlg.run()
        return {}

    def name(self):
        return 'organizador_lotes'

    def displayName(self):
        return self.tr('Organizador de Lotes')

    def group(self):
        return self.tr('Ferramentas UMC')

    def groupId(self):
        return 'umc_ferramentas'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return aAlgorithm(self.iface)
