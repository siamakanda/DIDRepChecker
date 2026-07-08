; Inno Setup installer for DIDRepChecker
; Download from https://jrsoftware.org/isinfo.php

[Setup]
AppName=DIDRepChecker
AppVersion=2.0.0
AppPublisher=DIDRepChecker
DefaultDirName={autopf}\DIDRepChecker
DefaultGroupName=DIDRepChecker
UninstallDisplayIcon={app}\DIDRepChecker.exe
Compression=lzma2
SolidCompression=yes
OutputDir=..\..\dist
OutputBaseFilename=DIDRepChecker-Setup-2.0.0
PrivilegesRequired=lowest

[Files]
Source: "..\..\dist\DIDRepChecker.exe"; DestDir: "{app}"
Source: "..\..\dist\didrepchecker-server.exe"; DestDir: "{app}"
Source: "..\..\config.example.json"; DestDir: "{app}"; DestName: "config.json"; Flags: onlyifdoesntexist

[Icons]
Name: "{group}\DIDRepChecker"; Filename: "{app}\DIDRepChecker.exe"
Name: "{commondesktop}\DIDRepChecker"; Filename: "{app}\DIDRepChecker.exe"
Name: "{group}\Uninstall DIDRepChecker"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\DIDRepChecker.exe"; Description: "Start DIDRepChecker"; Flags: nowait postinstall skipifsilent
