# Motorola Android 17 UI Port Kit — OnePlus 9R / Infinity-X

This starter project inventories an **already extracted** Motorola Android dump and optionally packages explicitly approved APKs into a test-only Magisk/KernelSU-style overlay.

Target: Infinity-X Android 17, OnePlus 9R (`lemonades`, SM8250).

## 1. Put your extracted dump in the repository

Place the extracted partition directories here, preserving the original layout:

```text
motorola_dump/
├── system/
├── product/
├── system_ext/
├── vendor/
└── odm/
```

The dump may contain only some of those partitions. Preserve the paths as they appear in your extraction. Do not rename all files into a single APK folder: original partition paths are useful for analysis.

**Privacy/licensing:** a full proprietary dump may be large and subject to redistribution restrictions. Prefer a private repository and check the source terms. Never put credentials or signing keys in this repository.

## 2. Add these files to your porting repository

Copy the `.github/`, `scripts/`, and `port_config/` directories from this kit into your repository. Commit them and the source dump (or the selected extracted files you are authorized to store).

## 3. Run the inventory workflow

On GitHub, open **Actions → Motorola Android 17 UI Port - Inventory and Package → Run workflow**.

- `source_dir`: `motorola_dump` (or your repository-relative source directory).
- `build_module`: **false** for the first run.

Download the `motorola-ui-port-reports` artifact. Start with:
- `apk-inventory.csv`: package, SDK, path, size, hash, heuristic category.
- `apk-permissions.txt`: declared permissions.
- `analysis-errors.txt`: APKs that could not be inspected.
- `summary.txt`: counts and limitations.

The category labels are heuristics, not proof. Confirm package names and component roles manually.

## 4. Inspect candidates before approving anything

For each likely app, inspect the manifest and code with tools such as JADX and Apktool on a local workstation. Check:
- `minSdkVersion` and `targetSdkVersion`;
- activities, services, receivers, content providers and widget providers;
- requested and signature/privileged permissions;
- shared libraries and Motorola framework references;
- native libraries and ABI (the OnePlus 9R is arm64);
- references to Motorola-only services, resources and package names;
- whether the component needs an overlay, a privileged-permission allowlist XML, or a matching framework component.

Android SDK metadata does **not** prove Android 17 compatibility. `aapt` inventory does not resolve all runtime dependencies.

Recommended order:
1. Static wallpapers and ordinary wallpaper picker app.
2. Launcher, then its companion apps/services.
3. Widget providers and their data/service dependencies.
4. Lockscreen only after determining whether it requires SystemUI/keyguard or framework modifications.

## 5. Optional test module

Only after review, edit `port_config/allowlist.txt`. Put exact source-relative APK paths in it, one per line, for example:

```text
product/app/Example/Example.apk
```

That is an example format only; use a path that actually exists in your dump. Do not add comments to the file other than lines starting with `#`.

Run the workflow again with `build_module: true`. It will fail if the allowlist is empty or a path is missing. The output is `motorola-ui-module.zip`.

The starter builder only copies APKs into a conventional overlay path and writes a source hash manifest. It does **not** install required XML configuration, grant privileged permissions, provide missing Motorola framework code, or make the apps compatible. Some privileged apps can fail or cause instability. This is not a production-ready port.

## 6. Reversible test procedure

1. Back up boot/system data and keep a recovery/ADB route available.
2. Do not test this first on your daily-use installation.
3. Install only one low-risk component at a time, starting with wallpaper assets/apps.
4. Reboot and check the feature, then collect logs:
   ```sh
   adb logcat -b all -d > motorola-ui-logcat.txt
   adb shell dumpsys package YOUR.PACKAGE.NAME
   ```
5. Look for `ClassNotFoundException`, `NoClassDefFoundError`, `SecurityException`, missing services, and permission denials.
6. If unstable, disable/remove the module in the module manager or from recovery/ADB and reboot. Keep a copy of the original ROM/boot image.

## 7. Important partition note

The builder maps `system/...` into `system/...` inside the module and maps `product/...`, `system_ext/...`, `vendor/...`, and `odm/...` under `system/<partition>/...`. This is a common module-overlay convention, but exact paths and mount behavior depend on the ROM and module manager. Verify the destination against the actual OnePlus 9R ROM before testing.

## Known limitations

- No automatic binary patching or APK resigning.
- No automated JADX/Apktool reverse engineering.
- No automatic copying of framework jars, overlays, XML permission allowlists, or native libraries.
- No guarantee a Motorola lockscreen can be ported as an app.
- Do not replace Infinity-X `SystemUI.apk`, framework jars, or keyguard files with Motorola versions as a shortcut.
