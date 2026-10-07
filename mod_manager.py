"""Small GUI manager for Vencord user plugins on Windows.

The executable is intentionally small: Vencord, Node.js and pnpm are cached on
first use under %LOCALAPPDATA%\VencordModManager instead of bundled into it.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import uuid
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from tkinter import BooleanVar, StringVar, Tk, filedialog, messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Callable


APP_NAME = "Vencord Mod Manager"
APP_VERSION = "1.5"
VENCORD_REPOSITORY = "Vendicated/Vencord"
PNPM_VERSION = "11.9.0"
NODE_MAJOR = 22
USER_AGENT = f"{APP_NAME}/{APP_VERSION}"
BUNDLED_PLUGIN_ID = "voice-streaks"
BUNDLED_VOICE_STREAKS_VERSION = 2
DEFAULT_LANGUAGE = "en"
LANGUAGE_NAMES = {"en": "English", "ru": "Русский"}


TEXT = {
    "en": {
        "language": "Language:",
        "language_changed": "Interface language: {language}",
        "source_warning": "Mods run third-party code inside Discord. Check archives and GitHub repositories before installing.",
        "refresh": "Refresh",
        "add_zip": "Add ZIP",
        "add_github": "Add GitHub",
        "remove_from_manager": "Remove from manager",
        "build_and_install": "Build and install",
        "restore_backup": "Restore backup",
        "check_userplugins": "Check userplugins",
        "plugins_heading": "Mods — select the ones to include in the build",
        "userplugins_heading": "Actual src/userplugins folders",
        "log_heading": "Log",
        "no_plugins": "No mods added yet.",
        "no_userplugins": "No Vencord user-plugin folders found yet.",
        "managed_by_manager": "Managed by the manager",
        "added_manually": "Added manually",
        "delete_files": "Delete files",
        "source_bundled": "Built-in plugin",
        "source_recovered": "Recovered plugin",
        "trust_sources": "Only add mods from sources you trust.",
        "discord_not_found": "Discord was not found. Install Discord or click Refresh after installing it.",
        "choose_zip": "Select a ZIP with a Vencord mod",
        "zip_archive": "ZIP archive",
        "github_prompt": "GitHub URL for the mod:\nhttps://github.com/owner/repository",
        "no_plugin_selected": "Select a mod with its checkbox to remove it.",
        "remove_confirmation": "Remove {count} mod(s) from the manager?",
        "delete_folder_confirmation": "Permanently delete the “{folder}” folder from src/userplugins? This cannot be undone. To apply it in Discord, click “Build and install” afterwards.",
        "select_discord": "Select an installed Discord first.",
        "build_confirmation": "The manager will build the selected mods. Discord will be closed only after a successful build, before installing and backing up app.asar. Continue?",
        "restore_confirmation": "Discord will be closed and app.asar will be restored from this manager's backup. Continue?",
        "error_prefix": "Error: {detail}",
        "unexpected_error": "Unexpected error: {detail}",
        "downloading": "Downloading: {url}",
        "vencord_ready": "Vencord is ready.",
        "node_ready": "Node.js {version} is ready.",
        "no_selected_plugins": "No mods are selected in the manager. Manually added userplugins will be kept.",
        "plugin_added": "Added mod: {name}",
        "plugin_removed": "Removed mod: {name}",
        "userplugin_deleted": "Deleted userplugins folder: {folder}",
        "build_ready": "Build is ready. Closing Discord...",
        "installation_done": "Done. Start Discord normally.",
        "restoration_done": "Restore completed.",
        "backup_created": "Backup created: {name}",
        "wrapper_installed": "Vencord ASAR wrapper installed.",
        "wrapper_restored": "Original app.asar restored.",
        "cannot_read_plugin_list": "Could not read the mod list: {detail}",
        "could_not_download": "Could not download the file: {detail}",
        "unsafe_archive": "The archive contains an unsafe path or symbolic link.",
        "invalid_zip": "The selected file is not a valid ZIP archive.",
        "plugin_entry_not_found": "index.ts or index.tsx was not found. This is not a Vencord user-plugin.",
        "archive_not_found": "Archive not found.",
        "github_public_only": "Only public github.com/owner/repository URLs are supported.",
        "github_url_required": "Use a URL like https://github.com/owner/repository",
        "github_metadata_failed": "Could not fetch the GitHub repository: {detail}",
        "invalid_plugin_path": "Invalid mod path.",
        "invalid_userplugins_folder": "Invalid userplugins folder.",
        "vencord_root_failed": "Could not determine the Vencord root folder.",
        "node_lts_failed": "Could not select a Node.js LTS release: {detail}",
        "node_missing": "node.exe was not found in the Node.js archive.",
        "command_failed": "Command exited with code {code}.",
        "npm_missing": "npm.cmd was not found in portable Node.js.",
        "pnpm_missing": "pnpm.cmd was not found after installation.",
        "plugin_files_missing": "Files for “{name}” are missing. Add the mod again.",
        "plugin_folder_owned": "The “{folder}” folder belongs to another manager mod.",
        "plugin_folder_manual": "The “{folder}” folder was added manually. Rename or delete it before installing this mod.",
        "patcher_missing": "Build finished without dist/patcher.js.",
        "asar_missing": "{path} was not found.",
        "asar_busy": "Discord is still holding app.asar. Fully close Discord and try installing again.",
        "backup_missing": "This manager's backup was not found.",
        "discord_close_timeout": "Discord did not close within 15 seconds and is holding app.asar. Close it in Task Manager and try again."
    },
    "ru": {
        "language": "Язык:",
        "language_changed": "Язык интерфейса: {language}",
        "source_warning": "Моды выполняют сторонний код внутри Discord. Проверяйте архивы и GitHub-репозитории перед установкой.",
        "refresh": "Обновить",
        "add_zip": "Добавить ZIP",
        "add_github": "Добавить GitHub",
        "remove_from_manager": "Удалить из менеджера",
        "build_and_install": "Собрать и установить",
        "restore_backup": "Восстановить резервную копию",
        "check_userplugins": "Проверить userplugins",
        "plugins_heading": "Моды — включите нужные перед сборкой",
        "userplugins_heading": "Реальные папки src/userplugins",
        "log_heading": "Журнал",
        "no_plugins": "Модов пока нет.",
        "no_userplugins": "Папок с Vencord user-plugin пока нет.",
        "managed_by_manager": "Управляется менеджером",
        "added_manually": "Добавлен вручную",
        "delete_files": "Удалить файлы",
        "source_bundled": "Встроенный мод",
        "source_recovered": "Восстановленный мод",
        "trust_sources": "Добавляйте только моды из источников, которым доверяете.",
        "discord_not_found": "Discord не найден. Установите Discord или нажмите «Обновить» после установки.",
        "choose_zip": "Выберите ZIP с Vencord модом",
        "zip_archive": "ZIP-архив",
        "github_prompt": "Ссылка GitHub на мод:\nhttps://github.com/владелец/репозиторий",
        "no_plugin_selected": "Отметьте мод галочкой, чтобы удалить его.",
        "remove_confirmation": "Удалить {count} мод(а/ов) из менеджера?",
        "delete_folder_confirmation": "Физически удалить папку «{folder}» из src/userplugins? Это нельзя отменить. Для применения в Discord затем нажмите «Собрать и установить».",
        "select_discord": "Сначала выберите установленный Discord.",
        "build_confirmation": "Менеджер соберёт выбранные моды. Discord будет закрыт только после успешной сборки, перед установкой и резервным копированием app.asar. Продолжить?",
        "restore_confirmation": "Discord будет закрыт, а app.asar будет восстановлен из резервной копии менеджера. Продолжить?",
        "error_prefix": "Ошибка: {detail}",
        "unexpected_error": "Непредвиденная ошибка: {detail}",
        "downloading": "Скачивание: {url}",
        "vencord_ready": "Vencord подготовлен.",
        "node_ready": "Node.js {version} подготовлен.",
        "no_selected_plugins": "В менеджере не выбрано модов. Ручные userplugins сохраняются.",
        "plugin_added": "Добавлен мод: {name}",
        "plugin_removed": "Удалён мод: {name}",
        "userplugin_deleted": "Удалена папка userplugins: {folder}",
        "build_ready": "Сборка готова. Закрытие Discord...",
        "installation_done": "Готово. Запустите Discord обычным способом.",
        "restoration_done": "Восстановление завершено.",
        "backup_created": "Создана резервная копия: {name}",
        "wrapper_installed": "Vencord ASAR-wrapper установлен.",
        "wrapper_restored": "Оригинальный app.asar восстановлен.",
        "cannot_read_plugin_list": "Не удалось прочитать список модов: {detail}",
        "could_not_download": "Не удалось скачать файл: {detail}",
        "unsafe_archive": "Архив содержит небезопасный путь или символическую ссылку.",
        "invalid_zip": "Выбранный файл не является корректным ZIP-архивом.",
        "plugin_entry_not_found": "Не найден index.ts или index.tsx. Это не Vencord user-plugin.",
        "archive_not_found": "Архив не найден.",
        "github_public_only": "Поддерживаются только публичные ссылки github.com/владелец/репозиторий.",
        "github_url_required": "Укажите ссылку вида https://github.com/владелец/репозиторий",
        "github_metadata_failed": "Не удалось получить репозиторий GitHub: {detail}",
        "invalid_plugin_path": "Некорректный путь мода.",
        "invalid_userplugins_folder": "Некорректная папка userplugins.",
        "vencord_root_failed": "Не удалось определить корневую папку Vencord.",
        "node_lts_failed": "Не удалось подобрать Node.js LTS: {detail}",
        "node_missing": "В архиве Node.js не найден node.exe.",
        "command_failed": "Команда завершилась с кодом {code}.",
        "npm_missing": "В portable Node.js не найден npm.cmd.",
        "pnpm_missing": "После установки не найден pnpm.cmd.",
        "plugin_files_missing": "Файлы мода «{name}» отсутствуют. Добавьте его снова.",
        "plugin_folder_owned": "Папка «{folder}» принадлежит другому моду менеджера.",
        "plugin_folder_manual": "Папка «{folder}» добавлена вручную. Переименуйте или удалите её перед установкой этого мода.",
        "patcher_missing": "Сборка завершилась без dist/patcher.js.",
        "asar_missing": "Не найден {path}.",
        "asar_busy": "Discord всё ещё удерживает app.asar. Полностью закройте Discord и повторите установку.",
        "backup_missing": "Резервная копия этого менеджера не найдена.",
        "discord_close_timeout": "Discord не завершился за 15 секунд и удерживает app.asar. Закройте его через Диспетчер задач и повторите."
    }
}


def text_for(language: str, key: str, **values: object) -> str:
    """Format an interface string in the selected language."""
    template = TEXT.get(language, TEXT[DEFAULT_LANGUAGE]).get(key, TEXT[DEFAULT_LANGUAGE].get(key, key))
    return template.format(**values)


@dataclass(frozen=True)
class LocalizedMessage:
    key: str
    values: dict[str, object]


def message(key: str, **values: object) -> LocalizedMessage:
    return LocalizedMessage(key, values)


def app_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "VencordModManager"


def bundled_root() -> Path:
    """Return the source folder in development or PyInstaller's extracted data."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


class ManagerSettings:
    """Small, separate settings file so existing plugin lists need no migration."""

    def __init__(self) -> None:
        self.path = app_root() / "settings.json"

    def load_language(self) -> str:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return DEFAULT_LANGUAGE
        language = raw.get("language") if isinstance(raw, dict) else None
        return language if language in LANGUAGE_NAMES else DEFAULT_LANGUAGE

    def save_language(self, language: str) -> None:
        if language not in LANGUAGE_NAMES:
            raise ValueError(f"Unsupported language: {language}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"language": language}, indent=2), encoding="utf-8")
        temporary.replace(self.path)


@dataclass
class PluginRecord:
    plugin_id: str
    name: str
    source_type: str
    source: str
    enabled: bool = False
    bundled_version: int | None = None


@dataclass(frozen=True)
class InstalledUserPlugin:
    folder_name: str
    managed_plugin_id: str | None


class ManagerError(RuntimeError):
    def __init__(self, key: str, **values: object) -> None:
        super().__init__(key)
        self.key = key
        self.values = values


class ModManager:
    def __init__(self, log: Callable[[str | LocalizedMessage], None]):
        self.root = app_root()
        self.cache = self.root / "cache"
        self.imports = self.root / "plugins"
        self.config_path = self.root / "plugins.json"
        self.log = log
        self.root.mkdir(parents=True, exist_ok=True)
        self.cache.mkdir(exist_ok=True)
        self.imports.mkdir(exist_ok=True)

    def load_plugins(self) -> list[PluginRecord]:
        if not self.config_path.exists():
            plugins: list[PluginRecord] = []
        else:
            try:
                raw = json.loads(self.config_path.read_text(encoding="utf-8"))
                plugins = [PluginRecord(**item) for item in raw if isinstance(item, dict)]
            except (json.JSONDecodeError, OSError, TypeError) as error:
                raise ManagerError("cannot_read_plugin_list", detail=error) from error

        changed = self._ensure_bundled_plugins(plugins)
        known_ids = {plugin.plugin_id for plugin in plugins}
        for directory in sorted(self.imports.iterdir(), key=lambda path: path.name.lower()):
            if directory.name in known_ids or not directory.is_dir():
                continue
            try:
                self._find_plugin_folder(directory)
            except ManagerError:
                continue
            plugins.append(PluginRecord(
                plugin_id=directory.name,
                name=re.sub(r"-[0-9a-f]{8}$", "", directory.name),
                source_type="recovered",
                source=str(directory),
                enabled=False
            ))
            changed = True

        if changed:
            self.save_plugins(plugins)
        return plugins

    def _ensure_bundled_plugins(self, plugins: list[PluginRecord]) -> bool:
        archive = bundled_root() / "bundled_plugins" / "voiceStreaks.zip"
        if not archive.is_file():
            return False

        existing = next((plugin for plugin in plugins if plugin.plugin_id == BUNDLED_PLUGIN_ID), None)
        target = self.imports / BUNDLED_PLUGIN_ID
        if existing and (existing.source_type != "bundled" or existing.bundled_version == BUNDLED_VOICE_STREAKS_VERSION):
            return False

        if target.is_dir():
            shutil.rmtree(target)
        if not target.is_dir():
            self._safe_extract(archive, target)
        self._find_plugin_folder(target)
        if existing:
            existing.name = "VoiceStreaks"
            existing.source_type = "bundled"
            existing.source = "bundled"
            existing.bundled_version = BUNDLED_VOICE_STREAKS_VERSION
        else:
            plugins.append(PluginRecord(
                plugin_id=BUNDLED_PLUGIN_ID,
                name="VoiceStreaks",
                source_type="bundled",
                source="bundled",
                enabled=False,
                bundled_version=BUNDLED_VOICE_STREAKS_VERSION
            ))
        return True

    def save_plugins(self, plugins: list[PluginRecord]) -> None:
        temporary = self.config_path.with_suffix(".tmp")
        temporary.write_text(json.dumps([asdict(plugin) for plugin in plugins], ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.config_path)

    def _download(self, url: str, destination: Path) -> None:
        self.log(message("downloading", url=url))
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
        except OSError as error:
            destination.unlink(missing_ok=True)
            raise ManagerError("could_not_download", detail=error) from error

    @staticmethod
    def _safe_extract(archive: Path, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        base = destination.resolve()
        try:
            with zipfile.ZipFile(archive) as zip_file:
                for entry in zip_file.infolist():
                    target = (destination / entry.filename).resolve()
                    is_link = (entry.external_attr >> 16) & 0o170000 == 0o120000
                    if is_link or not target.is_relative_to(base):
                        raise ManagerError("unsafe_archive")
                zip_file.extractall(destination)
        except zipfile.BadZipFile as error:
            raise ManagerError("invalid_zip") from error

    @staticmethod
    def _find_plugin_folder(root: Path) -> Path:
        direct = [root / "index.ts", root / "index.tsx"]
        for candidate in direct:
            if candidate.is_file():
                return root

        candidates = sorted(
            [
                *(path.parent for path in root.rglob("index.ts") if "node_modules" not in path.parts),
                *(path.parent for path in root.rglob("index.tsx") if "node_modules" not in path.parts)
            ],
            key=lambda path: (len(path.relative_to(root).parts), str(path).lower())
        )
        if not candidates:
            raise ManagerError("plugin_entry_not_found")
        return candidates[0]

    @staticmethod
    def _safe_name(value: str) -> str:
        result = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-").lower()
        return result[:48] or "plugin"

    def _import_archive(self, archive: Path, name: str, source_type: str, source: str) -> PluginRecord:
        if not archive.is_file():
            raise ManagerError("archive_not_found")
        plugin_id = f"{self._safe_name(name)}-{uuid.uuid4().hex[:8]}"
        temporary = self.imports / f".import-{uuid.uuid4().hex}"
        try:
            self._safe_extract(archive, temporary)
            plugin_folder = self._find_plugin_folder(temporary)
            target = self.imports / plugin_id
            shutil.copytree(plugin_folder, target, ignore=shutil.ignore_patterns("node_modules", ".git", "dist"))
            return PluginRecord(plugin_id=plugin_id, name=name, source_type=source_type, source=source)
        finally:
            shutil.rmtree(temporary, ignore_errors=True)

    def import_zip(self, archive: Path) -> PluginRecord:
        return self._import_archive(archive, archive.stem, "zip", str(archive))

    @staticmethod
    def _parse_github_url(url: str) -> tuple[str, str]:
        parsed = urllib.parse.urlparse(url.strip())
        if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
            raise ManagerError("github_public_only")
        parts = [part for part in parsed.path.strip("/").split("/") if part]
        if len(parts) < 2:
            raise ManagerError("github_url_required")
        return parts[0], parts[1].removesuffix(".git")

    def import_github(self, url: str) -> PluginRecord:
        owner, repository = self._parse_github_url(url)
        api_url = f"https://api.github.com/repos/{owner}/{repository}"
        request = urllib.request.Request(api_url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                metadata = json.load(response)
            branch = metadata["default_branch"]
        except (OSError, KeyError, json.JSONDecodeError) as error:
            raise ManagerError("github_metadata_failed", detail=error) from error

        archive = self.cache / f"github-{hashlib.sha256(url.encode()).hexdigest()[:16]}.zip"
        self._download(f"https://github.com/{owner}/{repository}/archive/refs/heads/{branch}.zip", archive)
        try:
            return self._import_archive(archive, repository, "github", f"https://github.com/{owner}/{repository}")
        finally:
            archive.unlink(missing_ok=True)

    def remove_plugin(self, plugin: PluginRecord) -> None:
        target = (self.imports / plugin.plugin_id).resolve()
        if target.parent != self.imports.resolve():
            raise ManagerError("invalid_plugin_path")
        shutil.rmtree(target, ignore_errors=True)

    def _managed_vencord(self) -> Path:
        return self.cache / "vencord"

    def _userplugins_directory(self) -> Path:
        return self._managed_vencord() / "src" / "userplugins"

    @staticmethod
    def _manifest_path(userplugins: Path) -> Path:
        return userplugins / ".vmm-managed.json"

    def _load_managed_manifest(self, userplugins: Path) -> dict[str, str]:
        manifest = self._manifest_path(userplugins)
        if not manifest.is_file():
            return {}
        try:
            raw = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(raw, dict):
            return {}
        return {
            folder: plugin_id
            for folder, plugin_id in raw.items()
            if isinstance(folder, str) and isinstance(plugin_id, str)
        }

    def _save_managed_manifest(self, userplugins: Path, managed: dict[str, str]) -> None:
        userplugins.mkdir(parents=True, exist_ok=True)
        temporary = self._manifest_path(userplugins).with_suffix(".tmp")
        temporary.write_text(json.dumps(managed, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self._manifest_path(userplugins))

    @staticmethod
    def _validated_userplugin_path(userplugins: Path, folder_name: str) -> Path:
        target = (userplugins / folder_name).resolve()
        if target.parent != userplugins.resolve() or not target.is_dir():
            raise ManagerError("invalid_userplugins_folder")
        return target

    def scan_userplugins(self) -> list[InstalledUserPlugin]:
        userplugins = self._userplugins_directory()
        if not userplugins.is_dir():
            return []
        managed = self._load_managed_manifest(userplugins)
        installed: list[InstalledUserPlugin] = []
        for directory in sorted(userplugins.iterdir(), key=lambda path: path.name.lower()):
            if directory.name.startswith(".") or not directory.is_dir():
                continue
            try:
                self._find_plugin_folder(directory)
            except ManagerError:
                continue
            installed.append(InstalledUserPlugin(directory.name, managed.get(directory.name)))
        return installed

    def delete_userplugin_folder(self, folder_name: str) -> str | None:
        userplugins = self._userplugins_directory()
        target = self._validated_userplugin_path(userplugins, folder_name)
        managed = self._load_managed_manifest(userplugins)
        managed_plugin_id = managed.pop(folder_name, None)
        shutil.rmtree(target)
        self._save_managed_manifest(userplugins, managed)
        return managed_plugin_id

    def _fetch_vencord(self) -> Path:
        workspace = self._managed_vencord()
        if (workspace / "package.json").is_file():
            return workspace

        temporary = self.cache / f"vencord-{uuid.uuid4().hex}.zip"
        extracted = self.cache / f"vencord-extract-{uuid.uuid4().hex}"
        try:
            self._download(f"https://github.com/{VENCORD_REPOSITORY}/archive/refs/heads/main.zip", temporary)
            self._safe_extract(temporary, extracted)
            candidates = [path for path in extracted.iterdir() if (path / "package.json").is_file()]
            if len(candidates) != 1:
                raise ManagerError("vencord_root_failed")
            shutil.rmtree(workspace, ignore_errors=True)
            shutil.move(str(candidates[0]), workspace)
            self.log(message("vencord_ready"))
            return workspace
        finally:
            temporary.unlink(missing_ok=True)
            shutil.rmtree(extracted, ignore_errors=True)

    def _managed_node(self) -> Path:
        node_cache = self.cache / "node"
        executable = next(node_cache.rglob("node.exe"), None) if node_cache.exists() else None
        if executable:
            return executable.parent

        architecture = "arm64" if os.environ.get("PROCESSOR_ARCHITECTURE", "").upper() == "ARM64" else "x64"
        request = urllib.request.Request("https://nodejs.org/dist/index.json", headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                releases = json.load(response)
            release = next((item for item in releases if item.get("lts") and item["version"].startswith(f"v{NODE_MAJOR}.")), None)
            release = release or next(item for item in releases if item.get("lts"))
            version = release["version"]
        except (OSError, StopIteration, KeyError, json.JSONDecodeError) as error:
            raise ManagerError("node_lts_failed", detail=error) from error

        archive = self.cache / f"node-{version}-{architecture}.zip"
        try:
            self._download(f"https://nodejs.org/dist/{version}/node-{version}-win-{architecture}.zip", archive)
            shutil.rmtree(node_cache, ignore_errors=True)
            self._safe_extract(archive, node_cache)
            executable = next(node_cache.rglob("node.exe"), None)
            if not executable:
                raise ManagerError("node_missing")
            self.log(message("node_ready", version=version))
            return executable.parent
        finally:
            archive.unlink(missing_ok=True)

    @staticmethod
    def _run(command: list[str], cwd: Path, environment: dict[str, str], log: Callable[[str | LocalizedMessage], None]) -> None:
        log("$ " + " ".join(command))
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        assert process.stdout is not None
        for line in process.stdout:
            log(line.rstrip())
        if process.wait() != 0:
            raise ManagerError("command_failed", code=process.returncode)

    def _managed_pnpm(self, node_dir: Path) -> Path:
        tools = self.cache / "tools"
        pnpm = tools / "pnpm.cmd"
        if pnpm.is_file():
            return pnpm

        npm = node_dir / "npm.cmd"
        if not npm.is_file():
            raise ManagerError("npm_missing")
        environment = os.environ.copy()
        environment["PATH"] = f"{node_dir};{environment.get('PATH', '')}"
        self._run([str(npm), "install", "--global", "--prefix", str(tools), f"pnpm@{PNPM_VERSION}"], self.cache, environment, self.log)
        if not pnpm.is_file():
            raise ManagerError("pnpm_missing")
        return pnpm

    def build(self, plugins: list[PluginRecord]) -> Path:
        workspace = self._fetch_vencord()
        node_dir = self._managed_node()
        pnpm = self._managed_pnpm(node_dir)
        userplugins = self._userplugins_directory()
        userplugins.mkdir(parents=True, exist_ok=True)
        previous_managed = self._load_managed_manifest(userplugins)

        selected = [plugin for plugin in plugins if plugin.enabled]
        desired_managed = {self._safe_name(plugin.plugin_id): plugin.plugin_id for plugin in selected}
        for folder_name in previous_managed:
            if folder_name not in desired_managed:
                target = userplugins / folder_name
                if target.is_dir():
                    shutil.rmtree(self._validated_userplugin_path(userplugins, folder_name))

        if not selected:
            self.log(message("no_selected_plugins"))
        for plugin in selected:
            source = self.imports / plugin.plugin_id
            if not source.is_dir():
                raise ManagerError("plugin_files_missing", name=plugin.name)
            target = userplugins / self._safe_name(plugin.plugin_id)
            owner = previous_managed.get(target.name)
            if target.exists() and owner not in {None, plugin.plugin_id}:
                raise ManagerError("plugin_folder_owned", folder=target.name)
            if target.exists() and owner is None:
                raise ManagerError("plugin_folder_manual", folder=target.name)
            if target.is_dir():
                shutil.rmtree(self._validated_userplugin_path(userplugins, target.name))
            shutil.copytree(source, target, ignore=shutil.ignore_patterns("node_modules", ".git", "dist"))
            self.log(message("plugin_added", name=plugin.name))
        self._save_managed_manifest(userplugins, desired_managed)

        environment = os.environ.copy()
        environment["PATH"] = f"{node_dir};{pnpm.parent};{environment.get('PATH', '')}"
        environment["COREPACK_ENABLE_STRICT"] = "0"
        # Vencord's normal source checkout obtains this from `git rev-parse`.
        # The manager deliberately uses a GitHub source archive so end users do
        # not need Git; provide archive metadata instead of invoking Git.
        environment["VENCORD_HASH"] = "vmm-source-archive"
        environment["VENCORD_REMOTE"] = VENCORD_REPOSITORY
        ready_marker = workspace / ".vmm-dependencies-ready"
        if not ready_marker.is_file():
            self._run([str(pnpm), "install", "--frozen-lockfile"], workspace, environment, self.log)
            ready_marker.write_text(str(time.time()), encoding="utf-8")
        self._run([str(pnpm), "build"], workspace, environment, self.log)

        patcher = workspace / "dist" / "patcher.js"
        if not patcher.is_file():
            raise ManagerError("patcher_missing")
        return patcher

    @staticmethod
    def find_discord_targets() -> dict[str, Path]:
        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        targets: dict[str, Path] = {}
        for channel, directory in (("Discord", "Discord"), ("Discord PTB", "DiscordPTB"), ("Discord Canary", "DiscordCanary")):
            base = local / directory
            resources = [path / "resources" for path in base.glob("app-*") if (path / "resources").is_dir()]
            if resources:
                targets[channel] = sorted(resources, key=lambda path: path.parent.name, reverse=True)[0]
        return targets

    def install_wrapper(self, resources: Path, patcher: Path) -> None:
        app_asar = resources / "app.asar"
        backup = resources / "app.asar.vmm-backup"
        if not app_asar.is_file():
            raise ManagerError("asar_missing", path=app_asar)
        if not backup.exists():
            shutil.copy2(app_asar, backup)
            self.log(message("backup_created", name=backup.name))

        self._write_asar_wrapper(app_asar, patcher)
        self.log(message("wrapper_installed"))

    @staticmethod
    def _write_asar_wrapper(destination: Path, patcher: Path) -> None:
        """Write the minimal valid ASAR archive Electron expects in resources.

        Discord's application loader reads resources/app.asar as an ASAR archive,
        not as a JavaScript file. Its archive needs only package.json and an
        index.js which delegates to the manager's built Vencord patcher.
        """
        index = f"// Installed by {APP_NAME}.\nrequire({json.dumps(str(patcher.resolve()))});\n".encode("utf-8")
        package = b'{"name":"discord","main":"index.js"}'
        header = json.dumps({
            "files": {
                "index.js": {"size": len(index), "offset": "0"},
                "package.json": {"size": len(package), "offset": str(len(index))}
            }
        }, separators=(",", ":")).encode("utf-8")

        # ASAR uses Chromium's Pickle header: payload length followed by the
        # nested header sizes, then the JSON header and file payloads.
        prefix = struct.pack("<4I", 4, len(header) + 8, len(header) + 4, len(header))
        temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_bytes(prefix + header + index + package)
            for _ in range(20):
                try:
                    temporary.replace(destination)
                    return
                except PermissionError:
                    time.sleep(0.5)
            raise ManagerError("asar_busy")
        finally:
            temporary.unlink(missing_ok=True)

    def restore(self, resources: Path) -> None:
        app_asar = resources / "app.asar"
        backup = resources / "app.asar.vmm-backup"
        if not backup.is_file():
            raise ManagerError("backup_missing")
        shutil.copy2(backup, app_asar)
        self.log(message("wrapper_restored"))


class ModManagerApp:
    def __init__(self) -> None:
        self.window = Tk()
        self.window.title(APP_NAME)
        self.window.minsize(760, 560)
        self.settings = ManagerSettings()
        self.language = self.settings.load_language()
        self.language_display_var = StringVar(value=LANGUAGE_NAMES[self.language])
        self.manager = ModManager(self.log)
        self.plugins: list[PluginRecord] = self.manager.load_plugins()
        self.plugin_vars: dict[str, BooleanVar] = {}
        self.installed_userplugins: list[InstalledUserPlugin] = []
        self.log_entries: list[str | LocalizedMessage] = []
        self.busy = False

        self.target_var = StringVar()
        self.targets: dict[str, Path] = {}
        self._build_ui()
        self.refresh_targets()
        self.refresh_plugins()
        self.refresh_userplugins()
        self.log(message("trust_sources"))

    def tr(self, key: str, **values: object) -> str:
        return text_for(self.language, key, **values)

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.window, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Vencord Mod Manager", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        language_row = ttk.Frame(frame)
        language_row.pack(fill="x", pady=(4, 0))
        self.language_label = ttk.Label(language_row)
        self.language_label.pack(side="left")
        self.language_box = ttk.Combobox(
            language_row,
            textvariable=self.language_display_var,
            values=tuple(LANGUAGE_NAMES.values()),
            state="readonly",
            width=12
        )
        self.language_box.pack(side="left", padx=(8, 0))
        self.language_box.bind("<<ComboboxSelected>>", self._change_language)

        self.warning_label = ttk.Label(
            frame,
            foreground="#c98a00",
            wraplength=720
        )
        self.warning_label.pack(anchor="w", pady=(4, 12))

        target_row = ttk.Frame(frame)
        target_row.pack(fill="x", pady=(0, 8))
        ttk.Label(target_row, text="Discord:").pack(side="left")
        self.target_box = ttk.Combobox(target_row, textvariable=self.target_var, state="readonly", width=52)
        self.target_box.pack(side="left", padx=8, fill="x", expand=True)
        self.refresh_targets_button = ttk.Button(target_row, command=self.refresh_targets)
        self.refresh_targets_button.pack(side="left")

        action_row = ttk.Frame(frame)
        action_row.pack(fill="x", pady=(0, 8))
        self.add_zip_button = ttk.Button(action_row, command=self.add_zip)
        self.add_zip_button.pack(side="left")
        self.add_github_button = ttk.Button(action_row, command=self.add_github)
        self.add_github_button.pack(side="left", padx=6)
        self.remove_button = ttk.Button(action_row, command=self.remove_selected)
        self.remove_button.pack(side="left")
        self.install_button = ttk.Button(action_row, command=self.install)
        self.install_button.pack(side="right")
        self.restore_button = ttk.Button(action_row, command=self.restore)
        self.restore_button.pack(side="right", padx=6)
        self.refresh_userplugins_button = ttk.Button(action_row, command=self.refresh_userplugins)
        self.refresh_userplugins_button.pack(side="right", padx=6)

        self.plugin_frame = ttk.LabelFrame(frame, padding=8)
        self.plugin_frame.pack(fill="x")

        self.userplugins_frame = ttk.LabelFrame(frame, padding=8)
        self.userplugins_frame.pack(fill="both", expand=True, pady=(10, 0))

        self.log_frame = ttk.LabelFrame(frame, padding=6)
        self.log_frame.pack(fill="both", expand=True, pady=(10, 0))
        self.log_box = ScrolledText(self.log_frame, height=10, state="disabled", wrap="word")
        self.log_box.pack(fill="both", expand=True)
        self._refresh_texts()

    def _refresh_texts(self) -> None:
        self.language_label.configure(text=self.tr("language"))
        self.warning_label.configure(text=self.tr("source_warning"))
        self.refresh_targets_button.configure(text=self.tr("refresh"))
        self.add_zip_button.configure(text=self.tr("add_zip"))
        self.add_github_button.configure(text=self.tr("add_github"))
        self.remove_button.configure(text=self.tr("remove_from_manager"))
        self.install_button.configure(text=self.tr("build_and_install"))
        self.restore_button.configure(text=self.tr("restore_backup"))
        self.refresh_userplugins_button.configure(text=self.tr("check_userplugins"))
        self.plugin_frame.configure(text=self.tr("plugins_heading"))
        self.userplugins_frame.configure(text=self.tr("userplugins_heading"))
        self.log_frame.configure(text=self.tr("log_heading"))
        self.refresh_plugins()
        self.refresh_userplugins()
        self._refresh_log()

    def _change_language(self, _event: object = None) -> None:
        reverse_names = {name: code for code, name in LANGUAGE_NAMES.items()}
        language = reverse_names.get(self.language_display_var.get(), DEFAULT_LANGUAGE)
        if language == self.language:
            return
        self.language = language
        self.settings.save_language(language)
        self._refresh_texts()
        self.log(message("language_changed", language=LANGUAGE_NAMES[language]))

    def _format_log_entry(self, entry: str | LocalizedMessage) -> str:
        if isinstance(entry, LocalizedMessage):
            return self.tr(entry.key, **entry.values)
        return entry

    def _refresh_log(self) -> None:
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        for entry in self.log_entries:
            self.log_box.insert("end", self._format_log_entry(entry) + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def log(self, entry: str | LocalizedMessage) -> None:
        def append() -> None:
            self.log_entries.append(entry)
            self.log_box.configure(state="normal")
            self.log_box.insert("end", self._format_log_entry(entry) + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")

        self.window.after(0, append)

    def refresh_targets(self) -> None:
        self.targets = self.manager.find_discord_targets()
        values = list(self.targets)
        self.target_box["values"] = values
        if values and self.target_var.get() not in self.targets:
            self.target_var.set(values[0])
        if not values:
            self.target_var.set("")
            self.log(message("discord_not_found"))

    def refresh_plugins(self) -> None:
        for child in self.plugin_frame.winfo_children():
            child.destroy()
        self.plugin_vars.clear()
        if not self.plugins:
            ttk.Label(self.plugin_frame, text=self.tr("no_plugins")).pack(anchor="w")
            return
        for plugin in self.plugins:
            row = ttk.Frame(self.plugin_frame)
            row.pack(fill="x", pady=2)
            enabled = BooleanVar(value=plugin.enabled)
            self.plugin_vars[plugin.plugin_id] = enabled
            ttk.Checkbutton(row, variable=enabled, command=self.persist_enabled).pack(side="left")
            ttk.Label(row, text=plugin.name, width=28).pack(side="left")
            source = self.tr("source_bundled") if plugin.source_type == "bundled" else (
                self.tr("source_recovered") if plugin.source_type == "recovered" else plugin.source
            )
            ttk.Label(row, text=source, foreground="#777777").pack(side="left", fill="x", expand=True)

    def refresh_userplugins(self) -> None:
        for child in self.userplugins_frame.winfo_children():
            child.destroy()
        self.installed_userplugins = self.manager.scan_userplugins()
        if not self.installed_userplugins:
            ttk.Label(self.userplugins_frame, text=self.tr("no_userplugins")).pack(anchor="w")
            return

        for installed in self.installed_userplugins:
            row = ttk.Frame(self.userplugins_frame)
            row.pack(fill="x", pady=2)
            source = self.tr("managed_by_manager") if installed.managed_plugin_id else self.tr("added_manually")
            ttk.Label(row, text=installed.folder_name, width=32).pack(side="left")
            ttk.Label(row, text=source, foreground="#777777").pack(side="left", fill="x", expand=True)
            ttk.Button(
                row,
                text=self.tr("delete_files"),
                command=lambda item=installed: self.delete_userplugin_folder(item)
            ).pack(side="right")

    def persist_enabled(self) -> None:
        for plugin in self.plugins:
            plugin.enabled = self.plugin_vars[plugin.plugin_id].get()
        self.manager.save_plugins(self.plugins)

    def _run_background(self, work: Callable[[], None]) -> None:
        if self.busy:
            return
        self.busy = True
        for button in self._busy_controls():
            button.configure(state="disabled")

        def runner() -> None:
            try:
                work()
            except ManagerError as error:
                detail = self.tr(error.key, **error.values)
                self.log(message("error_prefix", detail=detail))
                self.window.after(0, lambda detail=detail: messagebox.showerror(APP_NAME, detail))
            except Exception as error:  # Keep unexpected errors visible without losing the GUI.
                detail = self.tr("unexpected_error", detail=error)
                self.log(detail)
                self.window.after(0, lambda detail=detail: messagebox.showerror(APP_NAME, detail))
            finally:
                self.busy = False
                self.window.after(0, self._finish_background)

        threading.Thread(target=runner, daemon=True).start()

    def _finish_background(self) -> None:
        for button in self._busy_controls():
            button.configure(state="readonly" if button is self.language_box else "normal")
        self.refresh_plugins()
        self.refresh_userplugins()

    def _busy_controls(self) -> tuple[ttk.Widget, ...]:
        return (
            self.language_box,
            self.refresh_targets_button,
            self.add_zip_button,
            self.add_github_button,
            self.remove_button,
            self.install_button,
            self.restore_button,
            self.refresh_userplugins_button
        )

    def add_zip(self) -> None:
        filename = filedialog.askopenfilename(
            title=self.tr("choose_zip"),
            filetypes=[(self.tr("zip_archive"), "*.zip")]
        )
        if not filename:
            return

        def work() -> None:
            plugin = self.manager.import_zip(Path(filename))
            self.plugins.append(plugin)
            self.manager.save_plugins(self.plugins)
            self.log(message("plugin_added", name=plugin.name))

        self._run_background(work)

    def add_github(self) -> None:
        url = simpledialog.askstring(APP_NAME, self.tr("github_prompt"), parent=self.window)
        if not url:
            return

        def work() -> None:
            plugin = self.manager.import_github(url)
            self.plugins.append(plugin)
            self.manager.save_plugins(self.plugins)
            self.log(message("plugin_added", name=plugin.name))

        self._run_background(work)

    def remove_selected(self) -> None:
        selected = [plugin for plugin in self.plugins if self.plugin_vars.get(plugin.plugin_id, BooleanVar()).get()]
        if not selected:
            messagebox.showinfo(APP_NAME, self.tr("no_plugin_selected"))
            return
        if not messagebox.askyesno(APP_NAME, self.tr("remove_confirmation", count=len(selected))):
            return

        def work() -> None:
            for plugin in selected:
                self.manager.remove_plugin(plugin)
                self.plugins.remove(plugin)
                self.log(message("plugin_removed", name=plugin.name))
            self.manager.save_plugins(self.plugins)

        self._run_background(work)

    def delete_userplugin_folder(self, installed: InstalledUserPlugin) -> None:
        if not messagebox.askyesno(
            APP_NAME,
            self.tr("delete_folder_confirmation", folder=installed.folder_name)
        ):
            return

        def work() -> None:
            managed_id = self.manager.delete_userplugin_folder(installed.folder_name)
            if managed_id:
                plugin = next((item for item in self.plugins if item.plugin_id == managed_id), None)
                if plugin:
                    plugin.enabled = False
            self.manager.save_plugins(self.plugins)
            self.log(message("userplugin_deleted", folder=installed.folder_name))

        self._run_background(work)

    def _selected_resources(self) -> Path | None:
        target = self.target_var.get()
        if target not in self.targets:
            messagebox.showerror(APP_NAME, self.tr("select_discord"))
            return None
        return self.targets[target]

    @staticmethod
    def _close_discord() -> None:
        subprocess.run(
            ["taskkill", "/F", "/T", "/IM", "Discord.exe"],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            process_list = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Discord.exe", "/NH"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW
            ).stdout.lower()
            if not process_list.startswith("discord.exe"):
                return
            time.sleep(0.5)
        raise ManagerError("discord_close_timeout")

    def install(self) -> None:
        resources = self._selected_resources()
        if resources is None:
            return
        self.persist_enabled()
        if not messagebox.askyesno(
            APP_NAME,
            self.tr("build_confirmation")
        ):
            return

        def work() -> None:
            patcher = self.manager.build(self.plugins)
            self.log(message("build_ready"))
            self._close_discord()
            self.manager.install_wrapper(resources, patcher)
            self.log(message("installation_done"))

        self._run_background(work)

    def restore(self) -> None:
        resources = self._selected_resources()
        if resources is None:
            return
        if not messagebox.askyesno(APP_NAME, self.tr("restore_confirmation")):
            return

        def work() -> None:
            self._close_discord()
            self.manager.restore(resources)
            self.log(message("restoration_done"))

        self._run_background(work)

    def run(self) -> None:
        self.window.mainloop()


if __name__ == "__main__":
    ModManagerApp().run()
