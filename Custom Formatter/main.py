#!/usr/bin/env python3

"""
Sublime Custom Formatter
~~~~~~~~~~~~~~~~~~~~~~~~

Format code upon save with a custom shell command.

Configure in the syntax-specific settings under the key "formatter".

Example for `JavaScript.sublime-settings`:

    {
        "formatter": [
          "/usr/local/bin/prettier", "--write", "$1.js"
        ]
    }

Note: `$1.extension` is replaced with a temporary file containing the
current code to format.
"""

import logging
import os
import re
from subprocess import PIPE, Popen
import tempfile
import time

import sublime
import sublime_plugin


logging.basicConfig(
    level=logging.INFO, format=" %(asctime)s - %(levelname)s - %(message)s"
)

FILENAME_PATTERN = re.compile(r"\$1(\.\w+)$", flags=re.ASCII)
ERROR_PATTERN_1 = re.compile(
    rb"\bline (?P<line>\d+)(?:.*\bcolumn (?P<column>\d+))?", flags=re.I
)
ERROR_PATTERN_2 = re.compile(rb"\b(\d+):(\d+)\b", flags=re.I)


class ShellNonZeroExitCode(Exception):
    """Raised when a shell process returns a non-zero exit code."""


class RunFormatEventListener(sublime_plugin.EventListener):
    @classmethod
    def on_pre_save(cls, view):
        first = time.perf_counter()
        view.run_command("run_custom_formatter")
        second = time.perf_counter()
        print("[Custom Formatter]", round(second - first, 6), "seconds runtime.")

    @classmethod
    def on_post_save_async(cls, view):
        pass


class RunCustomFormatterCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        formatter = view.settings().get("formatter")
        if not formatter:
            return

        region = sublime.Region(0, view.size())
        text = view.substr(region)
        # logging.info("Formatting with: " + formatter[0])
        try:
            text = format_text(text, formatter)
        except ShellNonZeroExitCode as error:
            point_out_issue_to_user(error, view)
        else:
            position = save_cursor_and_viewport_position(view)
            view.replace(edit, region, text)
            set_cursor_and_viewport_position(position, view)


class GotoPositionCommand(sublime_plugin.TextCommand):
    def run(self, edit, position):
        """Note: position = (row, column) are 0-based in the Sublime API."""
        row, column = position
        point = self.view.text_point(row, column)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(point))
        self.view.show(point, keep_to_left=True, animate=False)


# Actions


def format_text(text, command):
    suffix = extract_extension(command)
    try:
        filepath = write_tempfile(text, suffix)
        command = [
            filepath if FILENAME_PATTERN.match(item) else item for item in command
        ]
        # logging.info(command)
        run_shell_command(command)
        with open(filepath, encoding="utf-8") as file:
            result = file.read()

    finally:
        if os.path.isfile(filepath):
            os.remove(filepath)

    return result


def point_out_issue_to_user(error, view):
    error_message = error.args[0]
    position = extract_position_with_issue(error_message)
    if not position:
        return
    position = position[0] - 1, position[1] - 1
    view.run_command("goto_position", {"position": position})


# Helpers


def write_tempfile(text, suffix):
    with tempfile.NamedTemporaryFile(
        mode="w+", delete=False, suffix=suffix, encoding="utf-8"
    ) as file:
        filepath = file.name
        file.write(text)
    return filepath


def extract_position_with_issue(error_message):
    """Return (row, column) with issue from error message."""
    # "line 10, column 5" type of errors.
    match = ERROR_PATTERN_1.search(error_message)
    if match:
        position = match.groupdict()
        return (int(position.get("line")), int(position.get("column") or 1))
    # "10:5" type of errors.
    match = ERROR_PATTERN_2.search(error_message)
    if match:
        return (int(match.group(1)), int(match.group(2)))


def extract_extension(command):
    for item in command:
        match = FILENAME_PATTERN.match(item)
        if match:
            return match.group(1)
    return ""


def save_cursor_and_viewport_position(view):
    cursor_position = view.rowcol(view.sel()[0].a)
    viewport_position = view.viewport_position()
    return cursor_position, viewport_position


def set_cursor_and_viewport_position(position, view):
    cursor_position, viewport_position = position
    # set cursor
    view.run_command("goto_position", {"position": cursor_position})
    # set viewport
    # The next command is needed for the viewport change to work.
    view.set_viewport_position((0.0, 0.0))
    view.set_viewport_position(viewport_position)


def run_shell_command(command):
    process = Popen(command, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    if process.returncode > 0:
        logging.info(command)
        logging.error(stderr)
        raise ShellNonZeroExitCode(stderr)
