# Imperialism remake
# Copyright (C) 2014 Trilarion
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
    GUI and internal working of the scenario editor. This is also partly of the client but since the client should not
    know anything about the scenario, we put it in the server module.
"""

import os

from PySide import QtCore, QtGui

import constants as c
import tools as t
import lib.graphics as g
import client.graphics as cg
from server.scenario import Scenario


class EditorMiniMap(QtGui.QWidget):
    """
        Small overview map
    """

    def __init__(self):
        super().__init__()
        self.setObjectName('minimap')

        layout = QtGui.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.scene = QtGui.QGraphicsScene()

        tracker = g.DraggableRectItem()
        tracker.setRect(0,0,100,100)
        tracker.setCursor(QtCore.Qt.PointingHandCursor)
        self.scene.addItem(tracker)

        self.view = QtGui.QGraphicsView(self.scene)
        self.view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        layout.addWidget(self.view)

        size = QtCore.QSize(300, 300)
        self.view.setSceneRect(0, 0, size.width(), size.height())
        self.view.setMinimumSize(size)

        self.toolbar = QtGui.QToolBar()
        self.toolbar.setFloatable(False)
        self.toolbar.setMovable(False)

        action_political = QtGui.QAction(t.load_ui_icon('icon.mini.political.png'), 'Show political view', self)
        self.toolbar.addAction(action_political)

        action_geographical = QtGui.QAction(t.load_ui_icon('icon.mini.geographical.png'), 'Show geographical view', self)
        self.toolbar.addAction(action_geographical)

        layout.addWidget(self.toolbar)

    def new_scenario(self, new_scenario):
        pass


class EditorMainMap(g.ZoomableGraphicsView):
    """
        The big map holding the game map and everything.
    """

    map_position_changed = QtCore.Signal(object)

    def __init__(self):
        super().__init__()

        self.scene = QtGui.QGraphicsScene()
        self.setScene(self.scene)
        self.setObjectName('map')
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setMouseTracking(True)
        self.current_map_position = (-1, -1)
        self.tile_size = 80
        self.scenario = None

    def draw_map(self, new_scenario):
        """
            When a scenario is loaded anew we need to draw the whole map new.
        """
        self.scenario = new_scenario

        self.scene.clear()

        map_size = self.scenario['map-size']

        # todo here should be the real drawing code

        width = (map_size[0] + 0.5) * self.tile_size
        height = map_size[1] * self.tile_size
        self.scene.setSceneRect(0, 0, width, height)

        pixmap = QtGui.QPixmap(c.extend(c.Graphics_Map_Folder, 'texture_ocean.jpg'))
        texture_ocean = QtGui.QBrush(pixmap)

        # fill the ground layer with ocean
        item = self.scene.addRect(0, 0, width, height)
        item.setBrush(texture_ocean)
        item.setZValue(0)

        # draw the grid
        for column in range(0, map_size[0]):
            for row in range(0, map_size[1]):
                x, y = self.scenario.scene_position(column, row)
                item = self.scene.addRect(x * self.tile_size, y * self.tile_size,  self.tile_size,  self.tile_size)
                item.setZValue(1000)

    def mouseMoveEvent(self, event):
        if self.scenario:
            # get mouse position in scene coordinates
            scene_position = self.mapToScene(event.pos()) / self.tile_size
            map_position = self.scenario.map_position(scene_position.x(), scene_position.y())
            if map_position != self.current_map_position:
                self.current_map_position = map_position
                self.map_position_changed.emit(self.current_map_position)
        super().mouseMoveEvent(event)


class InfoBox(QtGui.QLabel):
    """
        Info box on the right side of the editor.
    """

    def __init__(self):
        super().__init__()
        self.setObjectName('infobox')
        self.setText('Info box')

    def new_map_position(self, map_position):
        self.setText('New position {}'.format(map_position))


class NewScenarioDialogWidget(QtGui.QWidget):
    """
        New scenario dialog.
    """
    create_scenario = QtCore.Signal(dict)

    def __init__(self):
        super().__init__()

        self.items = {}

        widget_layout = QtGui.QVBoxLayout(self)

        # title box
        box = QtGui.QGroupBox('Title')
        layout = QtGui.QVBoxLayout(box)
        edit = QtGui.QLineEdit()
        edit.setFixedWidth(300)
        self.items['title'] = edit
        layout.addWidget(edit)
        widget_layout.addWidget(box)

        # map size
        box = QtGui.QGroupBox('Map size')
        layout = QtGui.QHBoxLayout(box)

        layout.addWidget(QtGui.QLabel('Width'))
        edit = QtGui.QLineEdit()
        edit.setFixedWidth(50)
        edit.setPlaceholderText('100')
        edit.setValidator(QtGui.QIntValidator(0, 100))
        self.items['width'] = edit
        layout.addWidget(edit)

        layout.addWidget(QtGui.QLabel('Height'))
        edit = QtGui.QLineEdit()
        edit.setFixedWidth(50)
        edit.setPlaceholderText('100')
        edit.setValidator(QtGui.QIntValidator(0, 100))
        self.items['heigh'] = edit
        layout.addWidget(edit)
        layout.addStretch()

        widget_layout.addWidget(box)

        # vertical stretch
        widget_layout.addStretch()

        # add the button
        layout = QtGui.QHBoxLayout()
        toolbar = QtGui.QToolBar()
        action_create = QtGui.QAction(t.load_ui_icon('icon.confirm.png'), 'Create new scenario', toolbar)
        action_create.triggered.connect(self.create_scenario_clicked)
        toolbar.addAction(action_create)
        layout.addStretch()
        layout.addWidget(toolbar)
        widget_layout.addLayout(layout)

    def create_scenario_clicked(self):
        """
            Callback if indeed yes is clicked.
        """
        self.items['title'] = self.items['title'].text()
        # we close the parent window and emit the appropriate signal
        self.parent().close()
        self.create_scenario.emit(self.items)

class EditorScreen(QtGui.QWidget):
    """
        The screen the contains the whole scenario editor. Is copied into the application main window if the user
        clicks on the editor pixmap in the client main screen.
    """

    def __init__(self, client):
        """
            Create and setup all the elements.
        """
        super().__init__()

        self.client = client
        self.scenario = Scenario()
        self.scenario.Complete_Change.connect(self.scenario_change)

        self.toolbar = QtGui.QToolBar()
        self.toolbar.setFloatable(False)
        self.toolbar.setMovable(False)

        action_new = QtGui.QAction(t.load_ui_icon('icon.scenario.new.png'), 'Create new scenario', self)
        action_new.triggered.connect(self.show_new_scenario_dialog)
        self.toolbar.addAction(action_new)

        action_load = QtGui.QAction(t.load_ui_icon('icon.scenario.load.png'), 'Load scenario', self)
        action_load.triggered.connect(self.load_scenario_dialog)
        self.toolbar.addAction(action_load)

        action_save = QtGui.QAction(t.load_ui_icon('icon.scenario.save.png'), 'Save scenario', self)
        action_save.triggered.connect(self.save_scenario_dialog)
        self.toolbar.addAction(action_save)

        self.toolbar.addSeparator()
        action_nations = QtGui.QAction(t.load_ui_icon('icon.editor.nations.png'), 'Modify Nations', self)
        action_nations.triggered.connect(self.show_nations_dialog)
        self.toolbar.addAction(action_nations)

        spacer = QtGui.QWidget()
        spacer.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.toolbar.addWidget(spacer)

        action_help = QtGui.QAction(t.load_ui_icon('icon.help.png'), 'Show help', self)
        action_help.triggered.connect(client.display_help_browser)  # TODO with partial make reference to specific page
        self.toolbar.addAction(action_help)

        action_quit = QtGui.QAction(t.load_ui_icon('icon.back.startscreen.png'), 'Exit to main menu', self)
        action_quit.triggered.connect(client.switch_to_start_screen)
        # TODO ask if something is changed we should save.. (you might loose progress)
        self.toolbar.addAction(action_quit)

        self.mini_map = EditorMiniMap()

        self.info_box = InfoBox()

        self.map = EditorMainMap()
        self.map.map_position_changed.connect(self.info_box.new_map_position)

        layout = QtGui.QGridLayout(self)
        layout.addWidget(self.toolbar, 0, 0, 1, 2)
        layout.addWidget(self.mini_map, 1, 0)
        layout.addWidget(self.info_box, 2, 0)
        layout.addWidget(self.map, 1, 1, 2, 1)
        layout.setRowStretch(2, 1)  # the info box will take all vertical space left
        layout.setColumnStretch(1, 1)  # the map will take all horizontal space left

    def show_new_scenario_dialog(self):
        """
            Show the dialog for creation of a new scenario dialog.
        """
        new_scenario_widget = NewScenarioDialogWidget()
        dialog = cg.GameDialog(self.client.main_window, new_scenario_widget, title='New Scenario', delete_on_close=True,
                               help_callback=self.client.display_help_browser)
        # TODO close callback
        dialog.setFixedSize(QtCore.QSize(500, 400))
        dialog.show()

    def load_scenario_dialog(self):
        """
            Show the load a scenario dialog. Then loads it if the user has selected one.
        """
        file_name = \
            QtGui.QFileDialog.getOpenFileName(self, 'Load Scenario', c.Scenario_Folder, 'Scenario Files (*.scenario)')[
                0]
        if file_name:
            # TODO what if file name does not exist or is not a valid scenario file
            self.scenario.load(file_name)
            self.client.schedule_notification('Loaded scenario {}'.format(self.scenario['title']))

    def save_scenario_dialog(self):
        """
            Show the save a scenario dialog. Then saves it.
        """
        file_name = \
            QtGui.QFileDialog.getSaveFileName(self, 'Save Scenario', c.Scenario_Folder, 'Scenario Files (*.scenario)')[
                0]
        if file_name:
            self.scenario.save(file_name)
            path, name = os.path.split(file_name)
            self.client.schedule_notification('Saved to {}'.format(name))

    def scenario_change(self):
        """
            Whenever the scenario changes completely (new scenario, scenario loaded, ...)
        """
        self.map.draw_map(self.scenario)

    def show_nations_dialog(self):
        """
            Show the modify nations dialog.
        """
        pass