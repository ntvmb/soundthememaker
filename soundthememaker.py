import os
import pathlib
import sys
import shutil
import configparser
import json
import random
import string
import py_kdialog
from typing import List, Iterable, Any

IMPORT_SOUND = "Import sound... "
UNSET_SOUND = "Unset sound... "
NOT_A_THEME = "This doesn't look like a sound theme."
home = pathlib.Path(os.environ["HOME"]).resolve()
tmp_dir = pathlib.Path("/tmp")


class Theme:
    def __init__(self):
        self.sounds = {
            "alarm-clock-elapsed": None,
            "audio-channel-front-center": None,
            "audio-channel-front-left": None,
            "audio-channel-front-right": None,
            "audio-channel-rear-center": None,
            "audio-channel-rear-left": None,
            "audio-channel-rear-right": None,
            "audio-channel-side-left": None,
            "audio-channel-side-right": None,
            "audio-test-signal": None,
            "audio-volume-change": None,
            "battery-caution": None,
            "battery-full": None,
            "battery-low": None,
            "bell": None,
            "bell-window-system": None,
            "camera-shutter": None,
            "complete": None,
            "complete-media-burn": None,
            "complete-media-error": None,
            "completion-fail": None,
            "completion-partial": None,
            "completion-rotation": None,
            "completion-success": None,
            "desktop-login": None,
            "desktop-logout": None,
            "device-added": None,
            "device-removed": None,
            "dialog-error": None,
            "dialog-error-critical": None,
            "dialog-error-serious": None,
            "dialog-error-veryserious": None,
            "dialog-information": None,
            "dialog-question": None,
            "dialog-special": None,
            "dialog-warning": None,
            "game-over-loser": None,
            "game-over-winner": None,
            "media-insert-request": None,
            "message": None,
            "message-attention": None,
            "message-connectivity-problem": None,
            "message-connectivity-error": None,
            "message-connectivity-error-serious": None,
            "message-connectivity-lost": None,
            "message-contact-in": None,
            "message-contact-out": None,
            "message-error": None,
            "message-highlight": None,
            "message-irc-event": None,
            "message-lowpriority": None,
            "message-new-email": None,
            "message-new-instant": None,
            "message-new-sms": None,
            "message-sent-instant": None,
            "network-connectivity-established": None,
            "network-connectivity-lost": None,
            "outcome-failure": None,
            "outcome-success": None,
            "phone-incoming-call": None,
            "phone-outgoing-busy": None,
            "phone-outgoing-calling": None,
            "power-plug": None,
            "power-unplug": None,
            "print-error": None,
            "service-login": None,
            "service-logout": None,
            "theme-demo": None,
            "trash-empty": None,
            "window-attention": None,
            "window-close": None,
            "window-maximized": None,
            "window-minimized": None,
            "window-move-end": None,
            "window-move-start": None,
            "window-pin": None,
            "window-question": None,
            "window-shaded": None,
            "window-unpin": None,
            "window-unshaded": None,
        }
        self.imported_sounds = []
        self.name = "Sound theme"
        self.comment = "This is a sound theme!"
        self.path = None
        self.modified = False


def set_title():
    tmp_name = py_kdialog.inputbox("Enter theme name...", the_theme.name)
    if tmp_name is not None:
        the_theme.name = tmp_name
        the_theme.modified = True


def set_comment():
    tmp_comment = py_kdialog.inputbox("Enter theme comment...", the_theme.comment)
    if tmp_comment is not None:
        the_theme.comment = tmp_comment
        the_theme.modified = True


def edit_sound(sound):
    items = the_theme.imported_sounds.copy()
    items.append(UNSET_SOUND)
    items.append(IMPORT_SOUND)
    if len(items) > 2:
        the_sound = py_kdialog.combobox(f"Choose a sound to use for {sound}.", *items)
    else:
        the_sound = IMPORT_SOUND
    if the_sound == IMPORT_SOUND:
        the_sound = py_kdialog.getopenfilename(
            "audio/flac audio/mpeg audio/vnd.wave audio/ogg audio/aac"
        )
        if the_sound is not None:
            the_sound = the_sound[0]
        the_theme.imported_sounds.append(the_sound)
        os.chdir(pathlib.Path(the_sound).parent)
    if the_sound is not None:
        if the_sound != UNSET_SOUND:
            the_theme.sounds[sound] = the_sound
        else:
            the_theme.sounds[sound] = None
        the_theme.modified = True


def add_sound():
    editing_sounds = True
    while editing_sounds:
        py_kdialog.title = f"Editing sounds in theme {the_theme.name}"
        items_dict = {k: f"{k} ({v})" for k, v in the_theme.sounds.items()}
        items = []
        for k, v in items_dict.items():
            items += [k, v]
        the_sound = py_kdialog.menu("Choose a sound to define:", *items)
        if the_sound is not None:
            edit_sound(the_sound)
        else:
            editing_sounds = False


def save_theme(force_dialog=False):
    py_kdialog.title = "Save theme"
    data = {
        "name": the_theme.name,
        "comment": the_theme.comment,
        "sounds": the_theme.sounds,
    }
    if the_theme.path is None or force_dialog:
        filename = py_kdialog.getsavefilename("application/json", str(home))
        if filename is None:
            return py_kdialog.CANCEL
    else:
        filename = the_theme.path
    with open(filename, "w") as fp:
        json.dump(data, fp, indent=4)
        the_theme.modified = False
        the_theme.path = filename
        return py_kdialog.OK


def export_theme(*, savedir=None, quiet=False):
    if not quiet:
        py_kdialog.title = "Export theme"
    if the_theme.modified:
        if not quiet:
            py_kdialog.msgbox("To export your theme, you must save it first.")
            status = save_theme()
            if status == py_kdialog.CANCEL:
                return
        else:
            raise RuntimeError("Theme not saved.")
    if savedir is None:
        savedir = py_kdialog.getsavefilename("inode/directory", str(home))
    if savedir is None:
        return
    workdir = tmp_dir / "".join(
        random.choices(string.ascii_letters + string.digits, k=5)
    )
    os.mkdir(workdir)
    os.mkdir(workdir / "stereo")
    index_theme = configparser.ConfigParser(interpolation=None)
    index_theme.optionxform = str
    index_theme["Sound Theme"] = {
        "Name": the_theme.name,
        "Comment": the_theme.comment,
        "Directories": "stereo",
        "Example": "theme-demo",
    }
    index_theme["stereo"] = {"OutputProfile": "stereo"}
    with (workdir / "index.theme").open("w") as fp:
        index_theme.write(fp, space_around_delimiters=False)
    for sound_name, sound_path in the_theme.sounds.items():
        if sound_path is not None:
            write_to = (
                workdir / "stereo" / f"{sound_name}{pathlib.Path(sound_path).suffix}"
            )
            shutil.copy(sound_path, str(write_to))
    shutil.copytree(workdir, savedir, dirs_exist_ok=True)
    shutil.rmtree(workdir)
    if not quiet:
        py_kdialog.msgbox("Theme export success!")


def install_theme():
    # TODO: Allow global installation
    py_kdialog.title = "Install theme"
    if the_theme.modified:
        py_kdialog.msgbox("To install your theme, you must save it first.")
        return
    savedir = (
        home
        / ".local"
        / "share"
        / "sounds"
        / "".join(e for e in the_theme.name if e.isalnum()).lower()
    )
    savedir.mkdir(parents=True, exist_ok=True)
    export_theme(savedir=str(savedir), quiet=True)
    py_kdialog.msgbox("Theme installation success!")


def edit_theme():
    editing = True
    while editing:
        file_info = the_theme.path if the_theme.path is not None else the_theme.name
        py_kdialog.title = f"Sound theme maker ({file_info})"
        # fmt: off
        choice = py_kdialog.menu(
            "What would you like to do?",
            "0", "Set theme name",
            "1", "Set theme comment",
            "2", "Edit sounds",
            "3", "Save theme",
            "5", "Export theme",
            "4", "Install theme",
        )
        # fmt: on
        try:
            match choice:
                case "0":
                    set_title()
                case "1":
                    set_comment()
                case "2":
                    add_sound()
                case "3":
                    save_theme()
                case "4":
                    install_theme()
                case "5":
                    export_theme()
                case _:
                    if the_theme.modified:
                        ans = py_kdialog.yesnocancel(
                            f"Save changes to {file_info}?", dtype=1
                        )
                        if ans == py_kdialog.YES:
                            save_theme()
                            editing = False
                        elif ans == py_kdialog.NO:
                            editing = False
                    else:
                        editing = False
        except NotImplementedError:
            py_kdialog.error("This functionality is not implemented.")


def new_theme():
    global the_theme
    the_theme = Theme()
    the_theme.modified = True
    set_title()
    edit_theme()


def existing_theme():
    # TODO: Implement this function
    raise NotImplementedError


def json_theme():
    global the_theme
    py_kdialog.title = "Open theme JSON"
    filename = py_kdialog.getopenfilename("application/json")
    if filename is not None:
        filename = filename[0]
        the_theme = Theme()
        the_theme.path = filename
        try:
            with open(filename) as fp:
                data = json.load(fp)
            if not isinstance(data, dict):
                raise TypeError(NOT_A_THEME)
            try:
                the_theme.name = data["name"]
                the_theme.comment = data["comment"]
            except KeyError as e:
                raise TypeError(NOT_A_THEME) from e
            sounds = data.get("sounds")
            if not isinstance(sounds, dict):
                raise TypeError(NOT_A_THEME)
            for k, v in sounds.items():
                if v is not None and not os.path.exists(v):
                    raise FileNotFoundError(f"Missing sound: {v}")
                elif v is not None:
                    the_theme.imported_sounds.append(v)
                if k in the_theme.sounds:
                    the_theme.sounds[k] = v
                else:
                    raise ValueError(f"Unknown sound ID: {v}")
        except Exception:
            py_kdialog.show_exc(f"An error occurred parsing {filename}:", dtype=1)
            return
        edit_theme()


def main_menu():
    py_kdialog.title = "Sound theme maker"
    # fmt: off
    choice = py_kdialog.menu(
        "What would you like to do?",
        "0", "Create a new theme",
        "2", "Open theme JSON",
        "1", "Import an existing theme",
    )
    # fmt: on
    match choice:
        case "0":
            new_theme()
        case "1":
            existing_theme()
        case "2":
            json_theme()
        case _:
            sys.exit(0)


def main():
    while True:
        try:
            main_menu()
        except NotImplementedError:
            py_kdialog.error("This functionality is not implemented.")
        except Exception:
            py_kdialog.show_exc(
                "A serious error has occurred. Details are shown below.", dtype=1
            )


if __name__ == "__main__":
    main()
