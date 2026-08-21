"""User-global configuration file (VIEWMD-0061).

Reads `$XDG_CONFIG_HOME/viewmd/config` (or `~/.config/viewmd/config`) as a flat
`key = value` file. CLI flags override these values; a missing file is a no-op.
"""

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

T = TypeVar("T")

NO_CONFIG_ENV = "VIEWMD_NO_CONFIG"
COLOR_CHOICES = ("auto", "always", "never")
THEME_CHOICES = ("dark", "light")

_TRUE = frozenset({"true", "yes", "on", "1"})
_FALSE = frozenset({"false", "no", "off", "0"})


class ConfigError(Exception):
    """The config file existed but could not be used. The message is user-facing."""


@dataclass(frozen=True)
class Config:
    """Overrides drawn from the config file. `None` means the key was not set."""

    width: str | None = None
    color: str | None = None
    full_front_matter: bool | None = None
    toc: bool | None = None
    depth: int | None = None
    theme: str | None = None


def default_config_path() -> Path:
    """XDG Base Directory path for the user-global config file.

    `$XDG_CONFIG_HOME/viewmd/config` when `XDG_CONFIG_HOME` is set and non-empty,
    otherwise `~/.config/viewmd/config`.
    """
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "viewmd" / "config"
    return Path.home() / ".config" / "viewmd" / "config"


def config_path_to_read(cli_path: str | None) -> Path | None:
    """Return the config file path to load, or `None` to skip reading one.

    `--config PATH` always wins (even when `VIEWMD_NO_CONFIG` is set). A non-empty
    `VIEWMD_NO_CONFIG` skips the default location. Otherwise the XDG path is used.
    """
    if cli_path is not None:
        return Path(cli_path)
    if os.environ.get(NO_CONFIG_ENV):
        return None
    return default_config_path()


def read_config(cli_path: str | None) -> Config:
    """Resolve and load the config file for this invocation.

    A missing default-location file is "no overrides." An explicit `--config PATH`
    that does not exist, a file that fails to parse, or an invalid value, raises
    `ConfigError`.
    """
    path = config_path_to_read(cli_path)
    if path is None:
        return Config()
    return load_config(path, required=cli_path is not None)


def load_config(path: Path, *, required: bool) -> Config:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        if not required:
            return Config()
        raise ConfigError(f"cannot read {path}: {e.strerror}") from e
    except OSError as e:
        raise ConfigError(f"cannot read {path}: {e.strerror}") from e
    except UnicodeDecodeError as e:
        raise ConfigError(f"{path}: not valid UTF-8 ({e})") from e
    return parse_config(text, source=str(path))


def parse_config(text: str, *, source: str) -> Config:
    raw: dict[str, tuple[int, str]] = {}
    for lineno, original in enumerate(text.splitlines(), start=1):
        line = original.strip()
        if not line or line.startswith("#"):
            continue
        # Optional INI section header; ignored so a `[viewmd]` file still works.
        if line.startswith("[") and line.endswith("]"):
            continue
        if "=" not in line:
            raise ConfigError(
                f"{source}:{lineno}: expected 'key = value', got {original.strip()!r}"
            )
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            raise ConfigError(f"{source}:{lineno}: missing key")
        if key in raw:
            raise ConfigError(f"{source}:{lineno}: duplicate key {key!r}")
        raw[key] = (lineno, value)

    width: str | None = None
    color: str | None = None
    full_front_matter: bool | None = None
    toc: bool | None = None
    depth: int | None = None
    theme: str | None = None
    for key, (lineno, value) in raw.items():
        if key == "width":
            width = _parse_width(value, source, lineno)
        elif key == "color":
            color = _parse_color(value, source, lineno)
        elif key == "full_front_matter":
            full_front_matter = _parse_bool(value, source, lineno, key=key)
        elif key == "toc":
            toc = _parse_bool(value, source, lineno, key=key)
        elif key == "depth":
            depth = _parse_depth(value, source, lineno)
        elif key == "theme":
            theme = _parse_theme(value, source, lineno)
        else:
            # Unknown keys are ignored (forward-compatible with future options),
            # but warned about once each so a typo doesn't silently do nothing.
            print(
                f"viewmd: {source}:{lineno}: unrecognized config key {key}",
                file=sys.stderr,
            )

    return Config(
        width=width, color=color, full_front_matter=full_front_matter, toc=toc, depth=depth,
        theme=theme,
    )


def _parse_width(value: str, source: str, lineno: int) -> str:
    if value == "full":
        return value
    if not value.lstrip("-").isdigit() or int(value) <= 0:
        raise ConfigError(
            f"{source}:{lineno}: invalid width {value!r}: must be a positive integer or 'full'"
        )
    return value


def _parse_color(value: str, source: str, lineno: int) -> str:
    if value not in COLOR_CHOICES:
        choices = ", ".join(COLOR_CHOICES)
        raise ConfigError(
            f"{source}:{lineno}: invalid color {value!r}: must be one of {choices}"
        )
    return value


def _parse_depth(value: str, source: str, lineno: int) -> int:
    if not value.isdigit() or int(value) < 1:
        raise ConfigError(
            f"{source}:{lineno}: invalid depth {value!r}: must be a positive integer"
        )
    return int(value)


def _parse_theme(value: str, source: str, lineno: int) -> str:
    if value not in THEME_CHOICES:
        choices = ", ".join(THEME_CHOICES)
        raise ConfigError(
            f"{source}:{lineno}: invalid theme {value!r}: must be one of {choices}"
        )
    return value


def _parse_bool(value: str, source: str, lineno: int, *, key: str) -> bool:
    lowered = value.lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    raise ConfigError(
        f"{source}:{lineno}: invalid {key} {value!r}: must be true or false"
    )


def coalesce(*values: T | None) -> T | None:
    """Return the first argument that is not `None`."""
    for value in values:
        if value is not None:
            return value
    return None
