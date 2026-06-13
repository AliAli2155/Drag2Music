; Drag2Music: Infinity Studio — Inno Setup Script
; Compiler: Inno Setup 6.x
; Output  : dist\Drag2Music_Setup.exe
;
; Build command (run from project root):
;   iscc installer\windows\tunefetch_setup.iss

#define AppName       "Drag2Music: Infinity Studio"
#define AppShortName  "Drag2Music"
#define AppVersion    "1.0.0"
#define AppPublisher  "Ali A."
#define AppURL        "https://github.com/AliAli2155/Drag2Music"
#define AppExeName    "Drag2Music.exe"
#define AppDataFile   ".drag2music_history.json"

[Setup]
; Application identity
AppId={{A3F2E7D1-84C6-4B2A-9F3E-D5C8E2A1B709}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases

; Installation target
DefaultDirName={autopf}\{#AppShortName}
DefaultGroupName={#AppShortName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Output
OutputDir=..\..\dist
OutputBaseFilename=Drag2Music_Setup
SetupIconFile=..\..\Drag2Music.ico

; Compression
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMADictionarySize=262144
LZMANumBlockThreads=4

; UI
WizardStyle=modern
WizardResizable=no
ShowLanguageDialog=auto
DisableWelcomePage=no
DisableDirPage=no
DisableReadyPage=no

; Misc
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=6.1
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}

; --- Self-contained: no Python, no ffmpeg, no yt-dlp required on target machine.
; --- PyInstaller embeds the entire Python runtime + all libraries inside the bundle.
; --- ffmpeg.exe is bundled at: {app}\ffmpeg_bins\windows\ffmpeg.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "turkish";  MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon";    Description: "{cm:CreateDesktopIcon}";    GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main application directory (entire dist\Drag2Music\ tree)
Source: "..\..\dist\Drag2Music\*";  DestDir: "{app}";  Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu
Name: "{autoprograms}\{#AppShortName}";         Filename: "{app}\{#AppExeName}";  WorkingDir: "{app}";  IconFilename: "{app}\{#AppExeName}";  Comment: "{#AppName}"
; Desktop (optional task)
Name: "{autodesktop}\{#AppShortName}";           Filename: "{app}\{#AppExeName}";  WorkingDir: "{app}";  Tasks: desktopicon;  Comment: "{#AppName}"
; Quick Launch (Windows XP/Vista)
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#AppShortName}";  Filename: "{app}\{#AppExeName}";  Tasks: quicklaunchicon

[Run]
; Offer to launch after installation
Filename: "{app}\{#AppExeName}";  Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}";  Flags: nowait postinstall skipifsilent runascurrentuser

[UninstallRun]
; Nothing extra to run on uninstall

[UninstallDelete]
; Clean up the app-data history file on uninstall (~/.drag2music_history.json)
Type: files;        Name: "{userdocs}\..\{#AppDataFile}"
; Remove the temp preview file if leftover
Type: filesandordirs; Name: "{userdocs}\..\tf_preview*"

[Code]
// ── MSVC Runtime check ────────────────────────────────────────────────────────
// PyInstaller bundles most DLLs, but on rare old/minimal Windows installs the
// Visual C++ 2015-2022 runtime might be missing.  We check and warn the user;
// the app will still attempt to run — most of the time it works fine.
function VCRedistInstalled: Boolean;
var
  RegKey:  String;
  Version: String;
begin
  // Check for VC++ 2015-2022 x64 Redistributable (14.x = 2015 through 2022)
  RegKey := 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64';
  Result := RegQueryStringValue(HKLM64, RegKey, 'Version', Version);
  if not Result then
    Result := RegQueryStringValue(HKLM, RegKey, 'Version', Version);
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  // Non-blocking advisory: installer continues regardless
  if not VCRedistInstalled then begin
    MsgBox(
      'Note: The Visual C++ 2015-2022 Runtime was not detected on this PC.' + #13#10 +
      'Drag2Music bundles all required files and will likely work fine.' + #13#10 +
      'If the app does not start, install the free runtime from microsoft.com/en-us/download (search: vc_redist.x64.exe).',
      mbInformation, MB_OK);
  end;
end;
