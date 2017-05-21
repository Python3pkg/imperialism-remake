# Imperialism remake
# Copyright (C) 2014-16 Trilarion
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
Starts the client and delivers most of the code responsible for the main client screen and the diverse dialogs.
"""

# TODO automatic placement of help dialog depending on if another dialog is open

from functools import partial
from PyQt5 import QtCore, QtGui, QtWidgets

from imperialism_remake.base import constants, tools
import imperialism_remake.base.network as base_network
from imperialism_remake.client import audio
import imperialism_remake.client.graphics as graphics
from imperialism_remake.lib import qt, utils
import imperialism_remake.version as version

# TODO like in audio, set the network client singleton somewhere else
local_network_client = base_network.NetworkClient()

from imperialism_remake.client.editor import EditorScreen
from imperialism_remake.client.lobby import GameLobbyWidget
from imperialism_remake.client.game import GameMainScreen
from imperialism_remake.client.preferences import PreferencesWidget
from imperialism_remake.client.server_monitor import ServerMonitorWidget


class MapItem(QtCore.QObject):
    """
        Holds together a clickable QPixmapItem, a description text and a reference to a label that shows the text

        TODO use signals to show the text instead
    """
    description_change = QtCore.pyqtSignal(str)

    def __init__(self, parent, pixmap, label, description):
        super().__init__(parent)
        # store label and description
        self.label = label
        self.description = description

        # create clickable pixmap item and create fade animation
        self.item = qt.ClickablePixmapItem(pixmap)
        self.fade = qt.FadeAnimation(self.item)
        self.fade.set_duration(300)

        # wire to fade in/out
        self.item.signaller.entered.connect(self.fade.fadein)
        self.item.signaller.left.connect(self.fade.fadeout)

        # wire to show/hide description
        self.item.signaller.entered.connect(self.show_description)
        self.item.signaller.left.connect(self.hide_description)

    def show_description(self):
        """
            Shows the description in the label.
        """
        self.label.setText('<font color=#ffffff size=6>{}</font>'.format(self.description))

    def hide_description(self):
        """
            Hides the description from the label.
        """
        self.label.setText('')


class StartScreen(QtWidgets.QWidget):
    """
        Creates the start screen

        TODO convert to simple method which does it, no need to be a class
    """

    frame_pen = QtGui.QPen(QtGui.QBrush(QtGui.QColor(255, 255, 255, 64)), 6)

    def __init__(self, client):
        super().__init__()

        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.setProperty('background', 'black')

        layout = qt.RelativeLayout(self)

        start_image = QtGui.QPixmap(constants.extend(constants.GRAPHICS_UI_FOLDER, 'start.background.jpg'))
        start_image_item = QtWidgets.QGraphicsPixmapItem(start_image)
        start_image_item.setZValue(1)

        scene = QtWidgets.QGraphicsScene(self)
        scene.addItem(start_image_item)

        view = QtWidgets.QGraphicsView(scene)
        view.resize(start_image.size())
        view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        view.setSceneRect(0, 0, start_image.width(), start_image.height())
        view.layout_constraint = qt.RelativeLayoutConstraint().center_horizontal().center_vertical()
        layout.addWidget(view)

        subtitle = QtWidgets.QLabel('')
        subtitle.layout_constraint = qt.RelativeLayoutConstraint((0.5, -0.5, 0),
            (0.5, -0.5, start_image.height() / 2 + 20))
        layout.addWidget(subtitle)

        actions = {'exit': client.quit, 'help': client.show_help_browser, 'lobby': client.show_game_lobby_dialog,
                   'editor': client.switch_to_editor_screen, 'options': client.show_preferences_dialog}

        image_map_file = constants.extend(constants.GRAPHICS_UI_FOLDER, 'start.overlay.info')
        image_map = utils.read_as_yaml(image_map_file)

        # security check, they have to be the same
        if list(actions.keys()) != list(image_map.keys()):
            raise RuntimeError('Start screen hot map info file ({}) corrupt.'.format(image_map_file))

        for k, v in list(image_map.items()):
            # add action from our predefined action dictionary
            pixmap = QtGui.QPixmap(constants.extend(constants.GRAPHICS_UI_FOLDER, v['overlay']))
            map_item = MapItem(view, pixmap, label=subtitle, description=v['label'])
            map_item.item.setZValue(3)
            offset = v['offset']
            map_item.item.setOffset(QtCore.QPointF(offset[0], offset[1]))
            map_item.item.signaller.clicked.connect(actions[k])

            frame_path = QtGui.QPainterPath()
            frame_path.addRect(map_item.item.boundingRect())
            frame_item = scene.addPath(frame_path, StartScreen.frame_pen)
            frame_item.setZValue(4)
            scene.addItem(map_item.item)

        version_label = QtWidgets.QLabel('<font color=#ffffff>{}</font>'.format(version.__version_full__))
        version_label.layout_constraint = qt.RelativeLayoutConstraint().east(20).south(20)
        layout.addWidget(version_label)


class ClientMainWindowWidget(QtWidgets.QWidget):
    """
        The main window (widget) which is the top level window of the application. It can be full screen or not and hold
        a single widget in a margin-less layout.
    """
    # TODO should we make this as small as possible, used only once put in Client

    def __init__(self, *args, **kwargs):
        """
        All the necessary initializations. Is shown at the end.
        """
        super().__init__(*args, **kwargs)
        # set geometry
        self.setGeometry(tools.get_option(constants.Option.MAINWINDOW_BOUNDS))
        # set icon
        self.setWindowIcon(tools.load_ui_icon('window.icon.ico'))
        # set title
        self.setWindowTitle('Imperialism Remake')

        # just a layout but nothing else
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.content = None

        # show in full screen, maximized or normal
        if tools.get_option(constants.Option.MAINWINDOW_FULLSCREEN):
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)
            self.showFullScreen()
        elif tools.get_option(constants.Option.MAINWINDOW_MAXIMIZED):
            self.showMaximized()
        else:
            self.show()

        # loading animation
        # TODO animation right and start, stop in client
        self.animation = QtGui.QMovie(constants.extend(constants.GRAPHICS_UI_FOLDER, 'loading.gif'))
        # self.animation.start()
        self.loading_label = QtWidgets.QLabel(self, flags=QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        self.loading_label.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.loading_label.setMovie(self.animation)
        # self.loading_label.show()

    def change_content_widget(self, widget):
        """
        Another screen shall be displayed. Exchange the content widget with a new one.
        """
        if self.content:
            self.layout.removeWidget(self.content)
            self.content.deleteLater()
        self.content = widget
        self.layout.addWidget(widget)


class Client:
    """
        Main class of the client, holds the help browser, the main window (full screen or not), the content of the main
        window, the audio player
    """

    def __init__(self):
        """
            Create the main window, the help browser dialog, the audio player, ...
        """
        # main window
        self.main_window = ClientMainWindowWidget()

        # help browser
        # TODO help browser only if
        # self.help_browser_widget = qt.BrowserWidget(tools.load_ui_icon)
        # self.help_browser_widget = qt.BrowserWidget(tools.load_ui_icon)
        # self.help_browser_widget.home_url = tools.local_url(constants.DOCUMENTATION_INDEX_FILE)
        # self.help_browser_widget.home()
        # self.help_dialog = graphics.GameDialog(self.main_window, self.help_browser_widget, title='Help')
        # self.help_dialog.setFixedSize(QtCore.QSize(800, 600))
        # move to lower right border, so that overlap with other windows is not that strong
        # self.help_dialog.move(self.main_window.x() + self.main_window.width() - 800,
        #                      self.main_window.y() + self.main_window.height() - 600)

        # add help browser keyboard shortcut
        action = QtWidgets.QAction(self.main_window)
        action.setShortcut(QtGui.QKeySequence('F1'))
        action.triggered.connect(self.show_help_browser)
        self.main_window.addAction(action)

        # add server monitor keyboard shortcut
        action = QtWidgets.QAction(self.main_window)
        action.setShortcut(QtGui.QKeySequence('F2'))
        action.triggered.connect(self.show_server_monitor)
        self.main_window.addAction(action)

        # for the notifications
        self.pending_notifications = []
        self.notification_position_constraint = qt.RelativeLayoutConstraint().center_horizontal().south(20)
        self.notification = None

        # after the player starts, the main window is not active anymore
        # set it active again or it doesn't get keyboard focus
        self.main_window.activateWindow()

    def schedule_notification(self, text):
        """
            Generic scheduling of a notification. Will be shown immediately if no other notification is shown, otherwise
            it will be shown as soon at the of the current list of notifications to be shown.
        """
        self.pending_notifications.append(text)
        if self.notification is None:
            self.show_next_notification()

    def show_next_notification(self):
        """
            Will be called whenever a notification is shown and was cleared. Tries to show the next one if there is one.
        """
        if len(self.pending_notifications) > 0:
            message = self.pending_notifications.pop(0)
            self.notification = qt.Notification(self.main_window, message,
                position_constraint=self.notification_position_constraint)
            self.notification.finished.connect(self.show_next_notification)
            self.notification.show()
        else:
            self.notification = None

    def show_help_browser(self, path=None):
        """
            Displays the help browser somewhere on screen. Can set a special page if needed.
        """
        # we sometimes wire signals that send parameters for url (mouse events for example) which we do not like
        if isinstance(path, str):
            url = qt.local_url(path)
            # self.help_browser_widget.load(url)
            QtGui.QDesktopServices.openUrl(url)
        else:
            QtGui.QDesktopServices.openUrl(qt.local_url(constants.DOCUMENTATION_INDEX_FILE))
            # TODO use QtWebEngine instead
            # self.help_dialog.show()

    def show_server_monitor(self):
        """
            Displays the server monitor as a modal window.

            TODO Do we want that non-modal?

            Is invoked when pressing F2.
        """
        monitor_widget = ServerMonitorWidget()
        dialog = graphics.GameDialog(self.main_window, monitor_widget, modal=False, delete_on_close=True, title='Server Monitor', help_callback=self.show_help_browser)
        dialog.setFixedSize(QtCore.QSize(900, 700))
        dialog.show()

    def switch_to_start_screen(self):
        """
            Switches the content of the main window to the start screen.
        """
        widget = StartScreen(self)
        self.main_window.change_content_widget(widget)

    def show_game_lobby_dialog(self):
        """
            Shows the game lobby dialog.
        """
        lobby_widget = GameLobbyWidget()
        dialog = graphics.GameDialog(self.main_window, lobby_widget, delete_on_close=True, title='Game Lobby', help_callback=self.show_help_browser)
        dialog.setFixedSize(QtCore.QSize(900, 700))
        lobby_widget.single_player_start.connect(self.single_player_start)
        dialog.show()

    def single_player_start(self, scenario_file, selected_nation):
        """
            Shows the main game screen which will start a scenario file and a selected nation.
        """
        #lobby_dialog.close()
        widget = GameMainScreen(self)
        self.main_window.change_content_widget(widget)

    def switch_to_editor_screen(self):
        """
            Switches the content of the main window to the editor screen.
        """
        widget = EditorScreen(self)
        self.main_window.change_content_widget(widget)

    def show_preferences_dialog(self):
        """
            Shows the preferences dialog.
        """
        preferences_widget = PreferencesWidget()
        dialog = graphics.GameDialog(self.main_window, preferences_widget, delete_on_close=True, title='Preferences',
            help_callback=partial(self.show_help_browser, path=constants.DOCUMENTATION_PREFERENCES_FILE),
            close_callback=preferences_widget.close_request)
        dialog.setFixedSize(QtCore.QSize(900, 700))
        dialog.show()

    def quit(self):
        """
            Cleans up and closes the main window which causes app.exec_() to finish.
        """
        # store state in options
        tools.set_option(constants.Option.MAINWINDOW_BOUNDS, self.main_window.normalGeometry())
        tools.set_option(constants.Option.MAINWINDOW_MAXIMIZED, self.main_window.isMaximized())

        # audio
        audio.soundtrack_player.stop()

        # stop the local server
        local_network_client.send(constants.C.SYSTEM, constants.M.SYSTEM_SHUTDOWN)
        # TODO is this okay, is there a better way
        local_network_client.socket.flush()

        # close the main window
        self.main_window.close()


def local_network_connect():
    """
        Connect to a server running locally.
    """

    # connect network client of client
    print('client tries to connect to server')
    local_network_client.connect_to_host(constants.NETWORK_PORT)
    # TODO what if this is not possible

    # tell name
    local_network_client.send(constants.C.GENERAL, constants.M.GENERAL_NAME, tools.get_option(constants.Option.LOCALCLIENT_NAME))


def start_client():
    """
        Creates the Qt application and shows the main window.
    """

    # create app
    app = QtWidgets.QApplication([])

    # TODO multiple screen support?

    # test for desktop availability
    desktop = app.desktop()
    rect = desktop.screenGeometry()
    if rect.width() < constants.MINIMAL_SCREEN_SIZE[0] or rect.height() < constants.MINIMAL_SCREEN_SIZE[1]:
        # noinspection PyTypeChecker
        QtWidgets.QMessageBox.warning(None, 'Warning',
            'Actual screen size below minimal screen size {}.'.format(constants.MINIMAL_SCREEN_SIZE))
        return

    # if no bounds are set, set reasonable bounds
    if tools.get_option(constants.Option.MAINWINDOW_BOUNDS) is None:
        tools.set_option(constants.Option.MAINWINDOW_BOUNDS, desktop.availableGeometry().adjusted(50, 50, -100, -100))
        tools.set_option(constants.Option.MAINWINDOW_MAXIMIZED, True)
        tools.log_info('No previous bounds of the main window stored, start maximized')

    # load global stylesheet to app
    with open(constants.GLOBAL_STYLESHEET_FILE, encoding='utf-8') as file:  # open is 'r' by default
        style_sheet = file.read()
    app.setStyleSheet(style_sheet)

    # setup sound system
    audio.load_soundtrack_playlist()
    audio.setup_soundtrack_player()

    # start audio player if wished
    if not tools.get_option(constants.Option.SOUNDTRACK_MUTE):
        audio.soundtrack_player.play()
    pass

    # create client object and switch to start screen
    client = Client()
    client.switch_to_start_screen()

    tools.log_info('client initialized, start Qt app execution')
    # TODO is this necessary to run as event?
    # noinspection PyCallByClass
    QtCore.QTimer.singleShot(0, local_network_connect)
    app.exec_()
