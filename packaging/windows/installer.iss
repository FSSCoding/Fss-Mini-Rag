; FSS-Mini-RAG Windows Installer (Inno Setup)
; Bundles embedded Python + all dependencies for standalone installation.
;
; Build: iscc packaging\windows\installer.iss
; Requires: Inno Setup 6+ (https://jrsoftware.org/isinfo.php)

#define MyAppName "FSS-Mini-RAG"
#define MyAppVersion GetEnv('FSS_VERSION')
#if MyAppVersion == ""
  #define MyAppVersion "2.3.0"
#endif
#define MyAppPublisher "Fox Software Solutions"
#define MyAppURL "https://github.com/FSSCoding/Fss-Mini-Rag"
#define MyAppExeName "rag-mini-gui.bat"

[Setup]
AppId={{8E2F4A1B-5C3D-4E6F-A8B9-1C2D3E4F5A6B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=..\..\dist
OutputBaseFilename=fss-mini-rag-{#MyAppVersion}-setup
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=..\..\assets\fss-mini-rag.ico
UninstallDisplayIcon={app}\icon.ico
WizardStyle=modern
LicenseFile=..\..\LICENSE
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"
Name: "addtopath"; Description: "Add rag-mini to system PATH"; GroupDescription: "System integration:"; Flags: checkedonce

[Files]
; Embedded Python distribution
Source: "build\python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs

; Application wheel and requirements
Source: "build\wheel\*"; DestDir: "{app}\packages"; Flags: ignoreversion

; Launcher scripts
Source: "build\launchers\rag-mini.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "build\launchers\rag-mini-gui.bat"; DestDir: "{app}"; Flags: ignoreversion

; Icon and assets
Source: "..\..\assets\Fss_Mini_Rag.png"; DestDir: "{app}"; DestName: "icon.png"; Flags: ignoreversion
Source: "..\..\assets\fss-mini-rag.ico"; DestDir: "{app}"; DestName: "icon.ico"; Flags: ignoreversion
Source: "..\..\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{group}\FSS-Mini-RAG"; Filename: "{app}\rag-mini-gui.bat"; IconFilename: "{app}\icon.ico"; Comment: "Launch FSS-Mini-RAG desktop GUI"
Name: "{group}\FSS-Mini-RAG CLI"; Filename: "cmd.exe"; Parameters: "/k ""{app}\rag-mini.bat"" --help"; IconFilename: "{app}\icon.ico"; Comment: "FSS-Mini-RAG command line"
Name: "{group}\Uninstall FSS-Mini-RAG"; Filename: "{uninstallexe}"
Name: "{autodesktop}\FSS-Mini-RAG"; Filename: "{app}\rag-mini-gui.bat"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
; Install packages after files are copied
Filename: "{app}\python\python.exe"; Parameters: "-m pip install --no-warn-script-location --prefix ""{app}\python"" {app}\packages\*.whl"; StatusMsg: "Installing FSS-Mini-RAG packages..."; Flags: runhidden waituntilterminated
; Verify installation
Filename: "{app}\python\python.exe"; Parameters: "-c ""import mini_rag; print('OK')"""; StatusMsg: "Verifying installation..."; Flags: runhidden waituntilterminated

[Registry]
; Add to PATH if requested
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Tasks: addtopath; Check: NeedsAddPath('{app}')

[UninstallDelete]
Type: filesandordirs; Name: "{app}\python\Lib\site-packages"
Type: filesandordirs; Name: "{app}\python\Scripts"

[Code]
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) then
  begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;
