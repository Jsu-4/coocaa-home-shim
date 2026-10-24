package com.ccos.tv.homepage;

import android.content.BroadcastReceiver;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;

import java.lang.reflect.Method;

public class BootReceiver extends BroadcastReceiver {

    /**
     * Something on Coocaa TVs (most likely the TV manager's autostart control) disables the boot
     * receivers of every third-party app, which silently drops even explicit broadcasts to them.
     * An app may re-enable its own components, so do that whenever this package runs.
     */
    static void keepEnabled(Context context) {
        ComponentName self = new ComponentName(context, BootReceiver.class);
        PackageManager pm = context.getPackageManager();
        try {
            if (pm.getComponentEnabledSetting(self) != PackageManager.COMPONENT_ENABLED_STATE_ENABLED) {
                pm.setComponentEnabledSetting(self, PackageManager.COMPONENT_ENABLED_STATE_ENABLED,
                        PackageManager.DONT_KILL_APP);
            }
        } catch (RuntimeException ignored) {
        }
    }

    /** Starts the watch without a reboot: am broadcast -a com.ccos.tv.homepage.WATCH -n com.ccos.tv.homepage/.BootReceiver */
    static final String ACTION_WATCH = "com.ccos.tv.homepage.WATCH";
    /** Sent at boot to a launcher build that has a BootReceiver; ignored by one that has none. */
    private static final String ACTION_LAUNCHER_BOOT = "com.ccos.tv.homepage.BOOT";

    @Override
    public void onReceive(Context context, Intent intent) {
        String action = intent.getAction();
        boolean boot = Intent.ACTION_LOCKED_BOOT_COMPLETED.equals(action) || Intent.ACTION_BOOT_COMPLETED.equals(action);
        if (!boot && !ACTION_WATCH.equals(action)) return;
        if (boot) {
            // The framework sometimes writes the literal strings home[0] / home[1] here at boot, and then
            // gotoHomePage follows those and the Home key does nothing. Put this package back first.
            setProp("persist.service.homepage.pkg", "com.ccos.tv.homepage");
            setProp("persist.service.homepage.cls", "com.ccos.tv.homepage.LaunchActivity");
            // Coocaa's standby force-stops every app but the homepage package (this one), and a stopped
            // launcher gets no boot broadcast of its own; an explicit one that includes stopped packages wakes it.
            context.sendBroadcast(new Intent(ACTION_LAUNCHER_BOOT)
                    .setClassName(BootWatchService.LAUNCHER, "com.gathin.tvhome.BootReceiver")
                    .addFlags(Intent.FLAG_INCLUDE_STOPPED_PACKAGES));
        }
        context.startService(new Intent(context, BootWatchService.class));
    }

    private static void setProp(String key, String value) {
        try {
            Class<?> c = Class.forName("android.os.SystemProperties");
            Method set = c.getMethod("set", String.class, String.class);
            set.invoke(null, key, value);
        } catch (ReflectiveOperationException | RuntimeException ignored) {
        }
    }
}
