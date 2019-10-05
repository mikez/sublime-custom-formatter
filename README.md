# Sublime Custom Code Formatter

Sublime Package. Format code upon save with a custom shell command.

## Usage

1. Open the Sublime Syntax-specific settings for a particular language. For example, `JavaScript.sublime-settings`.
2. Add the `formatter` key with the words of the command to run. For example:
```
    "formatter": [
        "/usr/local/bin/prettier",
        "--config", "/configs/prettier.config.json",
        "--write",
        "$1.js",
    ]
```

Note: Any `$1.extension` item in the command list is replaced by a temporary file containing the current code to format.

## Installation

Copy the `Custom Formatter` directory into your Sublime Packages folder. For example, on macOS this is `~/Library/Application Support/Sublime Text 3/Packages/`.

Enjoy! ✨