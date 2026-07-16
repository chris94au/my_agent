from __future__ import annotations

import sys
import types
from pathlib import Path


_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent


def _try_load_real_pyside6():
    candidate_paths = [
        _REPO_ROOT / ".venv" / "lib" / "python3.12" / "site-packages",
        _REPO_ROOT / ".venv" / "lib" / "python3.11" / "site-packages",
        _REPO_ROOT / ".venv" / "lib" / "python3.10" / "site-packages",
    ]
    original_sys_path = list(sys.path)
    original_module = sys.modules.get(__name__)
    try:
        for candidate in candidate_paths:
            if candidate.exists() and str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
        import importlib.machinery
        import importlib.util

        search_paths = [path for path in sys.path if path]
        spec = importlib.machinery.PathFinder.find_spec(__name__, search_paths)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[__name__] = module
            spec.loader.exec_module(module)
            try:
                import PySide6.QtCore  # noqa: F401
                import PySide6.QtGui  # noqa: F401
                import PySide6.QtWidgets  # noqa: F401
            except Exception:
                raise ImportError("PySide6 runtime dependencies are unavailable")
            globals().update(module.__dict__)
            return True
    except Exception:
        if original_module is not None:
            sys.modules[__name__] = original_module
        else:
            sys.modules.pop(__name__, None)
    finally:
        sys.path[:] = original_sys_path
    return False


if not _try_load_real_pyside6():
    import weakref

    class _BoundSignal:
        def __init__(self):
            self._callbacks = []

        def connect(self, callback):
            self._callbacks.append(callback)

        def emit(self, *args, **kwargs):
            for callback in list(self._callbacks):
                callback(*args, **kwargs)


    class Signal:
        def __init__(self, *args, **kwargs):
            self._args = args
            self._kwargs = kwargs

        def __set_name__(self, owner, name):
            self._name = name
            self._signals = weakref.WeakKeyDictionary()

        def __get__(self, instance, owner):
            if instance is None:
                return self
            signal = self._signals.get(instance)
            if signal is None:
                signal = _BoundSignal()
                self._signals[instance] = signal
            return signal


    class QObject:
        def __init__(self, parent=None):
            self._parent = parent


    class Qt:
        LeftDockWidgetArea = 1
        RightDockWidgetArea = 2
        TopDockWidgetArea = 4
        BottomDockWidgetArea = 8
        Vertical = 1
        Horizontal = 2
        Key_Return = 16777220
        Key_Enter = 16777221
        ControlModifier = 0x01000000
        DockWidgetMovable = 1
        DockWidgetFloatable = 2
        DockWidgetClosable = 4


    class QEvent:
        KeyPress = 6


    class QTimer:
        @staticmethod
        def singleShot(_msec, callback):
            callback()


    class QFont:
        Monospace = 1

        def __init__(self, family=""):
            self.family = family
            self._style_hint = None

        def setStyleHint(self, hint):
            self._style_hint = hint


    class QKeySequence:
        def __init__(self, sequence=""):
            self.sequence = sequence


    class _Clipboard:
        def __init__(self):
            self._text = ""

        def setText(self, text):
            self._text = str(text)

        def text(self):
            return self._text


    class QApplication(QObject):
        _instance = None

        def __init__(self, argv=None):
            super().__init__()
            QApplication._instance = self
            self.argv = argv or []
            self._clipboard = _Clipboard()
            self._application_name = ""
            self._organization_name = ""
            self._organization_domain = ""

        @classmethod
        def instance(cls):
            return cls._instance

        def exec(self):
            return 0

        def clipboard(self):
            return self._clipboard

        def setApplicationName(self, name):
            self._application_name = name

        def setOrganizationName(self, name):
            self._organization_name = name

        def setOrganizationDomain(self, domain):
            self._organization_domain = domain


    class QWidget(QObject):
        def __init__(self, parent=None):
            super().__init__(parent)
            self._layout = None
            self._visible = False
            self._object_name = ""
            self._children = []
            self._title = ""
            self._stylesheet = ""
            self._minimum_height = 0
            self._word_wrap = False

        def setLayout(self, layout):
            self._layout = layout

        def layout(self):
            return self._layout

        def setObjectName(self, name):
            self._object_name = name

        def objectName(self):
            return self._object_name

        def show(self):
            self._visible = True

        def hide(self):
            self._visible = False

        def isVisible(self):
            return self._visible

        def setWindowTitle(self, title):
            self._title = title

        def setStyleSheet(self, stylesheet):
            self._stylesheet = stylesheet

        def setMinimumHeight(self, value):
            self._minimum_height = value

        def setWordWrap(self, enabled):
            self._word_wrap = bool(enabled)

        def installEventFilter(self, _filter):
            self._event_filter = _filter

        def window(self):
            return self


    class _Layout:
        def __init__(self, parent=None):
            self.parent = parent
            self.items = []

        def addWidget(self, widget, *args):
            self.items.append(widget)

        def addLayout(self, layout, *args):
            self.items.append(layout)

        def addRow(self, *args):
            self.items.append(args)

        def addStretch(self, *args):
            self.items.append(("stretch", args))

        def setContentsMargins(self, *args):
            self.margins = args


    class QVBoxLayout(_Layout):
        pass


    class QHBoxLayout(_Layout):
        pass


    class QFormLayout(_Layout):
        pass


    class QGroupBox(QWidget):
        def __init__(self, title="", parent=None):
            super().__init__(parent)
            self.title = title


    class QLabel(QWidget):
        def __init__(self, text="", parent=None):
            super().__init__(parent)
            self._text = text

        def setText(self, text):
            self._text = str(text)

        def text(self):
            return self._text

        def setPlaceholderText(self, _text):
            pass


    class QLineEdit(QWidget):
        returnPressed = Signal()

        def __init__(self, parent=None):
            super().__init__(parent)
            self._text = ""
            self._placeholder = ""
            self._editable = True

        def setText(self, text):
            self._text = str(text)

        def text(self):
            return self._text

        def clear(self):
            self._text = ""

        def setPlaceholderText(self, text):
            self._placeholder = str(text)

        def setEditable(self, enabled):
            self._editable = bool(enabled)

        def lineEdit(self):
            return self


    class QPlainTextEdit(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self._text = ""
            self._placeholder = ""
            self._read_only = False
            self._tab_focus = False
            self._font = None

        def setPlainText(self, text):
            self._text = str(text)

        def toPlainText(self):
            return self._text

        def clear(self):
            self._text = ""

        def appendPlainText(self, text):
            self._text += ("\n" if self._text else "") + str(text)

        def setPlaceholderText(self, text):
            self._placeholder = str(text)

        def setReadOnly(self, value):
            self._read_only = bool(value)

        def setTabChangesFocus(self, value):
            self._tab_focus = bool(value)

        def setFont(self, font):
            self._font = font


    class QTextBrowser(QPlainTextEdit):
        def setMarkdown(self, text):
            self.setPlainText(text)

        def setOpenExternalLinks(self, _value):
            pass


    class QPushButton(QWidget):
        clicked = Signal()

        def __init__(self, text="", parent=None):
            super().__init__(parent)
            self._text = text
            self._enabled = True

        def setText(self, text):
            self._text = str(text)

        def text(self):
            return self._text

        def click(self):
            self.clicked.emit()

        def setEnabled(self, value):
            self._enabled = bool(value)

        def isEnabled(self):
            return self._enabled


    class QCheckBox(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self._checked = False

        def setChecked(self, value):
            self._checked = bool(value)

        def isChecked(self):
            return self._checked


    class QSpinBox(QWidget):
        valueChanged = Signal()

        def __init__(self, parent=None):
            super().__init__(parent)
            self._value = 0
            self._minimum = 0
            self._maximum = 100
            self._suffix = ""

        def setRange(self, minimum, maximum):
            self._minimum = minimum
            self._maximum = maximum

        def setValue(self, value):
            self._value = int(value)
            self.valueChanged.emit(self._value)

        def value(self):
            return self._value

        def setSuffix(self, suffix):
            self._suffix = str(suffix)


    class QDoubleSpinBox(QSpinBox):
        def setSingleStep(self, value):
            self._single_step = value

        def setValue(self, value):
            self._value = float(value)
            self.valueChanged.emit(self._value)

        def value(self):
            return float(self._value)


    class QComboBox(QWidget):
        currentIndexChanged = Signal()

        def __init__(self, parent=None):
            super().__init__(parent)
            self._items = []
            self._current_index = -1
            self._editable = False
            self._line_edit = QLineEdit(self)

        def addItem(self, text, user_data=None):
            self._items.append((text, user_data))
            if self._current_index == -1:
                self._current_index = 0

        def addItems(self, items):
            for item in items:
                self.addItem(item)

        def currentText(self):
            if 0 <= self._current_index < len(self._items):
                return self._items[self._current_index][0]
            return ""

        def currentData(self):
            if 0 <= self._current_index < len(self._items):
                return self._items[self._current_index][1]
            return None

        def setCurrentIndex(self, index):
            self._current_index = int(index)
            self.currentIndexChanged.emit(self._current_index)

        def count(self):
            return len(self._items)

        def setEditable(self, value):
            self._editable = bool(value)

        def lineEdit(self):
            return self._line_edit


    class QAction(QObject):
        triggered = Signal()

        def __init__(self, text="", parent=None):
            super().__init__(parent)
            self._text = text
            self._checked = False

        def text(self):
            return self._text

        def trigger(self):
            self.triggered.emit()

        def setChecked(self, value):
            self._checked = bool(value)

        def isChecked(self):
            return self._checked


    class QMenu(QWidget):
        def __init__(self, title="", parent=None):
            super().__init__(parent)
            self.title = title
            self.actions = []

        def addAction(self, action):
            if isinstance(action, str):
                action = QAction(action, self)
            self.actions.append(action)
            return action


    class QMenuBar(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.menus = []

        def addMenu(self, title):
            menu = QMenu(title, self)
            self.menus.append(menu)
            return menu


    class QStatusBar(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.message = ""

        def showMessage(self, message):
            self.message = str(message)


    class QToolBar(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.actions = []
            self._movable = True

        def setMovable(self, value):
            self._movable = bool(value)

        def addAction(self, action):
            if isinstance(action, str):
                action = QAction(action, self)
            self.actions.append(action)
            return action


    class QListWidgetItem:
        def __init__(self, text=""):
            self._text = str(text)

        def text(self):
            return self._text

        def setText(self, text):
            self._text = str(text)


    class QListWidget(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self._items = []

        def clear(self):
            self._items = []

        def addItem(self, item):
            if isinstance(item, str):
                item = QListWidgetItem(item)
            self._items.append(item)

        def count(self):
            return len(self._items)


    class QTabWidget(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.tabs = []

        def addTab(self, widget, title):
            self.tabs.append((widget, title))
            return len(self.tabs) - 1


    class QSplitter(QWidget):
        def __init__(self, orientation, parent=None):
            super().__init__(parent)
            self.orientation = orientation
            self.widgets = []

        def addWidget(self, widget):
            self.widgets.append(widget)

        def setStretchFactor(self, *_args):
            pass


    class QTableWidgetItem:
        def __init__(self, text=""):
            self._text = str(text)
            self._tooltip = ""

        def text(self):
            return self._text

        def setToolTip(self, tooltip):
            self._tooltip = str(tooltip)

        def toolTip(self):
            return self._tooltip


    class QTableWidget(QWidget):
        itemSelectionChanged = Signal()

        def __init__(self, parent=None):
            super().__init__(parent)
            self._columns = 0
            self._rows = []
            self._headers = []
            self._current_row = -1

        def setColumnCount(self, count):
            self._columns = int(count)

        def setHorizontalHeaderLabels(self, labels):
            self._headers = list(labels)

        def setRowCount(self, count):
            self._rows = [[None for _ in range(self._columns)] for _ in range(int(count))]

        def rowCount(self):
            return len(self._rows)

        def columnCount(self):
            return self._columns

        def setItem(self, row, column, item):
            while row >= len(self._rows):
                self._rows.append([None for _ in range(self._columns)])
            self._rows[row][column] = item

        def item(self, row, column):
            try:
                return self._rows[row][column]
            except Exception:
                return None

        def currentRow(self):
            return self._current_row

        def selectRow(self, row):
            self._current_row = row
            self.itemSelectionChanged.emit()


    class QDockWidget(QWidget):
        DockWidgetMovable = 1
        DockWidgetFloatable = 2
        DockWidgetClosable = 4

        def __init__(self, title="", parent=None):
            super().__init__(parent)
            self._title = title
            self._widget = None
            self._features = 0
            self._visible = True
            self._toggle_action = QAction(title, self)

        def setWidget(self, widget):
            self._widget = widget

        def widget(self):
            return self._widget

        def setFeatures(self, features):
            self._features = features

        def toggleViewAction(self):
            return self._toggle_action

        def setObjectName(self, name):
            self._object_name = name


    class QFileDialog:
        @staticmethod
        def getOpenFileName(*args, **kwargs):
            return "", ""

        @staticmethod
        def getSaveFileName(*args, **kwargs):
            return "", ""


    class QMessageBox:
        @staticmethod
        def information(*args, **kwargs):
            return None


    class QMainWindow(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self._central_widget = None
            self._docks = []
            self._menu_bar = QMenuBar(self)
            self._status_bar = QStatusBar(self)

        def setCentralWidget(self, widget):
            self._central_widget = widget

        def centralWidget(self):
            return self._central_widget

        def addDockWidget(self, area, dock):
            self._docks.append((area, dock))

        def menuBar(self):
            return self._menu_bar

        def statusBar(self):
            return self._status_bar

        def resize(self, *_args):
            pass

        def setWindowTitle(self, title):
            self._title = title

        def show(self):
            self._visible = True


    qtcore = types.ModuleType("PySide6.QtCore")
    qtcore.QObject = QObject
    qtcore.Signal = Signal
    qtcore.Qt = Qt
    qtcore.QEvent = QEvent
    qtcore.QTimer = QTimer

    qtgui = types.ModuleType("PySide6.QtGui")
    qtgui.QAction = QAction
    qtgui.QFont = QFont
    qtgui.QKeySequence = QKeySequence

    qtwidgets = types.ModuleType("PySide6.QtWidgets")
    qtwidgets.QApplication = QApplication
    qtwidgets.QWidget = QWidget
    qtwidgets.QMainWindow = QMainWindow
    qtwidgets.QDockWidget = QDockWidget
    qtwidgets.QMenu = QMenu
    qtwidgets.QMenuBar = QMenuBar
    qtwidgets.QStatusBar = QStatusBar
    qtwidgets.QToolBar = QToolBar
    qtwidgets.QHBoxLayout = QHBoxLayout
    qtwidgets.QVBoxLayout = QVBoxLayout
    qtwidgets.QFormLayout = QFormLayout
    qtwidgets.QGroupBox = QGroupBox
    qtwidgets.QLabel = QLabel
    qtwidgets.QLineEdit = QLineEdit
    qtwidgets.QPlainTextEdit = QPlainTextEdit
    qtwidgets.QTextBrowser = QTextBrowser
    qtwidgets.QPushButton = QPushButton
    qtwidgets.QCheckBox = QCheckBox
    qtwidgets.QSpinBox = QSpinBox
    qtwidgets.QDoubleSpinBox = QDoubleSpinBox
    qtwidgets.QComboBox = QComboBox
    qtwidgets.QListWidget = QListWidget
    qtwidgets.QListWidgetItem = QListWidgetItem
    qtwidgets.QTabWidget = QTabWidget
    qtwidgets.QSplitter = QSplitter
    qtwidgets.QTableWidget = QTableWidget
    qtwidgets.QTableWidgetItem = QTableWidgetItem
    qtwidgets.QFileDialog = QFileDialog
    qtwidgets.QMessageBox = QMessageBox

    sys.modules["PySide6.QtCore"] = qtcore
    sys.modules["PySide6.QtGui"] = qtgui
    sys.modules["PySide6.QtWidgets"] = qtwidgets

    __all__ = [
        "QObject",
        "Signal",
        "Qt",
        "QEvent",
        "QTimer",
        "QApplication",
        "QWidget",
        "QMainWindow",
        "QDockWidget",
        "QMenu",
        "QMenuBar",
        "QStatusBar",
        "QToolBar",
        "QHBoxLayout",
        "QVBoxLayout",
        "QFormLayout",
        "QGroupBox",
        "QLabel",
        "QLineEdit",
        "QPlainTextEdit",
        "QTextBrowser",
        "QPushButton",
        "QCheckBox",
        "QSpinBox",
        "QDoubleSpinBox",
        "QComboBox",
        "QListWidget",
        "QListWidgetItem",
        "QTabWidget",
        "QSplitter",
        "QTableWidget",
        "QTableWidgetItem",
        "QFileDialog",
        "QMessageBox",
        "QAction",
        "QFont",
        "QKeySequence",
    ]
