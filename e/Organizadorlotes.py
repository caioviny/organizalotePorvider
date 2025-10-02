# -*- coding: utf-8 -*-
"""
OrganizadorDeLotes
A QGIS plugin to organize lots within a block.
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.gui import QgsMapToolIdentifyFeature
from qgis.core import QgsProject, QgsFeature, QgsProcessing, QgsProcessingFeedback, QgsMessageLog, Qgis

from .OrganizadorLotesdialog import OrganizadorDeLotesDialog
import os.path
import processing

class OrganizadorDeLotes:

    def __init__(self, iface=None):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.tool = None
        self.dlg = None
        self.first_start = True

        # Carregar tradução
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(self.plugin_dir, 'i18n', f'OrganizadorDeLotes_{locale}.qm')
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

    def tr(self, message):
        return QCoreApplication.translate('OrganizadorDeLotes', message)

    def resetar_valores_plugin(self):
        """Reseta valores do plugin de forma segura"""
        try:
            if self.tool is not None and self.iface:
                self.iface.mapCanvas().unsetMapTool(self.tool)
                self.tool = None

            if self.iface:
                self.iface.mainWindow().unsetCursor()
                self.iface.mainWindow().statusBar().clearMessage()

            if self.dlg is not None:
                if hasattr(self.dlg, 'spinOrdemPrimeira'):
                    self.dlg.spinOrdemPrimeira.setValue(1)
                if hasattr(self.dlg, 'cmbConexao') and self.dlg.cmbConexao.count() > 0:
                    self.dlg.cmbConexao.setCurrentIndex(0)

            QgsMessageLog.logMessage("Valores do plugin resetados com sucesso", 'OrganizadorDeLotes', Qgis.Info)
        except Exception as e:
            QgsMessageLog.logMessage(f"Erro ao resetar valores: {str(e)}", 'OrganizadorDeLotes', Qgis.Warning)

    def run(self):
        """Abre o diálogo do Qt Designer"""
        self.resetar_valores_plugin()

        if self.first_start:
            self.first_start = False
            self.dlg = OrganizadorDeLotesDialog()

            if hasattr(self.dlg, 'btnSelecionarQuadra') and hasattr(self, 'ativarFerramentaSelecao') and self.iface:
                self.dlg.btnSelecionarQuadra.clicked.connect(self.ativarFerramentaSelecao)

            if hasattr(self.dlg, 'cmbConexao'):
                self.dlg.cmbConexao.clear()
                conexoes = self.listar_conexoes_postgis()
                parent = self.iface.mainWindow() if self.iface else None
                if not conexoes:
                    QMessageBox.warning(parent, "Aviso", "Nenhuma conexão PostgreSQL encontrada!")
                    return
                for nome in conexoes:
                    self.dlg.cmbConexao.addItem(nome)

            if hasattr(self.dlg, 'btnExecutar'):
                self.dlg.btnExecutar.clicked.connect(self.executar_organizacao)

        self.dlg.show()
        if hasattr(self.dlg, 'exec_'):
            self.dlg.exec_()

    # ============================
    # Métodos originais abaixo
    # ============================

    def listar_conexoes_postgis(self):
        settings = QSettings()
        settings.beginGroup('PostgreSQL/connections')
        conexoes = settings.childGroups()
        settings.endGroup()
        return conexoes

    def ativarFerramentaSelecao(self):
        if not self.iface or not self.dlg:
            return

        quadra_layer = None
        for layer in QgsProject.instance().mapLayers().values():
            if layer.name() == "Quadra":
                quadra_layer = layer
                break

        if not quadra_layer:
            QMessageBox.warning(self.iface.mainWindow(), "Aviso", "Camada 'Quadra' não encontrada!")
            return

        self.tool = QgsMapToolIdentifyFeature(self.iface.mapCanvas())
        self.tool.setLayer(quadra_layer)
        self.tool.featureIdentified.connect(self.capturarInsQuadra)
        self.iface.mapCanvas().setMapTool(self.tool)
        self.iface.mainWindow().setCursor(Qt.PointingHandCursor)

    def capturarInsQuadra(self, feature):
        if not self.dlg:
            return

        if feature.isValid():
            if 'ins_quadra' in feature.fields().names():
                ins_quadra = feature['ins_quadra']
                QMessageBox.information(self.dlg, "Quadra Capturada", f"Quadra capturada: {ins_quadra}")
                if hasattr(self.dlg, 'spinInsQuadra'):
                    self.dlg.spinInsQuadra.setValue(ins_quadra)
        if self.iface:
            self.iface.mapCanvas().unsetMapTool(self.tool)
            self.iface.mainWindow().unsetCursor()
            self.tool = None

    def executar_organizacao(self):
        # Aqui vai todo o seu código de execução original
        pass

    # TODO: manter todos os métodos que você já tinha, como organizar_ordem_lote, excluir_ins_quadra_existente, verificar_ins_quadra_existe
