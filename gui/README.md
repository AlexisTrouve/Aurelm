# Aurelm GUI — Flutter Desktop

## Setup

Flutter is required to build and run the GUI. It's not currently installed on this machine.

### Install Flutter

1. Download Flutter SDK from https://flutter.dev/docs/get-started/install/windows
2. Add Flutter to PATH
3. Run `flutter doctor` to verify setup
4. Enable Windows desktop support: `flutter config --enable-windows-desktop`

### Create the project

From this directory:

```bash
flutter create --org com.aurelm --project-name aurelm_gui .
```

This will generate the full Flutter project structure in place, preserving existing files.

### Run

```bash
flutter pub get
flutter run -d windows
```

## Architecture

- **State management**: Riverpod 3.0
- **Platform**: Windows Desktop (primary)
- **Features**: Dashboard, entity browser, timeline, agent chat, settings
