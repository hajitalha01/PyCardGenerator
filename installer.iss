; Card Generator — Inno Setup Installer Script
; =============================================
; Build the installer with Inno Setup 6 (https://jrsoftware.org/isinfo.php)
;
; 1. Build the executable:  python -m PyInstaller build.spec
; 2. Compile this script:   iscc installer.iss
;
; Output: dist\CardGenerator_Setup_v1.0.0.exe

#define MyAppName "Card Generator"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "CardGenerator"
#define MyAppURL "https://github.com/example/card-generator"
#define MyAppExeName "CardGenerator.exe"

#define BuildDir "dist"
#define OutputDir "dist"

[Setup]
AppId={{D8F3C1A2-5B7E-4F6D-9A1C-2E8B0D4F7A3E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes

; Output
OutputDir={#OutputDir}
OutputBaseFilename=CardGenerator_Setup_v{#MyAppVersion}

; Icon
SetupIconFile=assets\icons\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Compression
Compression=lzma2/max
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Windows version range
MinVersion=10.0
PrivilegesRequired=admin

; Misc
DisableProgramGroupPage=yes
DisableDirPage=auto
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checkablealone

[Files]
; Main executable and support files (one-folder build)
Source: "{#BuildDir}\CardGenerator.exe"; DestDir: "{app}"; Flags: ignoreversion

; Required runtime directories (created on first launch by the app)
; PyInstaller extracts these into _MEIPASS at runtime

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: postinstall nowait skipifsilent shellexec

[UninstallRun]
; Clean up user data (optional — commented out to preserve data on uninstall)
; Filename: "{cmd}"; Parameters: "/C rmdir /S /Q ""{localappdata}\CardGenerator"""; Flags: runhidden

[UninstallDelete]
; Remove any files the application may have created in its install dir

Type: filesandordirs; Name: "{app}\temp"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\uploads"
Type: filesandordirs; Name: "{app}\database\card_generator.db"

[Code]
function InitializeSetup: Boolean;
begin
  Result := True;
end;
