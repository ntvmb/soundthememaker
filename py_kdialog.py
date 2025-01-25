import os
import sys
import platform
import subprocess
import logging
import traceback
import locale
from typing import Union, Optional, Literal, Tuple, List


# ---Exceptions---
class KDialogError(Exception):
    pass


class InvalidDialogTypeError(ValueError, KDialogError):
    pass


class UnexpectedNonZeroError(subprocess.CalledProcessError, KDialogError):
    pass


class CancelledError(KDialogError):
    pass


class ProgressBar:
    def __init__(self, ref: str, count: int, auto_close=False):
        self.__ref = ref
        self.__itercount = count
        self.__progress = 0
        self.__closed = False
        self.__qdbus = None
        self.__auto_close = auto_close
        qdbus_choices = ["qdbus6", "qdbus", "qdbus-qt5"]
        for executable in qdbus_choices:
            try:
                subprocess.run([executable] + self.__ref.split(), check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
            else:
                self.__qdbus = executable
                break
        else:  # no break
            raise RuntimeError(
                f"Either qdbus is missing, or the specified dbus reference \
does not exist. Please instantiate this class using the {__name__}\
.progressbar() method."
            )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not self.__closed:
            self.close()

    def close(self):
        self.__closed = True
        subprocess.run([self.__qdbus] + self.__ref.split() + ["close"])

    @property
    def closed(self):
        return self.__closed

    @property
    def progress(self):
        return self.__progress

    @progress.setter
    def progress(self, value: int):
        if not isinstance(value, int):
            raise TypeError("progress must be an integer")
        if value < 0 or value > self.__itercount:
            raise ValueError(
                f"progress must be at least 0 and at most {self.__itercount}."
            )
        self.__progress = value
        self.update()

    @property
    def itercount(self):
        return self.__itercount

    def increment(self):
        if self.__closed:
            raise ValueError("Attempted to update a closed progress bar")
        self.__progress += 1
        self.update()
        if self.__progress >= self.__itercount and self.__auto_close:
            self.close()

    def update(self):
        if self.__closed:
            raise ValueError("Attempted to update a closed progress bar")
        call_args = self.__ref.split() + ["Set", "", "value", str(self.__progress)]
        if self.__qdbus is None:
            raise RuntimeError(
                "qdbus executable is not set for some reason. \
It should have been set when this class was instantiated."
            )
        try:
            subprocess.run([self.__qdbus] + call_args, check=True)
        except subprocess.CalledProcessError as e:
            self.close()
            raise CancelledError("Progress bar was cancelled.") from e


icon = None
title = "KDialog"
_log = logging.getLogger(__name__)

# Check for Linux
if platform.system() != "Linux":
    raise ImportError("OS not supported.")

locale.setlocale(locale.LC_ALL, os.environ["LANG"])

# Check for KDialog
try:
    _proc = subprocess.run(
        ["kdialog", "-v"], capture_output=True, text=True, check=True
    )
    _log.info(f"Using {_proc.stdout.rstrip("\n")}")
except (subprocess.CalledProcessError, FileNotFoundError):
    raise ImportError("KDialog is missing or corrupt. Please install KDialog.")

# Constants
OK = 0
CANCEL = 1
YES = 2
NO = 3
CONTINUE = 4


# Common function which runs KDialog
def do_call(*args, to_stdin=None) -> Tuple[int, str]:
    """Base method which runs KDialog.
    Returns the process's return code and output.
    """
    runtime_args = ["kdialog", "--title", title] + list(args)
    if title is None:
        runtime_args.pop(1)
    if to_stdin is None:
        process = subprocess.run(runtime_args, capture_output=True, text=True)
    else:
        process = subprocess.run(
            runtime_args, input=to_stdin, capture_output=True, text=True
        )
    try:
        out = process.stdout.rstrip("\n")
    except Exception:
        out = ""
    return process.returncode, out


def yesno(
    text: str,
    *,
    dtype: Literal[0, 1, "question", "warning"] = 0,
    yes_label: Optional[str] = None,
    no_label: Optional[str] = None,
) -> int:
    """Create a dialog box with yes/no options.

    If dtype is 0 or 'question', use the regular question dialog.
    If dtype is 1 or 'warning', use the warning dialog.
    """
    call_args = []

    if yes_label is not None:
        call_args.append("--yes-label")
        call_args.append(yes_label)

    if no_label is not None:
        call_args.append("--no-label")
        call_args.append(no_label)

    if dtype == 0 or dtype == "question":
        call_args.append("--yesno")
    elif dtype == 1 or dtype == "warning":
        call_args.append("--warningyesno")
    else:
        raise InvalidDialogTypeError(
            "Invalid dialog type. Valid options are 'question' (0) and 'warning' (1)"
        )

    call_args.append(text)
    returncode = do_call(*call_args)[0]
    if returncode == 0:
        return YES
    return NO


def yesnocancel(
    text: str,
    *,
    dtype: Literal[0, 1, "question", "warning"] = 0,
    yes_label: Optional[str] = None,
    no_label: Optional[str] = None,
    cancel_label=None,
) -> int:
    """Create a dialog box with yes/no/cancel options.

    If dtype is 0 or 'question', use the regular question dialog.
    If dtype is 1 or 'warning', use the warning dialog.
    """
    call_args = []

    if yes_label is not None:
        call_args.append("--yes-label")
        call_args.append(yes_label)

    if no_label is not None:
        call_args.append("--no-label")
        call_args.append(no_label)

    if cancel_label is not None:
        call_args.append("--cancel-label")
        call_args.append(cancel_label)

    if dtype == 0 or dtype == "question":
        call_args.append("--yesnocancel")
    elif dtype == 1 or dtype == "warning":
        call_args.append("--warningyesnocancel")
    else:
        raise InvalidDialogTypeError(
            "Invalid dialog type. Valid options are 'question' (0) and 'warning' (1)"
        )

    call_args.append(text)
    returncode = do_call(*call_args)[0]
    if returncode == 0:
        return YES
    elif returncode == 1:
        return NO
    return CANCEL


def sorry(
    text: str,
    *,
    ok_label: Optional[str] = None,
    details: Optional[Union[str, BaseException]] = None,
) -> Optional[int]:
    """Create a sorry dialog box.

    An Exception can be passed to details to show the traceback.
    """
    call_args = []

    if details is not None:
        is_detailed = True
    else:
        is_detailed = False

    if ok_label is not None:
        call_args.append("--ok-label")
        call_args.append(ok_label)

    if is_detailed:
        call_args.append("--detailedsorry")
    else:
        call_args.append("--sorry")

    call_args.append(text)

    if details is not None:
        if isinstance(details, BaseException):
            call_args.append(
                "".join(
                    traceback.format_exception(
                        type(details), details, details.__traceback__
                    )
                )
            )
        else:
            call_args.append(details)

    returncode = do_call(*call_args)[0]
    if returncode == 0:
        return OK
    elif returncode == 2:
        return None
    raise UnexpectedNonZeroError(f"Unexpected non-zero return code: {returncode}")


warning = sorry  # define alias


def error(
    text: str,
    *,
    ok_label: Optional[str] = None,
    details: Optional[Union[str, BaseException]] = None,
) -> Optional[int]:
    """Create an error dialog box.

    An Exception can be passed to details to show the traceback.
    """
    call_args = []

    if details is not None:
        is_detailed = True
    else:
        is_detailed = False

    if ok_label is not None:
        call_args.append("--ok-label")
        call_args.append(ok_label)

    if is_detailed:
        call_args.append("--detailederror")
    else:
        call_args.append("--error")

    call_args.append(text)

    if details is not None:
        if isinstance(details, BaseException):
            call_args.append(
                "".join(
                    traceback.format_exception(
                        type(details), details, details.__traceback__
                    )
                )
            )
        else:
            call_args.append(details)

    returncode = do_call(*call_args)[0]
    if returncode == 0:
        return OK
    elif returncode == 2:
        return None
    raise UnexpectedNonZeroError(f"Unexpected non-zero return code: {returncode}")


alert = error


def show_exc(
    text: str,
    *,
    dtype: Literal[0, 1, "sorry", "error"] = 0,
    ok_label: Optional[str] = None,
):
    """Uses sys.exc_info to graphically show exception info with the
    desired dialog type.
    """
    if dtype == 0 or dtype == "sorry":
        sorry(text, ok_label=ok_label, details=sys.exc_info()[1])
    elif dtype == 1 or dtype == "error":
        error(text, ok_label=ok_label, details=sys.exc_info()[1])
    else:
        raise InvalidDialogTypeError(
            "Invalid dialog type. Valid options are 'sorry' (0) and 'error' (1)"
        )


def warningcontinuecancel(text, *, continue_label=None, cancel_label=None) -> int:
    """Create a warning dialog box with with continue/cancel buttons."""
    call_args = []

    if continue_label is not None:
        call_args.append("--continue-label")
        call_args.append(continue_label)

    if cancel_label is not None:
        call_args.append("--cancel-label")
        call_args.append(cancel_label)

    call_args.append("--warningcontinuecancel")
    call_args.append(text)
    returncode = do_call(*call_args)[0]
    if returncode == 0:
        return CONTINUE
    return CANCEL


def msgbox(text, *, ok_label=None):
    """Create a message box."""
    call_args = []

    if ok_label is not None:
        call_args.append("--ok-label")
        call_args.append(ok_label)

    call_args.append("--msgbox")
    call_args.append(text)
    do_call(*call_args)[0]


def inputbox(text, init=None, *, ok_label=None, cancel_label=None) -> Optional[str]:
    """Create an input box."""
    call_args = []

    if ok_label is not None:
        call_args.append("--ok-label")
        call_args.append(ok_label)

    if cancel_label is not None:
        call_args.append("--cancel-label")
        call_args.append(cancel_label)

    call_args.append("--inputbox")
    call_args.append(text)

    if init is not None:
        call_args.append(init)
    returncode, response = do_call(*call_args)
    if returncode == 0:
        return response
    return None


def imgbox(filename, *, ok_label=None):
    """Create an image box."""
    call_args = []

    if ok_label is not None:
        call_args.append("--ok-label")
        call_args.append(ok_label)

    if os.path.isdir(filename):
        raise IsADirectoryError(f"Cannot open {filename}: {os.strerror(21)}")

    if not os.path.exists(filename):
        raise FileNotFoundError(f"Cannot open {filename}: {os.strerror(2)}")

    call_args.append("--imgbox")
    call_args.append(filename)
    do_call(*call_args)[0]


def imginputbox(filename, text, *, ok_label=None) -> Optional[str]:
    """Create an image input box."""
    call_args = []

    if ok_label is not None:
        call_args.append("--ok-label")
        call_args.append(ok_label)

    if os.path.isdir(filename):
        raise IsADirectoryError(f"Cannot open {filename}: {os.strerror(21)}")

    if not os.path.exists(filename):
        raise FileNotFoundError(f"Cannot open {filename}: {os.strerror(2)}")

    call_args.append("--imginputbox")
    call_args.append(filename)
    call_args.append(text)
    returncode, response = do_call(*call_args)
    if returncode == 0:
        return response
    return None


def password(
    text="Enter password", *, ok_label=None, cancel_label=None
) -> Optional[str]:
    """Create a password box."""
    call_args = []

    if ok_label is not None:
        call_args.append("--ok-label")
        call_args.append(ok_label)

    if cancel_label is not None:
        call_args.append("--cancel-label")
        call_args.append(cancel_label)

    call_args.append("--password")
    call_args.append(text)
    returncode, response = do_call(*call_args)
    if returncode == 0:
        return response
    return None


def newpassword(
    text="Create a new password", *, ok_label=None, cancel_label=None
) -> Optional[str]:
    """Create a new password dialog box."""
    call_args = []

    if ok_label is not None:
        call_args.append("--ok-label")
        call_args.append(ok_label)

    if cancel_label is not None:
        call_args.append("--cancel-label")
        call_args.append(cancel_label)

    call_args.append("--newpassword")
    call_args.append(text)
    returncode, response = do_call(*call_args)
    if returncode == 0:
        return response
    return None


def textbox(file_or_text, *, ok_label=None, is_text=False):
    """Create a text box."""
    call_args = []

    if ok_label is not None:
        call_args.append("--ok-label")
        call_args.append(ok_label)

    if os.path.isdir(file_or_text) and not is_text:
        raise IsADirectoryError(f"Cannot open {file_or_text}: {os.strerror(21)}")

    if not (os.path.exists(file_or_text) or is_text):
        raise FileNotFoundError(f"Cannot open {file_or_text}: {os.strerror(2)}")

    call_args.append("--textbox")
    if is_text:
        call_args.append("-")
    else:
        call_args.append(file_or_text)

    if is_text:
        do_call(*call_args, to_stdin=file_or_text)[0]
    else:
        do_call(*call_args)[0]


def textinputbox(text, *, ok_label=None) -> Optional[str]:
    """Create a text input box."""
    call_args = []
    if ok_label is not None:
        call_args.append("--ok-label")
        call_args.append(ok_label)

    call_args.append("--textinputbox")
    call_args.append(text)
    returncode, response = do_call(*call_args)
    if returncode == 0:
        return response
    return None


# no, it's not one of those things you'd order at a fast food restaurant
def combobox(text, *items, ok_label=None, cancel_label=None) -> Optional[str]:
    """Create a combo box (message box with drop down menu)."""
    call_args = []
    if ok_label is not None:
        call_args.append("--ok-label")
        call_args.append(ok_label)
    if cancel_label is not None:
        call_args.append("--cancel-label")
        call_args.append(cancel_label)

    call_args.append("--combobox")
    call_args.append(text)
    call_args += list(items)

    returncode, response = do_call(*call_args)
    if returncode == 0:
        return response
    return None


def menu(text, *items, ok_label=None, cancel_label=None) -> Optional[str]:
    """
    Create a menu dialog.
    For each menu item, follow this syntax:
    tag, item
    """
    call_args = []
    if len(items) % 2 != 0:
        raise KDialogError(f"Every item must have a tag and a name.")

    if ok_label is not None:
        call_args.append("--ok-label")
        call_args.append(ok_label)
    if cancel_label is not None:
        call_args.append("--cancel-label")
        call_args.append(cancel_label)

    call_args.append("--menu")
    call_args.append(text)
    call_args += list(items)

    returncode, response = do_call(*call_args)
    if returncode == 0:
        return response
    return None


def checklist(text, *items, ok_label=None, cancel_label=None) -> Optional[str]:
    """
    Create a check list.
    For each menu item, follow this syntax:
    tag, item, on/off
    """
    call_args = []
    call_args.append("--separate-output")
    if len(items) % 3 != 0:
        raise KDialogError(
            f"Every item must have a tag, a name, and specify whether it's on or off initially."
        )

    if ok_label is not None:
        call_args.append("--ok-label")
        call_args.append(ok_label)
    if cancel_label is not None:
        call_args.append("--cancel-label")
        call_args.append(cancel_label)

    call_args.append("--checklist")
    call_args.append(text)
    call_args += list(items)

    returncode, response = do_call(*call_args)
    if returncode == 0:
        return response
    return None


def radiolist(text, *items, ok_label=None, cancel_label=None) -> Optional[str]:
    """
    Create a radio list.
    For each menu item, follow this syntax:
    tag, item, on/off
    """
    call_args = []
    call_args.append("--separate-output")
    if len(items) % 3 != 0:
        raise KDialogError(
            f"Every item must have a tag, a name, and specify whether it's on or off initially."
        )

    if ok_label is not None:
        call_args.append("--ok-label")
        call_args.append(ok_label)
    if cancel_label is not None:
        call_args.append("--cancel-label")
        call_args.append(cancel_label)

    call_args.append("--radiolist")
    call_args.append(text)
    call_args += list(items)

    returncode, response = do_call(*call_args)
    if returncode == 0:
        return response
    return None


def passivepopup(text, timeout: Optional[int] = 10):
    """Create a passive pop-up (notification)."""
    call_args = ["--passivepopup", text, str(timeout)]
    if icon is not None:
        call_args.insert(0, "--icon")
        call_args.insert(1, icon)
    do_call(call_args)


def set_icon_with_gui():
    """Graphically set the icon for passive pop-ups."""
    global icon
    icon = do_call("--geticon")[1]


def getopenfilename(
    type: Optional[str] = None, startDir: str = ".", *, allow_multiple=False
) -> Optional[List[str]]:
    """Open a file or a list of files."""
    call_args = []

    if allow_multiple:
        call_args.append("--multiple")
        call_args.append("--separate-output")
    if startDir is None:
        startDir = "."

    call_args.append("--getopenfilename")
    if startDir is not None:
        if not os.path.isdir(startDir):
            raise NotADirectoryError(f"Cannot open {startDir}: {os.strerror(20)}")
        elif not os.path.exists(startDir):
            raise FileNotFoundError(f"Cannot open {startDir}: {os.strerror(2)}")
        else:
            call_args.append(startDir)
    if type is not None:
        call_args.append(type)

    returncode, response = do_call(*call_args)
    if returncode == 0:
        return response.splitlines()
    return None


def getsavefilename(type: Optional[str] = None, startDir: str = ".") -> Optional[str]:
    """Open a dialog to save files."""
    call_args = []

    if startDir is None:
        startDir = "."

    call_args.append("--getsavefilename")
    if startDir is not None:
        if not os.path.isdir(startDir):
            raise NotADirectoryError(f"Cannot open {startDir}: {os.strerror(20)}")
        elif not os.path.exists(startDir):
            raise FileNotFoundError(f"Cannot open {startDir}: {os.strerror(2)}")
        else:
            call_args.append(startDir)
    if type is not None:
        call_args.append(type)

    returncode, response = do_call(*call_args)
    if returncode == 0:
        return response
    return None


def getexistingdirectory(startDir: str = ".") -> Optional[str]:
    """Open an existing directory."""
    call_args = []

    if startDir is None:
        startDir = "."

    call_args.append("--getexistingdirectory")
    if not os.path.isdir(startDir):
        raise NotADirectoryError(f"Cannot open {startDir}: {os.strerror(20)}")
    elif not os.path.exists(startDir):
        raise FileNotFoundError(f"Cannot open {startDir}: {os.strerror(2)}")
    else:
        call_args.append(startDir)

    returncode, response = do_call(*call_args)
    if returncode == 0:
        return response
    return None


def slider(
    text: str,
    min: int,
    max: int,
    step: Optional[int] = None,
    *,
    ok_label=None,
    cancel_label=None,
) -> Optional[int]:
    """Slider dialog box"""
    call_args = []

    if step is None:
        step = max // 10

    if ok_label is not None:
        call_args.append("--ok-label")
        call_args.append(ok_label)
    if cancel_label is not None:
        call_args.append("--cancel-label")
        call_args.append(cancel_label)

    call_args += ["--slider", str(text), str(min), str(max), str(step)]
    returncode, response = do_call(*call_args)
    if returncode == 0:
        return int(response)
    return None


def progressbar(
    label: str, count: int, auto_close=False, *, cancel_label=None
) -> ProgressBar:
    call_args = []

    if cancel_label is not None:
        call_args.append("--cancel-label")
        call_args.append(cancel_label)

    call_args += ["--progressbar", label, str(count)]
    returncode, ref = do_call(*call_args)
    if returncode != 0:
        raise UnexpectedNonZeroError(f"Bad return code: {returncode}")
    return ProgressBar(ref, count, auto_close)
