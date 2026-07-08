{
  description = "DeepSight chess analysis app";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs, ... }:
    let
      systems = [ "x86_64-linux" ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      packages = forAllSystems (
        system:
        let
          pkgs = import nixpkgs { inherit system; };
          lib = pkgs.lib;

          pname = "deepsight";
          version = "0.1.0";
          appSrc = lib.cleanSourceWith {
            src = ./.;
            filter =
              path: type:
              let
                relPath = lib.removePrefix (toString ./. + "/") (toString path);
              in
              !(relPath == "Engines"
                || lib.hasPrefix "Engines/" relPath
                || relPath == "result"
                || lib.hasPrefix "result/" relPath
                || lib.hasPrefix "result-" relPath);
          };

          emberVersion = "1.1.2";
          stockfishRelease = "sf_18";
          pythonWindowsVersion = "3.11.9";

          pythonEnv = pkgs.python3.withPackages (ps: [
            ps.pyqt6
            ps.chess
          ]);

          stockfishLinux = pkgs.fetchurl {
            url = "https://github.com/official-stockfish/Stockfish/releases/download/${stockfishRelease}/stockfish-ubuntu-x86-64.tar";
            hash = "sha256-XG84sCpNpfP/52PyfabD50Puvv2StQyzZhYjuWaWrf8=";
          };

          stockfishWindows = pkgs.fetchurl {
            url = "https://github.com/official-stockfish/Stockfish/releases/download/${stockfishRelease}/stockfish-windows-x86-64.zip";
            hash = "sha256-QMyXWBfn7uJwsD81SBDSCVbfVlQg0yD23TfUVNyBoTk=";
          };

          emberWindows = pkgs.fetchurl {
            url = "https://github.com/ExxDreamerCode/Ember/releases/download/V${emberVersion}/ember.exe";
            hash = "sha256-4itVMaoqiEDoC5/kveeg5c5o9JvHNiKT8zo46FfcIVQ=";
          };

          pythonWindows = pkgs.fetchurl {
            url = "https://www.python.org/ftp/python/${pythonWindowsVersion}/python-${pythonWindowsVersion}-embed-amd64.zip";
            hash = "sha256-AJ1r9+Oy3co9eE+gn5D+VDNtW2Dw4PMFw39AC/g8/Ts=";
          };

          pyqt6Wheel = pkgs.fetchurl {
            url = "https://files.pythonhosted.org/packages/6f/85/dd9f03d78d87460e109e0121cd6201c5802bdd655656bf2780e964870fea/pyqt6-6.11.0-cp310-abi3-win_amd64.whl";
            hash = "sha256-vRG0WcVNygaOmIpCz4ODAzNPDUQbnRbZKuZxn8taxro=";
          };

          pyqt6Qt6Wheel = pkgs.fetchurl {
            url = "https://files.pythonhosted.org/packages/fa/f1/70e83c23bf897c7f5025aa100482f482038ef70232dc27b407659d941fbf/pyqt6_qt6-6.11.1-py3-none-win_amd64.whl";
            hash = "sha256-dIbIBRLoI/LTCH5n+FTwVWs0X0NoBAqFPI3E0w/T/mk=";
          };

          pyqt6SipWheel = pkgs.fetchurl {
            url = "https://files.pythonhosted.org/packages/4a/d6/c40e8ae38a6e2bce9e837b64688f55746bfdad1aa557eb733fb5e90edd7c/pyqt6_sip-13.11.1-cp311-cp311-win_amd64.whl";
            hash = "sha256-mNuO03zwgTDh7nS4/0emv7jDzf6CYxBZemMKUOR/7tw=";
          };

          chessSdist = pkgs.fetchurl {
            url = "https://files.pythonhosted.org/packages/93/09/7d04d7581ae3bb8b598017941781bceb7959dd1b13e3ebf7b6a2cd843bc9/chess-1.11.2.tar.gz";
            hash = "sha256-qLQ+Vnj9swAGlb2qVzEXrWg3YeXKOOWRxIJuum0luzk=";
          };

          emberNative = pkgs.rustPlatform.buildRustPackage {
            pname = "ember";
            version = emberVersion;

            src = pkgs.fetchFromGitHub {
              owner = "ExxDreamerCode";
              repo = "Ember";
              rev = "bd752d9ed530d3162e32b1c13a8ad9fc779f31b4";
              hash = "sha256-7SsrMXXAG2QAJNaq5zi5P6jAtuU5GzffToJOVPv7PsQ=";
            };

            cargoHash = "sha256-cacnWEtZZIjr3cpwFbNx8kj7hTqO4yc4FgXfn/6rEVs=";
            doCheck = false;
          };

          nativeEngines = pkgs.runCommand "deepsight-engines-${version}"
            {
              nativeBuildInputs = [ pkgs.gnutar ];
            }
            ''
              mkdir -p "$out/Engines"
              cp ${emberNative}/bin/ember "$out/Engines/ember"
              tar -xf ${stockfishLinux}
              cp stockfish/stockfish-ubuntu-x86-64 "$out/Engines/stockfish"
              chmod 0755 "$out"/Engines/*
            '';

          installEnginesPs1 = pkgs.writeText "install-engines.ps1" ''
            $ErrorActionPreference = 'Stop'

            $Root = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
            $Engines = Join-Path $Root 'Engines'
            New-Item -ItemType Directory -Force -Path $Engines | Out-Null

            function Get-PinnedFile {
              param(
                [string] $Url,
                [string] $Output,
                [string] $Sha256
              )

              Invoke-WebRequest -Uri $Url -OutFile $Output -UseBasicParsing
              $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Output).Hash.ToLowerInvariant()
              if ($actual -ne $Sha256.ToLowerInvariant()) {
                throw "Hash mismatch for $Output. Expected $Sha256, got $actual."
              }
            }

            Get-PinnedFile `
              -Url 'https://github.com/ExxDreamerCode/Ember/releases/download/V${emberVersion}/ember.exe' `
              -Output (Join-Path $Engines 'ember.exe') `
              -Sha256 'e22b5531aa2a8840e80b9fe4bde7a0e5ce68f49bc7362293f33a38e857dc2154'

            $stockfishZip = Join-Path $env:TEMP 'deepsight-stockfish-windows-x86-64.zip'
            $stockfishExtract = Join-Path $env:TEMP 'deepsight-stockfish-windows-x86-64'
            Remove-Item -LiteralPath $stockfishExtract -Recurse -Force -ErrorAction SilentlyContinue

            Get-PinnedFile `
              -Url 'https://github.com/official-stockfish/Stockfish/releases/download/${stockfishRelease}/stockfish-windows-x86-64.zip' `
              -Output $stockfishZip `
              -Sha256 '40cc975817e7eee270b03f354810d20956df565420d320f6dd37d454dc81a139'

            Expand-Archive -LiteralPath $stockfishZip -DestinationPath $stockfishExtract -Force
            Copy-Item `
              -LiteralPath (Join-Path $stockfishExtract 'stockfish\stockfish-windows-x86-64.exe') `
              -Destination (Join-Path $Engines 'stockfish-windows-x86-64.exe') `
              -Force
          '';

          launcherSource = pkgs.writeText "deepsight-launcher.c" ''
            #define UNICODE
            #define _UNICODE
            #include <windows.h>
            #include <wchar.h>
            #include <stdio.h>

            int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR commandLine, int showCommand) {
                (void)instance;
                (void)previous;
                (void)commandLine;
                (void)showCommand;

                wchar_t root[32768];
                DWORD length = GetModuleFileNameW(NULL, root, 32768);
                if (length == 0 || length >= 32768) {
                    MessageBoxW(NULL, L"Could not resolve DeepSight.exe location.", L"DeepSight", MB_ICONERROR);
                    return 1;
                }

                wchar_t *lastSlash = wcsrchr(root, L'\\');
                if (lastSlash == NULL) {
                    MessageBoxW(NULL, L"Could not resolve DeepSight installation directory.", L"DeepSight", MB_ICONERROR);
                    return 1;
                }
                *lastSlash = L'\0';

                wchar_t python[32768];
                wchar_t script[32768];
                wchar_t command[32768 * 2];

                swprintf(python, 32768, L"%ls\\pythonw.exe", root);
                swprintf(script, 32768, L"%ls\\main.py", root);
                swprintf(command, 32768 * 2, L"\"%ls\" \"%ls\"", python, script);

                STARTUPINFOW startup;
                PROCESS_INFORMATION process;
                ZeroMemory(&startup, sizeof(startup));
                ZeroMemory(&process, sizeof(process));
                startup.cb = sizeof(startup);

                if (!CreateProcessW(python, command, NULL, NULL, FALSE, 0, NULL, root, &startup, &process)) {
                    MessageBoxW(NULL, L"Could not start the bundled Python runtime.", L"DeepSight", MB_ICONERROR);
                    return 1;
                }

                CloseHandle(process.hThread);
                CloseHandle(process.hProcess);
                return 0;
            }
          '';

          windowsApp =
            { includeEngines }:
            pkgs.stdenvNoCC.mkDerivation {
              pname = "${pname}-windows-tree${lib.optionalString (!includeEngines) "-no-engines"}";
              inherit version;
              src = appSrc;

              nativeBuildInputs = [
                pkgs.gnutar
                pkgs.unzip
                pkgs.pkgsCross.mingwW64.stdenv.cc
              ];

              dontBuild = true;

              installPhase = ''
                runHook preInstall

                mkdir -p "$out/Lib/site-packages"
                unzip -q ${pythonWindows} -d "$out"
                chmod -R u+w "$out"

                cat > "$out/python311._pth" <<'EOF'
                python311.zip
                .
                Lib/site-packages
                import site
                EOF

                unzip -q ${pyqt6Wheel} -d "$out/Lib/site-packages"
                unzip -q ${pyqt6Qt6Wheel} -d "$out/Lib/site-packages"
                unzip -q ${pyqt6SipWheel} -d "$out/Lib/site-packages"

                mkdir chess-src
                tar -xzf ${chessSdist} -C chess-src
                cp -R chess-src/chess-1.11.2/chess "$out/Lib/site-packages/"

                cp -R main.py deepsight Images Books LICENSE README.md "$out/"
                cp ${installEnginesPs1} "$out/install-engines.ps1"

                x86_64-w64-mingw32-gcc \
                  -Os \
                  -municode \
                  -mwindows \
                  -static \
                  -static-libgcc \
                  ${launcherSource} \
                  -o "$out/DeepSight.exe"

                ${lib.optionalString includeEngines ''
                  mkdir -p "$out/Engines"
                  cp ${emberWindows} "$out/Engines/ember.exe"
                  unzip -q ${stockfishWindows} -d stockfish-windows
                  cp stockfish-windows/stockfish/stockfish-windows-x86-64.exe \
                    "$out/Engines/stockfish-windows-x86-64.exe"
                ''}

                find "$out" -type d -name __pycache__ -prune -exec rm -rf {} +

                runHook postInstall
              '';
            };

          windowsAppWithEngines = windowsApp { includeEngines = true; };
          windowsAppNoEngines = windowsApp { includeEngines = false; };

          windowsArchive = pkgs.stdenvNoCC.mkDerivation {
            pname = "${pname}-windows";
            inherit version;
            nativeBuildInputs = [ pkgs.zip ];
            dontUnpack = true;
            installPhase = ''
              runHook preInstall

              mkdir -p "$out"
              cp -R ${windowsAppWithEngines} DeepSight
              chmod -R u+w DeepSight
              zip -qr "$out/DeepSight-${version}-windows-x86_64.zip" DeepSight

              runHook postInstall
            '';
          };

          windowsInstaller = pkgs.stdenvNoCC.mkDerivation {
            pname = "${pname}-windows-installer";
            inherit version;
            nativeBuildInputs = [ pkgs.nsis ];
            dontUnpack = true;
            installPhase = ''
              runHook preInstall

              cat > installer.nsi <<'EOF'
              Unicode true
              !include "MUI2.nsh"
              !include "LogicLib.nsh"

              Name "DeepSight"
              OutFile "DeepSight-${version}-setup.exe"
              InstallDir "$LOCALAPPDATA\DeepSight"
              RequestExecutionLevel user
              SetCompressor /SOLID lzma

              !insertmacro MUI_PAGE_DIRECTORY
              !insertmacro MUI_PAGE_INSTFILES
              !insertmacro MUI_UNPAGE_CONFIRM
              !insertmacro MUI_UNPAGE_INSTFILES
              !insertmacro MUI_LANGUAGE "English"

              Section "Install"
                SetShellVarContext current
                SetOutPath "$INSTDIR"
                File /r "${windowsAppNoEngines}/*"

                DetailPrint "Downloading chess engines..."
                nsExec::ExecToLog '"$SYSDIR\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\install-engines.ps1"'
                Pop $0
                ''${If} $0 != 0
                  MessageBox MB_ICONSTOP "Failed to download the bundled engines. Check your network connection and run install-engines.ps1 from the installation directory, or use the portable Windows archive."
                  Abort
                ''${EndIf}

                WriteUninstaller "$INSTDIR\Uninstall.exe"
                CreateDirectory "$SMPROGRAMS\DeepSight"
                CreateShortcut "$SMPROGRAMS\DeepSight\DeepSight.lnk" "$INSTDIR\DeepSight.exe"
              SectionEnd

              Section "Uninstall"
                SetShellVarContext current
                Delete "$SMPROGRAMS\DeepSight\DeepSight.lnk"
                RMDir "$SMPROGRAMS\DeepSight"
                RMDir /r "$INSTDIR"
              SectionEnd
              EOF

              makensis installer.nsi
              mkdir -p "$out"
              cp "DeepSight-${version}-setup.exe" "$out/"

              runHook postInstall
            '';
          };

          deepsight = pkgs.stdenvNoCC.mkDerivation {
            inherit pname version;
            src = appSrc;

            nativeBuildInputs = [
              pkgs.makeWrapper
              pkgs.qt6.wrapQtAppsHook
            ];

            buildInputs = [ pkgs.qt6.qtbase ];
            dontBuild = true;

            installPhase = ''
              runHook preInstall

              mkdir -p "$out/bin" "$out/share/deepsight"
              cp -R main.py deepsight Images Books LICENSE README.md "$out/share/deepsight/"
              cp -R ${nativeEngines}/Engines "$out/share/deepsight/"

              makeWrapper ${pythonEnv}/bin/python "$out/bin/deepsight" \
                --add-flags "$out/share/deepsight/main.py" \
                --set DEEPSIGHT_DATA_DIR "$out/share/deepsight"

              runHook postInstall
            '';
          };
        in
        {
          default = deepsight;
          inherit deepsight;
          engines = nativeEngines;
          windows = windowsArchive;
          "windows-installer" = windowsInstaller;
        }
      );

      apps = forAllSystems (
        system:
        let
          packages = self.packages.${system};
        in
        {
          default = {
            type = "app";
            program = "${packages.default}/bin/deepsight";
          };
        }
      );
    };
}
