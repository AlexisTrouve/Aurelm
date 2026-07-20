; Inno Setup script for the Aurelm Windows installer.
;
; WHAT: wraps the bundle produced by scripts/build_distribution.ps1 (Flutter EXE +
; embedded CPython + app/) into a single setup.exe with Start Menu shortcut and a
; proper uninstaller.
;
; WHY per-user (PrivilegesRequired=lowest, installed under LocalAppData):
; installing into Program Files would raise a UAC prompt on every install and
; upgrade, and Arthur is explicitly a zero-maintenance user. Nothing here needs
; machine-wide scope — the app runs as him and writes nothing next to itself.
;
; WHY nothing is deleted on uninstall beyond our own files: the game database and
; the sealed API key live outside the install directory (a user-chosen DB path and
; the Windows credential store). Removing the app must never destroy a campaign.

#define AppName "Aurelm"
#define AppPublisher "Alexi Trouve"
#define AppExeName "aurelm_gui.exe"

; Version and source folder are passed by the build script:
;   ISCC /DAppVersion=0.1.0 /DBundleDir=<path to assembled bundle> installer.iss
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef BundleDir
  #define BundleDir "..\dist\aurelm-windows"
#endif
#ifndef OutDir
  #define OutDir "..\dist"
#endif

[Setup]
; Stable GUID — upgrades replace the previous install instead of stacking copies.
AppId={{7C1B4E2A-9D3F-4A65-B0E7-5F2C8A1D6B34}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#OutDir}
OutputBaseFilename=Aurelm-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Nothing to read before installing an app you were handed directly.
DisableWelcomePage=no
UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\{#AppExeName}

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; The whole assembled bundle: EXE + DLLs + data/ + python/ + app/.
; recursesubdirs is what carries the embedded interpreter and the Python packages.
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; __pycache__ dirs are created by the embedded interpreter AFTER install, so Inno
; does not know about them and would leave the folder behind.
Type: filesandordirs; Name: "{app}\app"
Type: filesandordirs; Name: "{app}\python"
