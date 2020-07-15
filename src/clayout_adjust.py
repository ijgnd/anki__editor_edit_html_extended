import io
import os
import pathlib
import subprocess
from tempfile import NamedTemporaryFile

from anki.hooks import wrap

from aqt import mw
from aqt.clayout import CardLayout
from aqt.qt import (
    QCursor,
    Qt,
)
from aqt.utils import (
    openFolder,
    tooltip,
)

from .config import addon_path, gc, pointversion, unique_string
from .dialog_cm import CmDialog
from .dialog_old_versions import OldVersions
from .helpers import now, readfile


def template_save_path(self, boxname):
    base = os.path.join(addon_path, "user_files")
    if gc("backup_template_path"):
        user = gc("backup_template_path")
        if os.path.isdir(base):
            base = user
        else:
            tooltip('Invalid setting for "backup_template_path". This is not a directory. '
                    'Using default path in add-on folder')
    # don't use model['name'] in case a user renames a template ...
    return os.path.join(base, str(self.model['id']), boxname)
CardLayout.template_save_path = template_save_path


def save_clear_editExternal(self, box, tedit):
    self.onTemplateSave(box, tedit)
    content = tedit.toPlainText()
    tedit.setPlainText("")
    if box == "css":
        ext = ".css"
    else:
        ext = ".html"
    suf = "current" + ext
    cur = NamedTemporaryFile(delete=False, suffix=suf)
    cur.write(str.encode(content))
    cur.close()
    cmd = gc("diffcommandstart")
    try:
        subprocess.Popen([cmd[0], cur.name])
    except:
        tooltip("Error while trying to open the external editor. Maybe there's an error in your config.")
        tedit.setPlainText(content)
CardLayout.save_clear_editExternal = save_clear_editExternal


def extra_dialog(self, box, tedit):
    p = self.template_save_path(box)
    if not os.path.isdir(p):
        tooltip("no prior versions found.")
        return
    d = OldVersions(self, self.note, box, p, tedit.toPlainText())
    d.exec()
CardLayout.extra_dialog = extra_dialog


def show_in_filemanager(self, box, tedit):
    p = self.template_save_path(box)
    if os.path.isdir(p):
        openFolder(p)
    else:
        tooltip("folder not found. Maybe no version was saved yet ...")
CardLayout.show_in_filemanager = show_in_filemanager


def saveStringForBox(self, boxname, content):
    if boxname == "css":
        ext = ".css"
    else:
        ext = ".html"
    folder = self.template_save_path(boxname)
    filename = now() + ext
    pathlib.Path(folder).mkdir(parents=True, exist_ok=True)
    p = os.path.join(folder, filename)
    with io.open(p, "w", encoding="utf-8") as f:
        f.write(content)
        tooltip('saved as {}'.format(filename))
CardLayout.saveStringForBox = saveStringForBox


def onTemplateSave(self, boxname, tedit):
    content = tedit.toPlainText()
    self.saveStringForBox(boxname, content)
CardLayout.onTemplateSave = onTemplateSave


def on_CMdialog_finished(self, status):
    if status:
        # unique string is used so that I find the cursor position in CM. Useless here.
        self.textedit_in_cm.setPlainText(mw.col.cmhelper_field_content.replace(unique_string, ""))  
CardLayout.on_CMdialog_finished = on_CMdialog_finished


def on_external_edit(self, boxname, textedit):
    self.textedit_in_cm = textedit
    content = textedit.toPlainText()
    win_title = 'Anki - edit html source code for field in codemirror'
    mode = "css" if boxname == "css" else "htmlmixed"
    d = CmDialog(self, content, mode, win_title, False, boxname, self.note)
    # exec_() doesn't work - jseditor isn't loaded = blocked
    # finished.connect via https://stackoverflow.com/questions/39638749/
    d.finished.connect(self.on_CMdialog_finished)
    d.setModal(True)
    d.show()
    d.web.setFocus()
CardLayout.on_external_edit = on_external_edit












if pointversion < 27:
    def common_context_menu(self, tedit, boxname):
        menu = tedit.createStandardContextMenu()
        sla = menu.addAction("edit in extra window with html/css editor")
        sla.triggered.connect(lambda _, s=self: on_external_edit(s, boxname, tedit))
        sav = menu.addAction("save")
        sav.triggered.connect(lambda _, s=self: onTemplateSave(s, boxname, tedit))
        a = menu.addAction("prior versions extra dialog")
        a.triggered.connect(lambda _, s=self: extra_dialog(s, boxname, tedit))
        b = menu.addAction("prior versions in file manager")
        b.triggered.connect(lambda _, s=self: show_in_filemanager(s, boxname, tedit))
        c = menu.addAction("save, edit external and clear")
        c.triggered.connect(lambda _, s=self: save_clear_editExternal(s, boxname, tedit))
        return menu
    CardLayout.common_context_menu = common_context_menu


    def make_context_menu_front(self, location):
        menu = self.common_context_menu(self.tform.front, "front")
        menu.exec_(QCursor.pos())
    CardLayout.make_context_menu_front = make_context_menu_front


    def make_context_menu_css(self, location):
        menu = self.common_context_menu(self.tform.css, "css")
        menu.exec_(QCursor.pos())
    CardLayout.make_context_menu_css = make_context_menu_css


    def make_context_menu_back(self, location):
        menu = self.common_context_menu(self.tform.back, "back")
        menu.exec_(QCursor.pos())
    CardLayout.make_context_menu_back = make_context_menu_back


    def additional_clayout_setup(self):
        # https://stackoverflow.com/a/44770024
        self.tform.front.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tform.front.customContextMenuRequested.connect(self.make_context_menu_front)
        self.tform.css.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tform.css.customContextMenuRequested.connect(self.make_context_menu_css)
        self.tform.back.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tform.back.customContextMenuRequested.connect(self.make_context_menu_back)
    CardLayout.setupMainArea = wrap(CardLayout.setupMainArea, additional_clayout_setup)









if pointversion >= 28:
    def make_new_context_menu(self, location):
        if self.tform.front_button.isChecked():
            boxname = "front"
        elif self.tform.back_button.isChecked():
            boxname = "back"
        else:
            boxname = "css"
        tedit = self.tform.edit_area
        menu = tedit.createStandardContextMenu()
        sla = menu.addAction("edit in extra window with html/css editor")
        sla.triggered.connect(lambda _, s=self: on_external_edit(s, boxname, tedit))
        sav = menu.addAction("save")
        sav.triggered.connect(lambda _, s=self: onTemplateSave(s, boxname, tedit))
        a = menu.addAction("prior versions extra dialog")
        a.triggered.connect(lambda _, s=self: extra_dialog(s, boxname, tedit))
        b = menu.addAction("prior versions in file manager")
        b.triggered.connect(lambda _, s=self: show_in_filemanager(s, boxname, tedit))
        c = menu.addAction("save, edit external and clear")
        c.triggered.connect(lambda _, s=self: save_clear_editExternal(s, boxname, tedit))
        menu.exec_(QCursor.pos())
    CardLayout.make_new_context_menu = make_new_context_menu


    def additional_clayout_setup(self):
        # https://stackoverflow.com/a/44770024
        self.tform.edit_area.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tform.edit_area.customContextMenuRequested.connect(self.make_new_context_menu)
    CardLayout.setup_edit_area = wrap(CardLayout.setup_edit_area, additional_clayout_setup)