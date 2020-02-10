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
from subprocess import Popen, PIPE
import tempfile

import sublime
import sublime_plugin


logging.basicConfig(
    level=logging.INFO, format=" %(asctime)s - %(levelname)s - %(message)s"
)

FILENAME_PATTERN = re.compile(r"\$1(\.\w+)$", flags=re.ASCII)


class ShellNonZeroExitCode(Exception):
    """Raised when a shell process returns a non-zero exit code."""


class RunFormatEventListener(sublime_plugin.EventListener):
    @classmethod
    def on_pre_save(cls, view):
        # logging.info('Hello Pre Save Async')
        view.run_command("run_custom_formatter")

    @classmethod
    def on_post_save_async(cls, view):
        # logging.info('Hello Post Save Async')
        pass


class RunCustomFormatterCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        formatter = view.settings().get("formatter")
        if formatter:
            region = sublime.Region(0, view.size())
            text = view.substr(region)
            # logging.info("Formatting with: " + formatter[0])
            try:
                text = format_text(text, formatter)
            except ShellNonZeroExitCode as error:
                point_out_issue_to_user(error, view)
            else:
                view.replace(edit, region, text)


class GotoPositionCommand(sublime_plugin.TextCommand):
    def run(self, edit, position):
        row, column = position
        point = self.view.text_point(row - 1, column)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(point))
        self.view.show(point)


# Actions


def format_text(text, command):
    suffix = extract_extension(command)
    try:
        filepath = write_tempfile(text, suffix)
        command = [
            filepath if FILENAME_PATTERN.match(item) else item for item in command
        ]
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
    if position:
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
    # "line 10" type of errors.
    match = re.search(rb"\bline (\d+)", error_message, flags=re.I)
    if match:
        return (int(match.group(1)), 0)
    # "2:5" type of errors.
    match = re.search(rb"\b(\d+):(\d+)\b", error_message, flags=re.I)
    if match:
        return (int(match.group(1)), int(match.group(2)))


def extract_extension(command):
    for item in command:
        match = FILENAME_PATTERN.match(item)
        if match:
            return match.group(1)
    return ""


def run_shell_command(command):
    process = Popen(command, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    if process.returncode > 0:
        logging.info(command)
        logging.error(stderr)
        raise ShellNonZeroExitCode(stderr)
