# Vencord Mod Manager 1.5

Open-source Windows GUI manager for Vencord user plugins. The executable stays small: on first use it downloads Vencord source, portable Node.js, and pnpm into `%LOCALAPPDATA%\VencordModManager`.

## Features

- Add a Vencord user plugin from a ZIP archive or a public GitHub repository.
- Enable chosen plugins and build them into Vencord.
- Includes the full source for VoiceStreaks as an optional, disabled-by-default plugin.
- Scans the real `src/userplugins` directory and distinguishes manually added folders from manager-owned folders.
- Physically deletes a selected user-plugin folder only after confirmation.
- Preserves manually added user plugins while rebuilding manager-owned plugins.
- Backs up Discord's `resources\app.asar` before replacing it with a valid ASAR wrapper.
- Restores that backup on request.
- Switches the complete manager interface between English (default) and Russian; the choice is saved locally.

## Use

1. Run `VencordModManager.exe`.
2. Tick VoiceStreaks or add other source plugins.
3. Select Discord and choose **Build and install** (or switch the interface to Russian first).
4. The manager builds first, closes Discord only after a successful build, creates a backup, then installs the wrapper.
5. Start Discord normally.

The **Actual src/userplugins folders** section operates on real folders in the managed Vencord source cache. **Delete files** removes the selected folder; choose **Build and install** afterwards to make Discord use the new build.

## Build from source

Requirements: Windows and Python 3.11+.

```powershell
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

The script repacks `bundled_plugins\voiceStreaks` from visible source files, installs PyInstaller from `requirements-build.txt`, and writes `dist\VencordModManager-1.5.exe`.

## Security

Plugins execute code inside modified Discord. Review every ZIP or GitHub repository before installing it. The generated executable is not code-signed; a new unsigned program that modifies Discord may trigger antivirus heuristics. This project does not attempt to bypass those checks.

## License

This project and bundled VoiceStreaks are distributed under GPL-3.0-or-later. Vencord itself is downloaded from its official public repository at build time; it is not included in this source release.
