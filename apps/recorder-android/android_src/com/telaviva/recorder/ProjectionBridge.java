package com.telaviva.recorder;

import android.content.Intent;
import android.media.projection.MediaProjection;
import android.os.Parcel;
import android.util.Base64;

/** Small Android bridge used from PyJNIus. */
public final class ProjectionBridge {
    private ProjectionBridge() {}

    public static String intentToBase64(Intent intent) {
        Parcel parcel = Parcel.obtain();
        try {
            intent.writeToParcel(parcel, 0);
            return Base64.encodeToString(parcel.marshall(), Base64.NO_WRAP);
        } finally {
            parcel.recycle();
        }
    }

    public static Intent intentFromBase64(String encoded) {
        byte[] bytes = Base64.decode(encoded, Base64.NO_WRAP);
        Parcel parcel = Parcel.obtain();
        try {
            parcel.unmarshall(bytes, 0, bytes.length);
            parcel.setDataPosition(0);
            return Intent.CREATOR.createFromParcel(parcel);
        } finally {
            parcel.recycle();
        }
    }

    /**
     * Android 14+ requires a MediaProjection.Callback to be registered before
     * createVirtualDisplay(). Python polls this flag and performs cleanup.
     */
    public static final class ProjectionCallback extends MediaProjection.Callback {
        private volatile boolean stopped = false;

        @Override
        public void onStop() {
            stopped = true;
        }

        public boolean isStopped() {
            return stopped;
        }
    }
}
