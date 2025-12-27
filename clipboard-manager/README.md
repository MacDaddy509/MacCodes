# Mac's Clipboard Manager

A powerful, feature-rich clipboard manager for Windows with OCR support, URL previews, and complete theme customization.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

### Core Clipboard Management
- 📋 **History tracking** - Saves last 25 clipboard items (text & images)
- 📌 **Pin favorites** - Keep important items at the top
- 🔍 **Search & filter** - Find anything in your history instantly
- ⏱️ **Timestamps** - Know when you copied something
- 💾 **Persistent storage** - History survives restarts

### Smart Features
- 🔤 **OCR text extraction** - Automatically extracts text from images
- 🌐 **URL detection** - Auto-opens links, shows website previews
- 📸 **URL screenshots** - Visual previews of websites (cached)
- 🔗 **Google search** - Right-click any text to Google it
- 🚫 **Duplicate prevention** - Won't save the same text twice

### Customization
- 🎨 **Full theme editor** - Change every color
- 🌙 **Dark mode** - Plus Ocean, Purple, and custom themes
- 👻 **Window opacity** - Make the window transparent
- 🔒 **Widget mode** - Lock window as borderless widget
- ⚙️ **Persistent settings** - Your preferences are saved

### Convenience
- 🔥 **Global hotkey** - Ctrl+Shift+V shows window from anywhere
- 📱 **System tray** - Minimizes to tray, not taskbar
- 🚀 **Auto-start** - Optional startup with Windows
- 💨 **Lightweight** - Runs in background, minimal resources

## Installation

### Option 1: Portable (Recommended)
1. Download `ClipboardManager.exe` from [Releases](https://github.com/Macdaddy509/clipboard-manager/releases)
2. Run it - no installation needed!
3. (Optional) Add to Windows Startup folder for auto-start

### Option 2: Build from Source
```bash
# Clone the repository
git clone https://github.com/Macdaddy509/clipboard-manager.git
cd clipboard-manager

# Install dependencies
pip install -r requirements.txt

# Install Tesseract OCR
# Download from: https://digi.bib.uni-mannheim.de/tesseract/
# Install to default location (C:\Program Files\Tesseract-OCR)

# Run the app
python clipboard_manager.py
```

## Usage

### Basic Operations
- **Copy something** - It's automatically saved to history
- **Double-click item** - Copies it back to clipboard (or opens URL)
- **Right-click item** - See more options (Google, Pin, Delete, etc.)
- **Search box** - Filter your clipboard history
- **Ctrl+Shift+V** - Show/hide window from anywhere

### Image OCR
- Copy any image with text (screenshot, photo, etc.)
- Text is automatically extracted and shown: `[IMAGE: extracted text...]`
- Double-click to copy the extracted text instead of the image

### URL Previews
- Copy any URL (works without http://)
- Click the item to see metadata preview
- Wait a few seconds for full screenshot preview
- Screenshots are cached for instant loading next time

### Themes
1. Click **⚙️ Settings**
2. Go to **Theme** tab for quick presets
3. Go to **Colors** tab to customize everything
4. Go to **Opacity** tab to adjust window transparency
5. Click **Save Current Theme** to keep your settings

### Widget Mode
- Click **🔓 Unlocked** to lock the window
- Window becomes borderless and non-resizable
- Perfect for keeping it visible on your desktop
- Click **🔒 Locked** to unlock again

## Privacy

This app:
- ✅ Stores ALL clipboard data **locally** on your computer
- ✅ Does **NOT** send your data to any server
- ✅ Does **NOT** track you or collect analytics
- ℹ️ When you click a URL in your history:
  - Fetches the webpage to show you a preview
  - Downloads page title, description, and screenshot
  - These are standard web requests (same as visiting the site)
- ✅ OCR text extraction happens **locally** using Tesseract
- ✅ No third-party data collection

**Your clipboard data stays on your computer.**

## File Locations

All files are created in the same folder as the .exe:

- `clipboard_history.json` - Your clipboard history
- `window_settings.json` - Window position, size, theme, lock state
- `url_screenshots/` - Cached website screenshots
- `temp_clipboard_image.png` - Temporary file for viewing images

## Keyboard Shortcuts

- **Ctrl+Shift+V** - Show/hide clipboard manager
- **Ctrl+F** - Focus search box (when window is open)
- **Delete** - Delete selected item
- **Escape** - Close settings window

## System Requirements

- Windows 10 or later (64-bit)
- ~550MB disk space (includes OCR engine)
- No other requirements - fully portable!

## Built With

- **Python 3.13** - Core language
- **Tkinter** - GUI framework
- **Tesseract OCR** - Text extraction from images
- **Playwright** - Website screenshot capture
- **PyInstaller** - Packaging to .exe

## Troubleshooting

**"OCR not working"**
- OCR is bundled with the app - no action needed
- If it still fails, check if image has clear, readable text

**"URL previews not loading"**
- Check your internet connection
- Some websites block automated screenshot tools
- Metadata preview will still work

**"Window won't show after Ctrl+Shift+V"**
- Check system tray - right-click skull icon → Show
- Restart the app if needed

**"Antivirus blocking the app"**
- PyInstaller apps sometimes trigger false positives
- Add an exception in your antivirus
- You can scan the .exe at virustotal.com

## Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

## License

MIT License - see [LICENSE](LICENSE) file for details

## Author

Created by Mac

## Acknowledgments

- Tesseract OCR team for the OCR engine
- Anthropic's Claude for development assistance
