#ifndef AppSourceDir
  #define AppSourceDir SourcePath + "dist\CounterMiao"
#endif
#ifndef InstallerOutputDir
  #define InstallerOutputDir SourcePath + "installer-output"
#endif

[Setup]
AppId={{9043A588-454A-41EB-A1BE-8619D0D5A2D6}
AppName=CounterMiao
AppVersion=4.3
AppVerName=CounterMiao 4.3
AppPublisher=CounterMiao
AppPublisherURL=https://github.com/ZHC00813/CounterMiao
AppSupportURL=https://github.com/ZHC00813/CounterMiao/issues
AppUpdatesURL=https://github.com/ZHC00813/CounterMiao/releases
DefaultDirName={localappdata}\Programs\CounterMiao
DefaultGroupName=CounterMiao
DisableDirPage=no
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.22000
OutputDir={#InstallerOutputDir}
OutputBaseFilename=CounterMiao-4.3-Setup
SetupIconFile=CounterMiao.ico
UninstallDisplayIcon={app}\CounterMiao.exe
VersionInfoVersion=4.3.0.0
VersionInfoProductVersion=4.3.0.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=no
RestartApplications=no
Uninstallable=yes

[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
chinesesimplified.DesktopShortcut=创建桌面快捷方式
english.DesktopShortcut=Create a desktop shortcut
chinesesimplified.LaunchApp=启动 CounterMiao
english.LaunchApp=Launch CounterMiao

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopShortcut}"; Flags: unchecked

[Files]
Source: "{#AppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\CounterMiao\CounterMiao"; Filename: "{app}\CounterMiao.exe"; WorkingDir: "{app}"
Name: "{userdesktop}\CounterMiao"; Filename: "{app}\CounterMiao.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\CounterMiao.exe"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent
