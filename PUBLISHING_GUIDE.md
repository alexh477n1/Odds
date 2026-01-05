# Publishing MatchCaddy to App Stores

This guide covers publishing your Expo app to both iOS App Store and Google Play Store.

## Prerequisites

1. **Expo Account**: Sign up at [expo.dev](https://expo.dev) if you haven't already
2. **Apple Developer Account**: $99/year for iOS App Store
3. **Google Play Developer Account**: $25 one-time fee for Android

---

## iOS App Store (Apple)

### Step 1: Configure iOS Settings

Your `app.json` already has basic iOS configuration. You may want to add more details:

```json
"ios": {
  "supportsTablet": true,
  "bundleIdentifier": "com.matchcaddy.app",
  "buildNumber": "1",
  "infoPlist": {
    "NSUserTrackingUsageDescription": "This identifier will be used to deliver personalized ads to you.",
    "NSCameraUsageDescription": "Allow MatchCaddy to access your camera",
    "NSPhotoLibraryUsageDescription": "Allow MatchCaddy to access your photos"
  }
}
```

### Step 2: Install EAS CLI

```bash
npm install -g eas-cli
```

### Step 3: Login to Expo

```bash
eas login
```

### Step 4: Configure EAS Build

Run this in your `matchcaddy-app` directory:

```bash
cd matchcaddy-app
eas build:configure
```

This creates an `eas.json` file. You can customize it for production builds.

### Step 5: Build for iOS

**For App Store submission:**
```bash
eas build --platform ios --profile production
```

This will:
- Build your app in the cloud
- Generate an `.ipa` file ready for App Store submission
- Take about 15-30 minutes

### Step 6: Submit to App Store

**Option A: Using EAS Submit (Recommended)**
```bash
eas submit --platform ios
```

**Option B: Manual Submission**
1. Download the `.ipa` from the EAS build page
2. Use **Transporter** app (macOS) or **Xcode** to upload
3. Or use **App Store Connect** web interface

### Step 7: App Store Connect Setup

1. Go to [App Store Connect](https://appstoreconnect.apple.com)
2. Create a new app:
   - Name: MatchCaddy
   - Bundle ID: `com.matchcaddy.app` (must match your app.json)
   - Primary Language: English
3. Fill out app information:
   - Description
   - Screenshots (required: 6.5" and 5.5" displays)
   - App icon (1024x1024px)
   - Privacy policy URL
   - Category
   - Age rating
4. Submit for review

---

## Google Play Store (Android)

### Step 1: Configure Android Settings

Your `app.json` already has Android configuration. You may want to add:

```json
"android": {
  "adaptiveIcon": {
    "foregroundImage": "./assets/adaptive-icon.png",
    "backgroundColor": "#0D0D0D"
  },
  "edgeToEdgeEnabled": true,
  "package": "com.matchcaddy.app",
  "versionCode": 1,
  "permissions": []
}
```

### Step 2: Build for Android

**For Play Store submission:**
```bash
eas build --platform android --profile production
```

This generates an `.aab` (Android App Bundle) file, which is required for Play Store.

### Step 3: Submit to Google Play Store

**Option A: Using EAS Submit (Recommended)**
```bash
eas submit --platform android
```

**Option B: Manual Submission**
1. Go to [Google Play Console](https://play.google.com/console)
2. Create a new app
3. Upload the `.aab` file
4. Fill out store listing:
   - App name, description, screenshots
   - App icon (512x512px)
   - Feature graphic (1024x500px)
   - Privacy policy URL
   - Content rating questionnaire
5. Submit for review

---

## Quick Start Commands

### Complete Workflow

```bash
# 1. Navigate to app directory
cd matchcaddy-app

# 2. Install dependencies (if not done)
npm install

# 3. Login to Expo
eas login

# 4. Configure EAS (first time only)
eas build:configure

# 5. Build for both platforms
eas build --platform all --profile production

# 6. Submit to stores
eas submit --platform ios
eas submit --platform android
```

---

## Important Notes

### Before Publishing

1. **Update Version Numbers**:
   - Update `version` in `app.json` (e.g., "1.0.0" → "1.0.1")
   - iOS: Increment `buildNumber` for each submission
   - Android: Increment `versionCode` for each submission

2. **App Icons & Screenshots**:
   - iOS: Need screenshots for different device sizes
   - Android: Need screenshots and feature graphic
   - Both: App icon must be high quality

3. **Privacy Policy**:
   - Required for both stores
   - Host it somewhere accessible (GitHub Pages, your website, etc.)

4. **Testing**:
   - Test your app thoroughly before submitting
   - Use TestFlight (iOS) and Internal Testing (Android) for beta testing

### EAS Build Profiles

You can create different build profiles in `eas.json`:

```json
{
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal"
    },
    "preview": {
      "distribution": "internal"
    },
    "production": {
      "autoIncrement": true
    }
  }
}
```

### Environment Variables

If you need environment variables (API keys, etc.):

1. Create `.env` file (add to `.gitignore`)
2. Use `expo-constants` or `eas secret:create` for secure storage
3. Access via `Constants.expoConfig.extra`

---

## Cost Breakdown

- **Apple Developer Program**: $99/year
- **Google Play Developer**: $25 one-time
- **EAS Build**: Free tier includes limited builds, then paid plans
- **EAS Submit**: Free for Expo accounts

---

## Resources

- [Expo EAS Build Docs](https://docs.expo.dev/build/introduction/)
- [Expo EAS Submit Docs](https://docs.expo.dev/submit/introduction/)
- [App Store Connect Guide](https://developer.apple.com/app-store-connect/)
- [Google Play Console Guide](https://support.google.com/googleplay/android-developer/)

---

## Troubleshooting

### Common Issues

1. **Build fails**: Check logs in EAS dashboard
2. **Bundle ID mismatch**: Ensure `app.json` matches App Store Connect/Play Console
3. **Missing permissions**: Add required permissions to `app.json`
4. **Icon issues**: Ensure icons are correct size and format

### Getting Help

- Expo Discord: [discord.gg/expo](https://discord.gg/expo)
- Expo Forums: [forums.expo.dev](https://forums.expo.dev)
- Stack Overflow: Tag `expo`

---

Good luck with your app launch! 🚀





