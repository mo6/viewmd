import pytest

from viewmd.config import (
    Config,
    ConfigError,
    coalesce,
    config_path_to_read,
    default_config_path,
    parse_config,
    read_config,
)


def test_default_path_uses_xdg_config_home_when_set(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert default_config_path() == tmp_path / "xdg" / "viewmd" / "config"


def test_default_path_falls_back_to_home_config_when_xdg_unset(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert default_config_path() == tmp_path / ".config" / "viewmd" / "config"


def test_default_path_treats_empty_xdg_config_home_as_unset(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", "")
    monkeypatch.setenv("HOME", str(tmp_path))
    assert default_config_path() == tmp_path / ".config" / "viewmd" / "config"


def test_config_path_to_read_prefers_explicit_cli_path_over_no_config_env(tmp_path, monkeypatch):
    monkeypatch.setenv("VIEWMD_NO_CONFIG", "1")
    assert config_path_to_read(str(tmp_path / "custom")) == tmp_path / "custom"


def test_config_path_to_read_skips_default_when_viewmd_no_config_is_set(monkeypatch):
    monkeypatch.setenv("VIEWMD_NO_CONFIG", "1")
    assert config_path_to_read(None) is None


def test_config_path_to_read_does_not_skip_when_viewmd_no_config_is_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("VIEWMD_NO_CONFIG", "")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert config_path_to_read(None) == tmp_path / "xdg" / "viewmd" / "config"


def test_parse_config_reads_each_known_key():
    cfg = parse_config(
        "width = 80\ncolor = never\nfull_front_matter = true\n",
        source="config",
    )
    assert cfg == Config(width="80", color="never", full_front_matter=True)


def test_parse_config_accepts_width_full():
    assert parse_config("width = full\n", source="config").width == "full"


def test_parse_config_accepts_boolean_synonyms():
    assert parse_config("full_front_matter = yes\n", source="c").full_front_matter is True
    assert parse_config("full_front_matter = off\n", source="c").full_front_matter is False


def test_parse_config_ignores_comments_blanks_and_section_headers():
    cfg = parse_config(
        "# a comment\n\n[viewmd]\nwidth = 40\n",
        source="config",
    )
    assert cfg.width == "40"
    assert cfg.color is None


def test_parse_config_ignores_unknown_keys():
    cfg = parse_config("toc = true\nwidth = 40\n", source="config")
    assert cfg.width == "40"


def test_parse_config_rejects_malformed_line():
    with pytest.raises(ConfigError, match="expected 'key = value'"):
        parse_config("not a config line\n", source="config")


def test_parse_config_rejects_invalid_color():
    with pytest.raises(ConfigError, match="invalid color 'purple'"):
        parse_config("color = purple\n", source="config")


def test_parse_config_rejects_invalid_width():
    with pytest.raises(ConfigError, match="invalid width"):
        parse_config("width = banana\n", source="config")


def test_parse_config_rejects_duplicate_key():
    with pytest.raises(ConfigError, match="duplicate key 'width'"):
        parse_config("width = 40\nwidth = 80\n", source="config")


def test_read_config_missing_default_file_is_empty(tmp_path, monkeypatch):
    monkeypatch.delenv("VIEWMD_NO_CONFIG", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert read_config(None) == Config()


def test_read_config_missing_explicit_path_is_an_error(tmp_path):
    missing = tmp_path / "nope"
    with pytest.raises(ConfigError, match="cannot read"):
        read_config(str(missing))


def test_read_config_loads_explicit_path(tmp_path):
    path = tmp_path / "config"
    path.write_text("color = always\n")
    assert read_config(str(path)).color == "always"


def test_coalesce_returns_first_non_none():
    assert coalesce(None, "a", "b") == "a"
    assert coalesce(None, None, False) is False
    assert coalesce(None, None) is None
