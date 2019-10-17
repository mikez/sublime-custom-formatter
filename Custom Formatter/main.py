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
            text = format_text(text, formatter)

            view.replace(edit, region, text)


def format_text(text, command):
    suffix = extract_extension(command)
    try:
        with tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix=suffix, encoding="utf-8"
        ) as file:
            file.write(text)
            file.close()
            command = [
                file.name if FILENAME_PATTERN.match(item) else item for item in command
            ]
            run_shell_command(command)
    finally:
        if os.path.isfile(file.name):
            with open(file.name, encoding="utf-8") as file2:
                result = file2.read()
            os.remove(file.name)

    return result


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
