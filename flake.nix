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

          # Bumping any of these pins means updating THIRD_PARTY_NOTICES.md.
          emberVersion = "1.3.1";
          emberRev = "9e015493";
          emberAsset = "ember-${emberVersion}-${emberRev}-linux-amd64";
          stockfishRelease = "sf_18";

          pythonEnv = pkgs.python3.withPackages (ps: [
            ps.pyqt6
            ps.chess
          ]);

          stockfishLinux = pkgs.fetchurl {
            url = "https://github.com/official-stockfish/Stockfish/releases/download/${stockfishRelease}/stockfish-ubuntu-x86-64.tar";
            hash = "sha256-XG84sCpNpfP/52PyfabD50Puvv2StQyzZhYjuWaWrf8=";
          };

          # Like Stockfish, Ember comes from its own release rather than being built here, so the
          # version, the revision in the asset name and the hash are the only things to bump.
          emberLinux = pkgs.fetchurl {
            url = "https://github.com/ExxDreamerCode/Ember/releases/download/V${emberVersion}/${emberAsset}.tar.gz";
            hash = "sha256-fFcTGVTkcrGVvr6pKP+uAq8i/pZsa6IH247HomPdjdE=";
          };

          nativeEngines = pkgs.runCommand "deepsight-engines-${version}"
            {
              nativeBuildInputs = [ pkgs.gnutar ];
            }
            ''
              mkdir -p "$out/Engines"
              tar -xf ${emberLinux}
              cp ${emberAsset}/ember "$out/Engines/ember-${emberVersion}"
              tar -xf ${stockfishLinux}
              cp stockfish/stockfish-ubuntu-x86-64 "$out/Engines/stockfish"
              chmod 0755 "$out"/Engines/*
            '';

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
              cp -R main.py deepsight Images Books LICENSE README.md THIRD_PARTY_NOTICES.md licenses "$out/share/deepsight/"
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
