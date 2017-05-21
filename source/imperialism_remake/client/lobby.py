# Imperialism remake
# Copyright (C) 2016 Trilarion
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

"""
Game lobby. Place for starting/loading games.
"""

from functools import partial

import PyQt5.QtCore as QtCore
import PyQt5.QtGui as QtGui
import PyQt5.QtWidgets as QtWidgets

from imperialism_remake.base import constants, tools
import imperialism_remake.base.network as base_network
import imperialism_remake.client.graphics as graphics
from imperialism_remake.lib import qt, utils
from imperialism_remake.client.client import local_network_client


class GameLobbyWidget(QtWidgets.QWidget):
    """
    Content widget for the game lobby.
    """

    single_player_start = QtCore.pyqtSignal(str, str)

    def __init__(self, *args, **kwargs):
        """
        Create toolbar.
        """
        super().__init__(*args, **kwargs)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # create tool bar
        toolbar = QtWidgets.QToolBar()
        action_group = QtWidgets.QActionGroup(toolbar)

        # actions single player new/load
        a = qt.create_action(tools.load_ui_icon('icon.lobby.single.new.png'), 'Start new single player scenario', action_group, toggle_connection=self.toggled_single_player_scenario_selection, checkable=True)
        toolbar.addAction(a)
        a = qt.create_action(tools.load_ui_icon('icon.lobby.single.load.png'), 'Continue saved single player scenario', action_group, toggle_connection=self.toggled_single_player_load_scenario, checkable=True)
        toolbar.addAction(a)

        toolbar.addSeparator()

        # actions multi player
        a = qt.create_action(tools.load_ui_icon('icon.lobby.network.png'), 'Show server lobby', action_group, toggle_connection=self.toggled_server_lobby, checkable=True)
        toolbar.addAction(a)
        a = qt.create_action(tools.load_ui_icon('icon.lobby.multiplayer-game.png'), 'Start or continue multiplayer scenario', action_group, toggle_connection=self.toggled_multiplayer_scenario_selection, checkable=True)
        toolbar.addAction(a)

        self.layout.addWidget(toolbar, alignment=QtCore.Qt.AlignTop)

        self.content = None


    def change_content_widget(self, widget, alignment=None):
        """
        Another screen shall be displayed. Exchange the content widget with a new one.
        """
        if self.content:
            self.layout.removeWidget(self.content)
            self.content.deleteLater()

        self.content = widget

        if self.content:
            # self.layout.addWidget(widget, stretch=1, alignment=QtCore.Qt.AlignCenter)
            if alignment:
                self.layout.addWidget(widget, stretch=1, alignment=alignment)
            else:
                self.layout.addWidget(widget, stretch=1)

    def toggled_single_player_scenario_selection(self, checked):
        """
        Toolbar action switch to single player scenario selection.
        """

        if checked:
            # create single player scenario title selection widget
            widget = SinglePlayerScenarioTitleSelection()
            # widget.title_selected.connect(self.single_player_scenario_selection_preview, QtCore.Qt.QueuedConnection)
            widget.title_selected.connect(self.single_player_scenario_selection_preview)

            # change content widget
            self.change_content_widget(widget, QtCore.Qt.AlignVCenter)

    def toggled_single_player_load_scenario(self, checked):
        """
        Toolbar action switch to single player load a scenario.
        """

        if checked:
            # noinspection PyCallByClass
            file_name = QtWidgets.QFileDialog.getOpenFileName(self, 'Continue Single Player Scenario', constants.SCENARIO_FOLDER, 'Scenario Files (*.scenario)')[0]
            if file_name:
                # TODO check that it is a valid single player scenario in play
                pass

    def toggled_server_lobby(self, checked):
        """
        Toolbar action switch to server lobby.
        """
        if checked:
            # create new widget
            widget = ServerLobby()

            # change content widget
            self.change_content_widget(widget)

    def toggled_multiplayer_scenario_selection(self, checked):
        """
        Toolbar action switch to multiplayer scenario selection.
        """
        if checked:
            pass

    def single_player_scenario_selection_preview(self, scenario_file):
        """
        Single player scenario selection, a scenario title was selected, show preview.
        """

        # create single player scenario preview widget
        widget = SinglePlayerScenarioPreview(scenario_file)
        widget.nation_selected.connect(partial(self.single_player_start.emit, scenario_file))
        #widget.nation_selected.connect(

        # change content widget
        self.change_content_widget(widget)


class ServerLobby(QtWidgets.QWidget):
    """
    Server lobby.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QtWidgets.QHBoxLayout(self)

        self.client_list_widget = QtWidgets.QListWidget()
        # list.itemSelectionChanged.connect(self.selection_changed)
        # list.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.client_list_widget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.client_list_widget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.client_list_widget.setFixedWidth(200)
        layout.addWidget(qt.wrap_in_groupbox(self.client_list_widget, 'Players'))

        self.chat_log_text_edit = QtWidgets.QTextEdit()
        self.chat_log_text_edit.setEnabled(False)
        chat_log_group = qt.wrap_in_groupbox(self.chat_log_text_edit, 'Chat log')

        self.chat_input_edit = QtWidgets.QLineEdit()
        self.chat_input_edit.returnPressed.connect(self.send_chat_message)
        chat_input_group = qt.wrap_in_groupbox(self.chat_input_edit, 'Chat input')
        layout.addLayout(qt.wrap_in_boxlayout((chat_log_group, chat_input_group), horizontal=False, add_stretch=False), stretch=1)

        # connection to server

        # chat messages
        local_network_client.connect_to_channel(constants.C.CHAT, self.receive_chat_messages)
        local_network_client.send(constants.C.CHAT, constants.M.CHAT_SUBSCRIBE)

        # LOBBY
        local_network_client.connect_to_channel(constants.C.LOBBY, self.receive_lobby_messages)
        self.request_updated_client_list()

        # set timer for connected client updates
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.request_updated_client_list)
        self.timer.setInterval(5000)
        self.timer.start()

    def send_chat_message(self):
        """
        Sends a chat message.
        """
        chat_message = self.chat_input_edit.text()
        local_network_client.send(constants.C.CHAT, constants.M.CHAT_MESSAGE, chat_message)
        self.chat_input_edit.setText('')

    def receive_chat_messages(self, client: base_network.NetworkClient, channel: constants.C, action: constants.M, content):
        """
        Receives a chat message. Adds it to the chat log.

        :param client:
        :param channel:
        :param action:
        :param content:
        """
        if action == constants.M.CHAT_MESSAGE:
            self.chat_log_text_edit.append(content)

    def request_updated_client_list(self):
        """
        Sends a request to get an updated connected client list.
        """
        local_network_client.send(constants.C.LOBBY, constants.M.LOBBY_CONNECTED_CLIENTS)

    def receive_lobby_messages(self, client: base_network.NetworkClient, channel: constants.C, action: constants.M, content):
        """
        Handles all received lobby messages.

        :param client:
        :param channel:
        :param action:
        :param content:
        """
        if action == constants.M.LOBBY_CONNECTED_CLIENTS:
            self.client_list_widget.clear()
            self.client_list_widget.addItems(content)

    def cleanup(self, parent_widget):
        """
        User wants to close the dialog

        :param parent_widget:
        """
        local_network_client.send(constants.C.CHAT, constants.M.CHAT_UNSUBSCRIBE)
        local_network_client.disconnect_from_channel(constants.C.CHAT, self.receive_chat_messages)

        local_network_client.disconnect_from_channel(constants.C.LOBBY, self.receive_lobby_messages)

        return True

class SinglePlayerScenarioPreview(QtWidgets.QWidget):
    """
    Displays the preview of a single player scenario in the game lobby.

    If a nation is selected the nation_selected signal is emitted with the nation name.
    """

    #: signal, emitted if a nation is selected and the start button is presed
    nation_selected = QtCore.pyqtSignal(int)

    def __init__(self, scenario_file):
        """
            Given a scenario file name, get the preview from the server.
        """
        # TODO move the network communication outside this class.
        super().__init__()

        # add a channel for us
        local_network_client.connect_to_channel(constants.C.LOBBY, self.received_preview)

        # send a message and ask for preview
        local_network_client.send(constants.C.LOBBY, constants.M.LOBBY_SCENARIO_PREVIEW, scenario_file)

        self.selected_nation = None

    def received_preview(self, client, channel, action, message):
        """
        Populates the widget after the network reply comes from the server with the preview.
        """

        # immediately unsubscribe, we need it only once
        local_network_client.disconnect_from_channel(constants.C.LOBBY, self.received_preview)

        # unpack message
        nations = [(message['nations'][key][constants.NationProperty.NAME], key) for key in message['nations']]
        nations = sorted(nations)  # by first element, which is the name
        nation_names, self.nation_ids = list(zip(*nations))

        # fill the widget with useful stuff
        layout = QtWidgets.QGridLayout(self)

        # selection list for nations
        self.nations_list = QtWidgets.QListWidget()
        # self.nations_list.setFixedWidth(200)
        self.nations_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.nations_list.itemSelectionChanged.connect(self.nations_list_selection_changed)
        self.nations_list.addItems(nation_names)
        self.nations_list.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.nations_list.setFixedWidth(self.nations_list.sizeHintForColumn(0) + 2 * self.nations_list.frameWidth() + 17 + 10) # 10px extra
        # TODO use app.style().pixelMetric(QtWidgets.QStyle.PM_ScrollBarExtent)
        layout.addWidget(qt.wrap_in_groupbox(self.nations_list, 'Nations'), 0, 0)

        # map view (no scroll bars)
        self.map_scene = QtWidgets.QGraphicsScene()
        self.map_view = qt.FitSceneInViewGraphicsView(self.map_scene)
        self.map_view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.map_view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        #self.map_view.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        # self.map_view.setFixedSize(100, 100)
        layout.addWidget(qt.wrap_in_groupbox(self.map_view, 'Map'), 0, 1)

        # scenario description
        self.description = QtWidgets.QPlainTextEdit()
        self.description.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.description.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.description.setReadOnly(True)
        self.description.setPlainText(message[constants.ScenarioProperty.DESCRIPTION])
        height = self.description.fontMetrics().lineSpacing() * 4 # 4 lines high
        self.description.setFixedHeight(height)
        layout.addWidget(qt.wrap_in_groupbox(self.description, 'Description'), 1, 0, 1, 2)  # goes over two columns

        # nation description
        self.nation_info = QtWidgets.QPlainTextEdit()
        self.nation_info.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.nation_info.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.nation_info.setReadOnly(True)
        height = self.nation_info.fontMetrics().lineSpacing() * 6 # 6 lines high
        self.nation_info.setFixedHeight(height)
        layout.addWidget(qt.wrap_in_groupbox(self.nation_info, 'Nation Info'), 2, 0, 1, 2)

        # stretching of the elements
        layout.setRowStretch(0, 1)  # nation list and map get all the available height
        layout.setColumnStretch(1, 1)  # map gets all the available width

        # add the start button
        toolbar = QtWidgets.QToolBar()
        toolbar.addAction(qt.create_action(tools.load_ui_icon('icon.confirm.png'), 'Start selected scenario', toolbar, trigger_connection=self.start_scenario_clicked))
        layout.addWidget(toolbar, 3, 0, 1, 2, alignment=QtCore.Qt.AlignRight)

        # draw the map
        columns = message[constants.ScenarioProperty.MAP_COLUMNS]
        rows = message[constants.ScenarioProperty.MAP_ROWS]
        self.map_scene.setSceneRect(0, 0, columns, rows)

        # fill the ground layer with a neutral color
        item = self.map_scene.addRect(0, 0, columns, rows)
        item.setBrush(QtCore.Qt.lightGray)
        item.setPen(qt.TRANSPARENT_PEN)
        item.setZValue(0)

        # for all nations
        for nation_id, nation in list(message['nations'].items()):

            # get nation color
            color_string = nation[constants.NationProperty.COLOR]
            color = QtGui.QColor()
            color.setNamedColor(color_string)

            # get nation name
            nation_name = nation[constants.NationProperty.NAME]

            # get nation outline
            path = QtGui.QPainterPath()
            # TODO traversing everything is quite slow go only once and add to paths
            for column in range(0, columns):
                for row in range(0, rows):
                    if nation_id == message['map'][column + row * columns]:
                        path.addRect(column, row, 1, 1)
            path = path.simplified()

            item = graphics.MiniMapNationItem(path)
            item.signaller.clicked.connect(
                partial(self.map_selected_nation, utils.index_of_element(nation_names, nation_name)))
            #item.signaller.entered.connect(partial(self.change_map_name, nation_name))
            #item.signaller.left.connect(partial(self.change_map_name, ''))
            brush = QtGui.QBrush(color)
            item.setBrush(brush)

            item.setToolTip(nation_name)

            pen = QtGui.QPen()
            pen.setWidth(2)
            pen.setCosmetic(True)
            item.setPen(pen)

            self.map_scene.addItem(item)
            # item = self.map_scene.addPath(path, brush=brush) # will use the default pen for outline

        self.preview = message

    def change_map_name(self, nation_name, event):
        """
        Display of hoovered nation name.
        """
        # TODO not looking nice so far. Improve, display somewhere else (not in the scene).
        self.map_name_item.setText(nation_name)

    def map_selected_nation(self, nation_row, event):
        """
            Clicked on a nation in the map. Just selects the corresponding row in the nation table.
        """
        self.nations_list.setCurrentRow(nation_row)

    def nations_list_selection_changed(self):
        """
            A nation was selected in the nations table, fill nation description and set it selected.
        """
        row = self.nations_list.currentRow()
        nation_id = self.nation_ids[row]
        # self.selected_nation = self.preview['nations'][nation_id][constants.NationProperty.NAME]
        self.selected_nation = nation_id
        nation_description = self.preview['nations'][nation_id][constants.NationProperty.DESCRIPTION]
        self.nation_info.setPlainText(nation_description)

    def start_scenario_clicked(self):
        """
            Start scenario button is clicked. Only react if a nation is already selected.
        """
        if self.selected_nation is not None:
            self.nation_selected.emit(self.selected_nation)

    def stop(self):
        """
            Interruption. Clean up network channels and the like.
        """
        # TODO is this right? network channel might still be open
        # local_network_client.remove_channel(self.CH_PREVIEW, ignore_not_existing=True)


class SinglePlayerScenarioTitleSelection(QtWidgets.QGroupBox):
    """
    Displays a widget with all available scenario titles for starting new single player scenarios.
    """

    #: signal, emitted if a title is selected.
    title_selected = QtCore.pyqtSignal(str)

    # TODO if the height is higher than the window we may have to enable scroll bars, not now with one scenario though

    def __init__(self):
        """

        """
        super().__init__()
        self.setTitle('Select Scenario')
        self.layout = QtWidgets.QVBoxLayout(self)

        # add a channel for us
        local_network_client.connect_to_channel(constants.C.LOBBY, self.received_titles)

        # send message and ask for scenario titles
        local_network_client.send(constants.C.LOBBY, constants.M.LOBBY_SCENARIO_CORE_LIST)

    def received_titles(self, client, channel, action, content):
        """
            Received all available scenario titles as a list together with the file names
            which act as unique identifiers. The list is sorted by title.
        """

        # immediately close the channel, we do not want to get this content twice
        client.remove_channel(channel)

        # unpack content
        scenario_titles, self.scenario_files = list(zip(*content))

        # create list widget
        self.list = QtWidgets.QListWidget()
        self.list.itemSelectionChanged.connect(self.selection_changed)
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.list.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.list.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.list.addItems(scenario_titles)
        # set height size fixed to content
        self.list.setFixedHeight(self.list.sizeHintForRow(0) * self.list.count() + 2 * self.list.frameWidth())

        self.layout.addWidget(self.list)

    def selection_changed(self):
        """
            A scenario title has been selected in the list.
        """
        # get selected file
        row = self.list.currentRow()  # only useful if QListWidget does not sort by itself
        scenario_file = self.scenario_files[row]
        # emit title selected signal
        self.title_selected.emit(scenario_file)

    def stop(self):
        """
            Interruption. Clean up network channels and the like.
        """
        # network channel might still be open
        local_network_client.remove_channel(self.CH_TITLES, ignore_not_existing=True)
