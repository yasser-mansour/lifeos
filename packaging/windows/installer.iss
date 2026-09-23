; Inno Setup script for LIFEOS-Setup-<version>.exe — a normal per-user
; Windows installer (no admin rights required): Start Menu shortcut,
; optional Desktop shortcut, standard uninstall entry. User data lives in
; %LOCALAPPDATA%\LIFEOS (see desktop/windows/lifeos_windows.py), which this
; installer never touches — installing, updating, or uninstalling LIFEOS
; never deletes it.
;
; Build with: iscc packaging\windows\installer.iss
; (after packaging\windows\build_release.ps1 has produced dist\LIFEOS.exe)

#define MyAppName "LIFEOS"
#define MyAppVersion GetEnv("LIFEOS_VERSION")
#if MyAppVersion == ""
  #define MyAppVersion "0.1.0"
#endif
#define MyAppExeName "LIFEOS.exe"

[Setup]
AppId={{6A6E6E9A-6B0C-4C6A-9A0C-9B3F5B8B8B10}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=LIFEOS
DefaultDirName={autopf}\LIFEOS
DefaultGroupName=LIFEOS
DisableProgramGroupPage=yes
; Per-user install (PrivilegesRequired=lowest) — no admin prompt, matching
; "Do not require administrator privileges unless truly necessary."
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=dist
OutputBaseFilename=LIFEOS-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
; No source code license to declare a distribution license for yet — see
; the repository's own LICENSE status. Nothing else in this script implies one.

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\LIFEOS.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: dontcopy external skipifsourcedoesntexist

[Icons]
Name: "{group}\LIFEOS"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall LIFEOS"; Filename: "{uninstallexe}"
Name: "{autodesktop}\LIFEOS"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Open LIFEOS"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Explicitly NOT deleting %LOCALAPPDATA%\LIFEOS — per spec "uninstall
; behavior regarding user data must be explicit and safe" / "do NOT
; silently delete personal LIFEOS data unless the user explicitly chooses
; that." Default uninstall removes only the installed program files above.

[Code]
// WebView2 Runtime check — most Windows 10/11 machines already have it
// (shipped via Windows Update since 2021), but a normal user should never
// have to know what WebView2 is or go troubleshoot it themselves.
function IsWebView2Installed(): Boolean;
var
  Version: String;
begin
  Result :=
    RegQueryStringValue(HKLM64, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) or
    RegQueryStringValue(HKCU, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version);
end;

procedure InstallWebView2();
var
  ResultCode: Integer;
  BootstrapperPath: String;
begin
  ExtractTemporaryFile('MicrosoftEdgeWebview2Setup.exe');
  BootstrapperPath := ExpandConstant('{tmp}\MicrosoftEdgeWebview2Setup.exe');
  if FileExists(BootstrapperPath) then
  begin
    Exec(BootstrapperPath, '/silent /install', '', SW_SHOW, ewWaitUntilTerminated, ResultCode);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and not IsWebView2Installed() then
  begin
    InstallWebView2();
  end;
end;
