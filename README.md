# coocaa-home-shim

A tiny Android app (about 15 KB, no internet permission) that lets the
[Clean Your TV](https://github.com/Gathin23/cleanyourtv) launcher be Home on Skyworth's China-market
TVs running **Coocaa OS** (酷开系统).

Tested on a Skyworth 7S60_A5 (Coocaa OS on Android 8.0). The full setup, with the debloat list and the
launcher config, is in
[`examples/skyworth-7s60-a5`](https://github.com/Gathin23/cleanyourtv/tree/main/examples/skyworth-7s60-a5)
of that repo.

## Why it is needed

On Coocaa OS the Home key and the boot flow start whatever the system properties
`persist.service.homepage.pkg` / `.cls` name. Android's HOME resolution is not used, so
`set-home-activity` and a HOME intent filter do nothing. You can `setprop` the properties from ADB, but
`com.tianci.system` rewrites them at every boot, to `com.ccos.tv.homepage/.LaunchActivity` if a package
of that name is installed, and to the stock home (`com.tianci.movieplatform`) otherwise.

This app is that package. It has:

- **`LaunchActivity`**: an invisible activity that starts the launcher
  (`com.coocaa.tvhome/com.gathin.tvhome.MainActivity`) and finishes. If the launcher is missing, it
  starts the stock Coocaa home instead, so Home never leads nowhere.
- **`BootReceiver` and `BootWatchService`**: Coocaa's own boot flow opens the stock home after the boot
  video, whatever the properties say. For two minutes after boot, every 2 seconds, the service checks
  the front app (`sky.current.apk`). When it is the stock home, it asks `com.tianci.system` to go Home
  (`content://com.tianci.provider`, method `COMMON`, `gotoHomePage`), because Coocaa blocks activity
  starts from background apps. It stops as soon as the launcher or any other app is in front, then
  exits its process: Coocaa force-stops a package whose process lingers, and a stopped package misses
  the next boot broadcast. Each run is logged to
  `/sdcard/Android/data/com.ccos.tv.homepage/files/watch.log`.

  Something on Coocaa OS (most likely the TV manager's autostart control) disables the boot receivers
  of third-party apps. The app re-enables its own receiver whenever it runs.

With the stock home disabled (`pm disable-user --user 0 com.tianci.movieplatform`), the boot flow has
nothing else to open and the watch has nothing to do.

The launcher must be built as `com.coocaa.tvhome`
(`./gradlew assembleRelease -PlauncherApplicationId=com.coocaa.tvhome`): Coocaa's memory manager
force-stops third-party apps shortly after they leave the screen, but spares `com.coocaa.*` packages.

## Install

From a clone of cleanyourtv, with the TV's IP in `TV_HOST`:

```bash
PY=tools/venv/bin/python
"$PY" -I tools/b64push.py coocaa-home-shim.apk /data/local/tmp/shim.apk
"$PY" -I tools/tv.py 'pm install -r /data/local/tmp/shim.apk; rm -f /data/local/tmp/shim.apk'
"$PY" -I tools/tv.py 'setprop persist.service.homepage.pkg com.ccos.tv.homepage; setprop persist.service.homepage.cls com.ccos.tv.homepage.LaunchActivity; input keyevent KEYCODE_HOME'
```

Uninstall it before giving Home back to Coocaa, or `com.tianci.system` will point Home at it again on
the next boot:

```bash
"$PY" -I tools/tv.py 'pm enable com.tianci.movieplatform; pm uninstall com.ccos.tv.homepage'
"$PY" -I tools/tv.py 'setprop persist.service.homepage.pkg com.tianci.movieplatform; setprop persist.service.homepage.cls com.coocaa.homepage.vast.HomePageActivity'
```

## Build

JDK 17 and Android SDK platform 34: `./gradlew assembleRelease`, then
`app/build/outputs/apk/release/app-release.apk`. `targetSdk` stays at 25 on purpose, so the boot watch
may run as a plain background service on Android 8. `settings.gradle` lists the Aliyun mirrors first,
for builds from mainland China.

## Licence

MIT
