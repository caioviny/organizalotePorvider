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

    def add_action(self, icon_path, text, callback, enabled_flag=True, 
                   add_to_menu=True, add_to_toolbar=True, status_tip=None, 
                   whats_this=None, parent=None):
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        
        if status_tip is not None:
            action.setStatusTip(status_tip)
        if whats_this is not None:
            action.setWhatsThis(whats_this)
        if add_to_toolbar:
            self.iface.addToolBarIcon(action)
        if add_to_menu:
            self.iface.addPluginToVectorMenu(self.menu, action)
            
        self.actions.append(action)
        return action

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

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        self.add_action(
            icon_path,
            text=self.tr(u'Organiza Lote'),
            callback=self.run,
            parent=self.iface.mainWindow()
        )
        self.first_start = True

    def unload(self):
        for action in self.actions:
            self.iface.removePluginVectorMenu(self.tr(u'&OrganizadorDeLotes'), action)
            self.iface.removeToolBarIcon(action)

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

    def verificar_ins_quadra_existe(self, conexao, ins_quadra):
        """Verifica se já existe registros na tabela novaordem para a ins_quadra"""
        try:
            # Abordagem mais simples: Tentar buscar um registro específico
            # Se a consulta retornar dados, existe; se não retornar, não existe
            alg_params = {
                'DATABASE': conexao,
                'SQL': f'''
                    SELECT 1 as existe 
                    FROM comercial_umc.novaordem 
                    WHERE ins_quadra = {ins_quadra} 
                    LIMIT 1
                ''',
                'OUTPUT': 'memory:temp_verificacao'
            }
            
            try:
                result = processing.run('native:postgisexecuteandloadsql', alg_params)
                
                # Verificar se a camada de resultado tem features
                output_layer = result['OUTPUT']
                feature_count = output_layer.featureCount()
                
                QgsMessageLog.logMessage(
                    f"Verificação ins_quadra {ins_quadra}: {feature_count} registros encontrados", 
                    'OrganizadorDeLotes', 
                    Qgis.Info
                )
                
                # Se tem features, existem registros na tabela
                return feature_count > 0
                
            except Exception as e_inner:
                QgsMessageLog.logMessage(
                    f"Erro na consulta SQL para ins_quadra {ins_quadra}: {str(e_inner)}", 
                    'OrganizadorDeLotes', 
                    Qgis.Warning
                )
                
                # Se deu erro na consulta, pode ser que a tabela não existe ou está vazia
                # Vamos tentar uma abordagem ainda mais simples
                try:
                    alg_params_simples = {
                        'DATABASE': conexao,
                        'SQL': f'SELECT COUNT(*) FROM comercial_umc.novaordem WHERE ins_quadra = {ins_quadra}'
                    }
                    
                    # Usar apenas postgisexecutesql sem tentar carregar resultado
                    processing.run('native:postgisexecutesql', alg_params_simples)
                    
                    # Se chegou até aqui, a tabela existe
                    # Agora vamos tentar uma consulta que falhe apenas se não houver dados
                    alg_params_teste = {
                        'DATABASE': conexao,
                        'SQL': f'''
                            DO $
                            DECLARE
                                rec_count INTEGER;
                            BEGIN
                                SELECT COUNT(*) INTO rec_count 
                                FROM comercial_umc.novaordem 
                                WHERE ins_quadra = {ins_quadra};
                                
                                IF rec_count = 0 THEN
                                    RAISE EXCEPTION 'NO_RECORDS_FOUND';
                                END IF;
                            END $;
                        '''
                    }
                    
                    processing.run('native:postgisexecutesql', alg_params_teste)
                    
                    # Se chegou até aqui sem erro, existem registros
                    QgsMessageLog.logMessage(
                        f"Registros confirmados para ins_quadra {ins_quadra} via DO block", 
                        'OrganizadorDeLotes', 
                        Qgis.Info
                    )
                    return True
                    
                except Exception as e_do:
                    error_msg = str(e_do).lower()
                    if 'no_records_found' in error_msg:
                        QgsMessageLog.logMessage(
                            f"Nenhum registro encontrado para ins_quadra {ins_quadra}", 
                            'OrganizadorDeLotes', 
                            Qgis.Info
                        )
                        return False
                    else:
                        QgsMessageLog.logMessage(
                            f"Erro no DO block para ins_quadra {ins_quadra}: {str(e_do)}", 
                            'OrganizadorDeLotes', 
                            Qgis.Warning
                        )
                        return False
                
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Erro geral ao verificar ins_quadra {ins_quadra}: {str(e)}", 
                'OrganizadorDeLotes', 
                Qgis.Critical
            )
            # Em caso de erro na verificação, assumir que não existe para ser seguro
            return False

    def excluir_ins_quadra_existente(self, conexao, ins_quadra):
        """
        Exclui TODOS os registros da tabela novaordem onde ins_quadra = valor capturado
        Se existir pelo menos 1 registro com a ins_quadra, TODOS serão excluídos
        """
        try:
            # SQL que exclui TODOS os registros com a ins_quadra capturada
            sql_exclusao = f'DELETE FROM comercial_umc.novaordem WHERE ins_quadra = {ins_quadra}'
            
            QgsMessageLog.logMessage(
                f"Executando SQL de exclusão: {sql_exclusao}", 
                'OrganizadorDeLotes', 
                Qgis.Info
            )
            
            # Usar processing para executar o DELETE na conexão PostgreSQL
            alg_params = {
                'DATABASE': conexao,
                'SQL': sql_exclusao
            }
            
            processing.run('native:postgisexecutesql', alg_params)
            
            QgsMessageLog.logMessage(
                f"TODOS os registros da quadra {ins_quadra} foram excluídos da tabela novaordem com sucesso!", 
                'OrganizadorDeLotes', 
                Qgis.Info
            )
            return True
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Erro ao excluir TODOS os registros da ins_quadra {ins_quadra}: {str(e)}", 
                'OrganizadorDeLotes', 
                Qgis.Critical
            )
            return False

    def organizar_ordem_lote(self, conexao, ins_quadra, ordem_primeira, feedback=None):
        results = {}
        try:
            camada_lotes = None
            for layer in QgsProject.instance().mapLayers().values():
                if 'gis_boletim_lote' in layer.name().lower() or 'lote' in layer.name().lower():
                    camada_lotes = layer
                    break
            
            if not camada_lotes:
                raise Exception("Camada de lotes não encontrada no projeto!")

            # Extrair lotes da quadra
            alg_params = {
                'FIELD': 'ins_quadra',
                'INPUT': camada_lotes,
                'OPERATOR': 0,
                'VALUE': str(ins_quadra),
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs = processing.run('native:extractbyattribute', alg_params, feedback=feedback)
            camada_filtrada = outputs['OUTPUT']

            # Calcular offset
            offset = sum(1 for f in camada_filtrada.getFeatures() if f['ordem'] >= ordem_primeira)

            # Recalcular ordem
            expressao_ordem = f'''
                CASE
                    WHEN "ordem" >= {ordem_primeira} THEN "ordem" - ({ordem_primeira} - 1)
                    WHEN "ordem" < {ordem_primeira} THEN "ordem" + {offset}
                END
            '''

            # Garantir que o campo de saída se chama 'n_ordem'
            alg_params = {
                'FIELDS_MAPPING': [
                    {'expression': '"matricula"', 'length': -1, 'name': 'matricula', 'precision': 0, 'type': 2},
                    {'expression': '"ins_quadra"', 'length': -1, 'name': 'ins_quadra', 'precision': 0, 'type': 2},
                    {'expression': expressao_ordem, 'length': -1, 'name': 'n_ordem', 'precision': 0, 'type': 4}
                ],
                'INPUT': camada_filtrada,
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs = processing.run('native:refactorfields', alg_params, feedback=feedback)
            camada_processada = outputs['OUTPUT']

            # Exportar para PostgreSQL (tabela 'novaordem', coluna 'n_ordem')
            alg_params = {
                'ADDFIELDS': False,
                'APPEND': True,
                'A_SRS': 'EPSG:31984',
                'CLIP': False,
                'DATABASE': conexao,
                'DIM': 0,
                'GEOCOLUMN': '',
                'GTYPE': 0,
                'INDEX': False,
                'INPUT': camada_processada,
                'LAUNDER': False,
                'MAKEVALID': False,
                'OPTIONS': '',
                'OVERWRITE': False,
                'PK': 'id',
                'PRECISION': True,
                'PROMOTETOMULTI': True,
                'SCHEMA': 'comercial_umc',
                'TABLE': 'novaordem',
            }
            processing.run('gdal:importvectorintopostgisdatabaseavailableconnections', alg_params, feedback=feedback)

            results['success'] = True
            results['message'] = f"Nova ordem atualizada com sucesso!"
            
        except Exception as e:
            results['success'] = False
            results['message'] = f"Erro: {str(e)}"
            QgsMessageLog.logMessage(f"Erro: {str(e)}", 'OrganizadorDeLotes', Qgis.Critical)
            
        return results

    def executar_organizacao(self):
        try:
            conexao = self.dlg.cmbConexao.currentText()
            ins_quadra = self.dlg.spinInsQuadra.value()
            ordem_primeira = self.dlg.spinOrdemPrimeira.value()

            if not conexao:
                QMessageBox.warning(self.dlg, "Aviso", "Selecione uma conexão PostgreSQL!")
                return

            # Verificar se uma quadra válida foi selecionada (diferente do valor padrão 99)
            if ins_quadra == 99:
                QMessageBox.warning(self.dlg, "Aviso", "Selecione uma quadra clicando no botão 'Selecionar Quadra'!")
                return

            if ordem_primeira < 1:
                QMessageBox.warning(self.dlg, "Aviso", "A ordem da primeira deve ser maior que 1!")
                return

            resposta = QMessageBox.question(
                self.dlg,
                "Confirmar Operação",
                f"Reorganizar lotes da quadra {ins_quadra} a partir da ordem {ordem_primeira}?\n\n"
                f"ATENÇÃO: Todos os registros existentes da quadra {ins_quadra} na tabela novaordem serão substituídos!",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if resposta == QMessageBox.No:
                return

            feedback = QgsProcessingFeedback()
            self.iface.messageBar().pushMessage(
                "OrganizadorDeLotes", 
                "Processando...", 
                level=Qgis.Info, 
                duration=2
            )
            
            # PASSO 1: SEMPRE excluir registros existentes da ins_quadra
            QgsMessageLog.logMessage(
                f"PASSO 1: Excluindo registros existentes da quadra {ins_quadra}...", 
                'OrganizadorDeLotes', 
                Qgis.Info
            )
            
            if not self.excluir_ins_quadra_existente(conexao, ins_quadra):
                QMessageBox.critical(self.dlg, "Erro", 
                    f"Erro ao excluir registros existentes da quadra {ins_quadra}.\n"
                    "O processo foi interrompido.")
                return
            
            # PASSO 2: Inserir novos registros
            QgsMessageLog.logMessage(
                f"PASSO 2: Inserindo novos registros da quadra {ins_quadra}...", 
                'OrganizadorDeLotes', 
                Qgis.Info
            )
            
            resultados = self.organizar_ordem_lote(conexao, ins_quadra, ordem_primeira, feedback)

            if resultados.get('success', False):
                QMessageBox.information(
                    self.dlg, 
                    "Sucesso", 
                    f"Quadra {ins_quadra} reorganizada com sucesso!\n\n"
                    "✅ Registros antigos excluídos\n"
                    "✅ Nova ordem inserida"
                )
                self.dlg.close()
            else:
                QMessageBox.critical(self.dlg, "Erro", resultados.get('message', 'Erro desconhecido'))
                
        except Exception as e:
            QMessageBox.critical(self.dlg, "Erro", f"Erro durante a execução: {str(e)}")
            QgsMessageLog.logMessage(f"Erro: {str(e)}", 'OrganizadorDeLotes', Qgis.Critical)

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



 
