import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
import pyperclip
import json
import webbrowser
from datetime import datetime
import pystray
from PIL import Image, ImageGrab, ImageDraw, ImageTk
import threading
import keyboard
import base64
import io
import subprocess
import os
import sys
from playwright.sync_api import sync_playwright
import hashlib
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import pytesseract

# Get the correct path whether running as script or exe
if getattr(sys, 'frozen', False):
    # Running as compiled exe
    base_path = sys._MEIPASS
else:
    # Running as script
    base_path = os.path.dirname(os.path.abspath(__file__))

tesseract_path = os.path.join(base_path, 'tesseract', 'tesseract.exe')
pytesseract.pytesseract.tesseract_cmd = tesseract_path

# List to store full clipboard items with timestamps and pin status
full_history = []

# Variable to remember the last thing we saw on clipboard
last_clipboard = ""
last_clipboard_image = None

# Settings
MAX_HISTORY = 25
window_locked = False

# Default theme settings
DEFAULT_THEME = {
    'name': 'Light',
    'window_bg': '#ecf0f1',
    'title_bg': '#2c3e50',
    'title_fg': '#ffffff',
    'button_frame_bg': '#34495e',
    'button_bg': '#3498db',
    'button_fg': '#ffffff',
    'list_bg': '#ecf0f1',
    'list_select_bg': '#3498db',
    'list_fg': '#000000',
    'search_bg': '#ecf0f1',
    'search_fg': '#000000',
    'status_bg': '#34495e',
    'status_fg': '#ffffff',
    'preview_bg': '#ecf0f1',
    'preview_fg': '#000000',
    'window_opacity': 1.0,
    'text_opacity': 1.0,
    'button_opacity': 1.0,
    'status_opacity': 1.0
}

# Current theme
current_theme = DEFAULT_THEME.copy()

# Screenshot cache directory
SCREENSHOT_CACHE_DIR = "url_screenshots"
if not os.path.exists(SCREENSHOT_CACHE_DIR):
    os.makedirs(SCREENSHOT_CACHE_DIR)

# Function to save window position and size
def save_window_settings():
    settings = {
        'geometry': root.geometry(),
        'locked': window_locked,
        'theme': current_theme
    }
    with open("window_settings.json", "w") as file:
        json.dump(settings, file, indent=2)

# Function to load window position and size
def load_window_settings():
    global window_locked, current_theme
    try:
        with open("window_settings.json", "r") as file:
            settings = json.load(file)
            root.geometry(settings.get('geometry', '800x500'))
            window_locked = settings.get('locked', False)
            loaded_theme = settings.get('theme', DEFAULT_THEME)
            # Merge with defaults to handle new theme properties
            current_theme = DEFAULT_THEME.copy()
            current_theme.update(loaded_theme)
            if window_locked:
                lock_window()
    except FileNotFoundError:
        pass

# Function to apply theme
def apply_theme():
    # Apply window opacity
    root.attributes('-alpha', current_theme['window_opacity'])
    
    # Apply colors
    title.config(bg=current_theme['title_bg'], fg=current_theme['title_fg'])
    button_frame.config(bg=current_theme['button_frame_bg'])
    
    # Update all buttons
    for widget in button_frame.winfo_children():
        if isinstance(widget, tk.Button):
            # Keep semantic colors for specific buttons
            if widget == clear_button:
                widget.config(bg="#e74c3c")
            elif widget == delete_button:
                widget.config(bg="#e67e22")
            elif widget == pin_button:
                widget.config(bg="#9b59b6")
            elif widget == lock_button:
                if window_locked:
                    widget.config(bg="#e74c3c")
                else:
                    widget.config(bg="#27ae60")
            elif widget == minimize_btn:
                widget.config(bg="#3498db")
            elif widget == close_btn:
                widget.config(bg="#c0392b")
            else:
                widget.config(bg=current_theme['button_bg'], fg=current_theme['button_fg'])
    
    search_frame.config(bg=current_theme['search_bg'])
    search_label.config(bg=current_theme['search_bg'], fg=current_theme['search_fg'])
    search_entry.config(bg=current_theme['search_bg'], fg=current_theme['search_fg'])
    
    history_list.config(bg=current_theme['list_bg'], fg=current_theme['list_fg'],
                       selectbackground=current_theme['list_select_bg'])
    
    status_frame.config(bg=current_theme['status_bg'])
    status_label.config(bg=current_theme['status_bg'], fg=current_theme['status_fg'])
    current_clipboard_label.config(bg=current_theme['status_bg'], fg=current_theme['status_fg'])
    
    preview_frame.config(bg=current_theme['preview_bg'])
    preview_label.config(bg=current_theme['title_bg'], fg=current_theme['title_fg'])

# Function to save history to a file
def save_history():
    with open("clipboard_history.json", "w") as file:
        json.dump(full_history, file)

# Function to load history from file
def load_history():
    global last_clipboard, full_history
    try:
        with open("clipboard_history.json", "r") as file:
            full_history = json.load(file)
            refresh_display()
            if full_history:
                if full_history[0]['type'] == 'text':
                    last_clipboard = full_history[0]['text']
    except FileNotFoundError:
        pass

# Function to refresh the display
def refresh_display():
    history_list.delete(0, tk.END)
    search_term = search_var.get().lower()
    
    # Sort: pinned items first, then by timestamp
    sorted_history = sorted(full_history, key=lambda x: (not x.get('pinned', False), -x.get('timestamp', 0)))
    
    for item in sorted_history:
        item_type = item.get('type', 'text')
        
        if item_type == 'image':
            ocr_text = item.get('ocr_text', '')
            if ocr_text:
                display_text = f"[IMAGE: {ocr_text[:25]}...]"
            else:
                display_text = "[IMAGE]"
        else:
            text = item['text']
            # Apply search filter
            if search_term and search_term not in text.lower():
                continue
            
            # Format display
            display_text = text.replace('\n', ' ').replace('\r', '')
        
        # Add pin indicator and timestamp
        pin_indicator = "📌 " if item.get('pinned', False) else ""
        time_str = datetime.fromtimestamp(item['timestamp']).strftime("%H:%M:%S")
        display_line = f"{pin_indicator}[{time_str}] {display_text}"
        
        # Truncate to 50 characters total
        if len(display_line) > 50:
            display_line = display_line[:50] + "..."
        
        history_list.insert(tk.END, display_line)

# Function to normalize URL
def normalize_url(url):
    """Add http:// if URL doesn't have a protocol"""
    url = url.strip()
    if not url.startswith(('http://', 'https://', 'ftp://')):
        # Check if it looks like a URL (has a domain extension)
        if '.' in url and ' ' not in url:
            return 'http://' + url
    return url

# Function to fetch URL metadata
def fetch_url_metadata(url):
    """Fetch page title, description, and favicon"""
    try:
        url = normalize_url(url)
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, timeout=5, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get title
        title = soup.find('title')
        title = title.text.strip() if title else "No title"
        
        # Get description
        description = soup.find('meta', attrs={'name': 'description'})
        if not description:
            description = soup.find('meta', attrs={'property': 'og:description'})
        description = description['content'].strip() if description and 'content' in description.attrs else "No description available"
        
        # Get favicon
        favicon = soup.find('link', rel='icon') or soup.find('link', rel='shortcut icon')
        favicon_url = None
        if favicon and 'href' in favicon.attrs:
            favicon_url = favicon['href']
            if not favicon_url.startswith('http'):
                parsed = urlparse(url)
                favicon_url = f"{parsed.scheme}://{parsed.netloc}{favicon_url}"
        
        return {
            'title': title,
            'description': description,
            'favicon_url': favicon_url,
            'url': url
        }
    except Exception as e:
        return {
            'title': 'Error loading preview',
            'description': str(e),
            'favicon_url': None,
            'url': url
        }

# Function to capture screenshot of URL
def capture_url_screenshot(url):
    """Capture a screenshot of the URL using Playwright"""
    try:
        url = normalize_url(url)
        
        # Create cache filename based on URL hash
        url_hash = hashlib.md5(url.encode()).hexdigest()
        cache_path = os.path.join(SCREENSHOT_CACHE_DIR, f"{url_hash}.png")
        
        # Check if cached
        if os.path.exists(cache_path):
            return cache_path
        
        # Capture screenshot
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1280, 'height': 720})
            page.goto(url, wait_until='networkidle', timeout=30000)  # Changed these
            page.wait_for_timeout(1000)  # Extra wait for rendering
            page.screenshot(path=cache_path)
            browser.close()
        
        return cache_path
    except Exception as e:
        print(f"Screenshot error: {e}")
        return None

# Function to update preview pane
def update_preview(event=None):
    selection = history_list.curselection()
    if selection:
        index = get_actual_index(selection[0])
        if index is not None:
            item = full_history[index]
            item_type = item.get('type', 'text')
            
            if item_type == 'image':
                # Show preview pane for images
                preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, ipadx=5, ipady=5)
                
                # Check if there's OCR text
                ocr_text = item.get('ocr_text', '')
                if ocr_text:
                    preview_label.config(text="Image Preview (OCR Text Available)")
                else:
                    preview_label.config(text="Image Preview")
                
                # Hide metadata, show canvas
                preview_metadata_frame.pack_forget()
                preview_canvas.pack(fill=tk.BOTH, expand=True)
                
                img = base64_to_image(item['image_data'])
                
                # Resize image to fit preview pane (max 400x400)
                img.thumbnail((400, 400), Image.Resampling.LANCZOS)
                
                # Convert to PhotoImage
                photo = ImageTk.PhotoImage(img)
                
                # Clear canvas and display image
                preview_canvas.delete("all")
                preview_canvas.image = photo  # Keep a reference
                preview_canvas.create_image(200, 200, image=photo, anchor=tk.CENTER)
                
                # If OCR text exists, display it below image
                if ocr_text:
                    preview_canvas.create_text(200, 380, text=f"Text: {ocr_text[:50]}...", 
                                              font=("Arial", 8), fill="blue", width=380)
                
            elif is_url(item['text']):
                # Show preview for URLs
                preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, ipadx=5, ipady=5)
                preview_label.config(text="URL Preview")
                
                url = item['text'].strip()
                
                # Show metadata frame immediately
                preview_canvas.pack_forget()
                preview_metadata_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                
                metadata_status.config(text="Loading metadata...")
                metadata_title.config(text="")
                metadata_desc.config(text="")
                metadata_url.config(text="")
                
                # Fetch metadata first (fast)
                def fetch_metadata():
                    data = fetch_url_metadata(url)
                    
                    # Update UI in main thread
                    root.after(0, lambda: metadata_title.config(text=data['title']))
                    root.after(0, lambda: metadata_desc.config(text=data['description']))
                    root.after(0, lambda: metadata_url.config(text=data['url']))
                    root.after(0, lambda: metadata_status.config(text="Loading screenshot..."))
                    
                    # Try to load favicon
                    if data['favicon_url']:
                        try:
                            favicon_response = requests.get(data['favicon_url'], timeout=3)
                            favicon_img = Image.open(io.BytesIO(favicon_response.content))
                            favicon_img = favicon_img.resize((16, 16), Image.Resampling.LANCZOS)
                            favicon_photo = ImageTk.PhotoImage(favicon_img)
                            root.after(0, lambda: metadata_favicon.config(image=favicon_photo))
                            metadata_favicon.image = favicon_photo  # Keep reference
                        except:
                            pass
                
                # Fetch screenshot in background (slow)
                def fetch_screenshot():
                    screenshot_path = capture_url_screenshot(url)
                    
                    if screenshot_path:
                        # Switch to screenshot view
                        img = Image.open(screenshot_path)
                        img.thumbnail((400, 400), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(img)
                        
                        # Update UI in main thread
                        root.after(0, lambda: preview_metadata_frame.pack_forget())
                        root.after(0, lambda: preview_canvas.pack(fill=tk.BOTH, expand=True))
                        root.after(0, lambda: preview_canvas.delete("all"))
                        root.after(0, lambda: preview_canvas.create_image(200, 200, image=photo, anchor=tk.CENTER))
                        preview_canvas.image = photo  # Keep reference
                        root.after(0, lambda: preview_label.config(text="URL Screenshot"))
                    else:
                        root.after(0, lambda: metadata_status.config(text="Screenshot failed"))
                
                # Start both threads
                threading.Thread(target=fetch_metadata, daemon=True).start()
                threading.Thread(target=fetch_screenshot, daemon=True).start()
                
            else:
                # Hide preview pane for regular text
                preview_frame.pack_forget()
    else:
        # No selection, hide preview
        preview_frame.pack_forget()

# Settings Window
def open_settings():
    settings_window = tk.Toplevel(root)
    settings_window.title("Settings")
    settings_window.geometry("500x600")
    settings_window.resizable(False, False)
    
    # Create notebook for tabs
    notebook = ttk.Notebook(settings_window)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Theme Tab
    theme_tab = tk.Frame(notebook, bg='white')
    notebook.add(theme_tab, text='Theme')
    
    tk.Label(theme_tab, text="Quick Themes", font=("Arial", 12, "bold"), bg='white').pack(pady=10)
    
    preset_frame = tk.Frame(theme_tab, bg='white')
    preset_frame.pack(pady=5)
    
    def apply_preset(preset_name):
        global current_theme
        presets = {
            'Light': DEFAULT_THEME.copy(),
            'Dark': {
                'name': 'Dark',
                'window_bg': '#2c3e50',
                'title_bg': '#1a1a1a',
                'title_fg': '#ecf0f1',
                'button_frame_bg': '#34495e',
                'button_bg': '#3498db',
                'button_fg': '#ffffff',
                'list_bg': '#34495e',
                'list_select_bg': '#3498db',
                'list_fg': '#ecf0f1',
                'search_bg': '#2c3e50',
                'search_fg': '#ecf0f1',
                'status_bg': '#1a1a1a',
                'status_fg': '#ecf0f1',
                'preview_bg': '#34495e',
                'preview_fg': '#ecf0f1',
                'window_opacity': 1.0,
                'text_opacity': 1.0,
                'button_opacity': 1.0,
                'status_opacity': 1.0
            },
            'Ocean': {
                'name': 'Ocean',
                'window_bg': '#e8f4f8',
                'title_bg': '#006994',
                'title_fg': '#ffffff',
                'button_frame_bg': '#0080b8',
                'button_bg': '#00a8e8',
                'button_fg': '#ffffff',
                'list_bg': '#d9f0f7',
                'list_select_bg': '#00a8e8',
                'list_fg': '#003f5c',
                'search_bg': '#d9f0f7',
                'search_fg': '#003f5c',
                'status_bg': '#006994',
                'status_fg': '#ffffff',
                'preview_bg': '#d9f0f7',
                'preview_fg': '#003f5c',
                'window_opacity': 1.0,
                'text_opacity': 1.0,
                'button_opacity': 1.0,
                'status_opacity': 1.0
            },
            'Purple': {
                'name': 'Purple',
                'window_bg': '#f3e5f5',
                'title_bg': '#6a1b9a',
                'title_fg': '#ffffff',
                'button_frame_bg': '#8e24aa',
                'button_bg': '#ab47bc',
                'button_fg': '#ffffff',
                'list_bg': '#e1bee7',
                'list_select_bg': '#ab47bc',
                'list_fg': '#4a148c',
                'search_bg': '#e1bee7',
                'search_fg': '#4a148c',
                'status_bg': '#6a1b9a',
                'status_fg': '#ffffff',
                'preview_bg': '#e1bee7',
                'preview_fg': '#4a148c',
                'window_opacity': 1.0,
                'text_opacity': 1.0,
                'button_opacity': 1.0,
                'status_opacity': 1.0
            }
        }
        current_theme = presets[preset_name].copy()
        apply_theme()
        update_status(f"Applied {preset_name} theme")
    
    tk.Button(preset_frame, text="Light", command=lambda: apply_preset('Light'),
             bg='#ecf0f1', width=10).pack(side=tk.LEFT, padx=5)
    tk.Button(preset_frame, text="Dark", command=lambda: apply_preset('Dark'),
             bg='#2c3e50', fg='white', width=10).pack(side=tk.LEFT, padx=5)
    tk.Button(preset_frame, text="Ocean", command=lambda: apply_preset('Ocean'),
             bg='#00a8e8', fg='white', width=10).pack(side=tk.LEFT, padx=5)
    tk.Button(preset_frame, text="Purple", command=lambda: apply_preset('Purple'),
             bg='#ab47bc', fg='white', width=10).pack(side=tk.LEFT, padx=5)
    
    # Colors Tab
    colors_tab = tk.Frame(notebook, bg='white')
    notebook.add(colors_tab, text='Colors')
    
    # Create scrollable frame
    canvas = tk.Canvas(colors_tab, bg='white')
    scrollbar = tk.Scrollbar(colors_tab, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg='white')
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    def create_color_picker(parent, label_text, theme_key):
        frame = tk.Frame(parent, bg='white')
        frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(frame, text=label_text, bg='white', width=20, anchor='w').pack(side=tk.LEFT)
        
        color_display = tk.Label(frame, bg=current_theme[theme_key], width=10, relief=tk.RAISED)
        color_display.pack(side=tk.LEFT, padx=5)
        
        def pick_color():
            color = colorchooser.askcolor(current_theme[theme_key])[1]
            if color:
                current_theme[theme_key] = color
                color_display.config(bg=color)
                apply_theme()
        
        tk.Button(frame, text="Choose", command=pick_color, width=8).pack(side=tk.LEFT)
    
    tk.Label(scrollable_frame, text="Customize Colors", font=("Arial", 12, "bold"), bg='white').pack(pady=10)
    
    create_color_picker(scrollable_frame, "Window Background:", 'window_bg')
    create_color_picker(scrollable_frame, "Title Background:", 'title_bg')
    create_color_picker(scrollable_frame, "Title Text:", 'title_fg')
    create_color_picker(scrollable_frame, "Button Frame:", 'button_frame_bg')
    create_color_picker(scrollable_frame, "Button Background:", 'button_bg')
    create_color_picker(scrollable_frame, "Button Text:", 'button_fg')
    create_color_picker(scrollable_frame, "List Background:", 'list_bg')
    create_color_picker(scrollable_frame, "List Selection:", 'list_select_bg')
    create_color_picker(scrollable_frame, "List Text:", 'list_fg')
    create_color_picker(scrollable_frame, "Search Background:", 'search_bg')
    create_color_picker(scrollable_frame, "Search Text:", 'search_fg')
    create_color_picker(scrollable_frame, "Status Bar Background:", 'status_bg')
    create_color_picker(scrollable_frame, "Status Bar Text:", 'status_fg')
    create_color_picker(scrollable_frame, "Preview Background:", 'preview_bg')
    create_color_picker(scrollable_frame, "Preview Text:", 'preview_fg')
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Opacity Tab
    opacity_tab = tk.Frame(notebook, bg='white')
    notebook.add(opacity_tab, text='Opacity')
    
    tk.Label(opacity_tab, text="Adjust Transparency", font=("Arial", 12, "bold"), bg='white').pack(pady=10)
    
    def create_opacity_slider(parent, label_text, theme_key):
        frame = tk.Frame(parent, bg='white')
        frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(frame, text=label_text, bg='white').pack(anchor='w')
        
        value_label = tk.Label(frame, text=f"{int(current_theme[theme_key] * 100)}%", bg='white')
        value_label.pack(anchor='w')
        
        def on_change(val):
            current_theme[theme_key] = float(val)
            value_label.config(text=f"{int(float(val) * 100)}%")
            if theme_key == 'window_opacity':
                root.attributes('-alpha', float(val))
        
        slider = tk.Scale(frame, from_=0.1, to=1.0, resolution=0.05, orient=tk.HORIZONTAL,
                         command=on_change, bg='white', length=300)
        slider.set(current_theme[theme_key])
        slider.pack()
    
    create_opacity_slider(opacity_tab, "Window Opacity:", 'window_opacity')
    
    tk.Label(opacity_tab, text="Note: Text, button, and status bar opacity\nare visual hints only.",
            bg='white', fg='gray').pack(pady=10)
    
    # Actions Tab
    actions_tab = tk.Frame(notebook, bg='white')
    notebook.add(actions_tab, text='Actions')
    
    tk.Label(actions_tab, text="Theme Management", font=("Arial", 12, "bold"), bg='white').pack(pady=10)
    
    def save_custom_theme():
        save_window_settings()
        messagebox.showinfo("Saved", "Current theme saved successfully!")
    
    def reset_theme():
        global current_theme
        current_theme = DEFAULT_THEME.copy()
        apply_theme()
        messagebox.showinfo("Reset", "Theme reset to default!")
        settings_window.destroy()
    
    tk.Button(actions_tab, text="💾 Save Current Theme", command=save_custom_theme,
             width=30, height=2).pack(pady=10)
    tk.Button(actions_tab, text="🔄 Reset to Default", command=reset_theme,
             width=30, height=2).pack(pady=10)
    
    tk.Label(actions_tab, text="Your theme will be saved\nautomatically when you close the app.",
            bg='white', fg='gray').pack(pady=20)
    
    # Close button
    tk.Button(settings_window, text="Close", command=settings_window.destroy,
             width=15).pack(pady=10)

# Create the main window
root = tk.Tk()
root.title("Macs Clipboard Manager")
root.geometry("800x500")

# Make window stay on top (optional for widget-like behavior)
root.attributes('-topmost', False)

# Function to toggle lock/unlock
def toggle_lock():
    global window_locked
    window_locked = not window_locked
    if window_locked:
        lock_window()
    else:
        unlock_window()
    save_window_settings()

def lock_window():
    global window_locked
    window_locked = True
    root.resizable(False, False)
    root.overrideredirect(True)  # Remove title bar
    lock_button.config(text="🔒 Locked", bg="#e74c3c")
    
    update_status("Window locked - click 🔒 Locked to unlock")

def unlock_window():
    global window_locked
    window_locked = False
    root.resizable(True, True)
    root.overrideredirect(False)  # Show title bar
    lock_button.config(text="🔓 Unlocked", bg="#27ae60")
    
    update_status("Window unlocked - resize/move freely")

# Create a title label
title = tk.Label(root, text="📋 Macs Clipboard History", font=("Arial", 16, "bold"), bg="#2c3e50", fg="white")
title.pack(fill=tk.X, pady=0)

# Button frame
button_frame = tk.Frame(root, bg="#34495e")
button_frame.pack(fill=tk.X, pady=5)

# Function to clear all history
def clear_history():
    global full_history
    history_list.delete(0, tk.END)
    full_history = []
    save_history()
    update_status("History cleared")
    preview_frame.pack_forget()

# Create buttons
clear_button = tk.Button(button_frame, text="Clear History", command=clear_history, 
                         bg="#e74c3c", fg="white", font=("Arial", 9), padx=10)
clear_button.pack(side=tk.LEFT, padx=5)

def delete_selected():
    global full_history
    selection = history_list.curselection()
    if selection:
        index = get_actual_index(selection[0])
        if index is not None:
            item_type = full_history[index].get('type', 'text')
            if item_type == 'image':
                deleted_text = "[IMAGE]"
            else:
                deleted_text = full_history[index]['text'][:50]
            full_history.pop(index)
            save_history()
            refresh_display()
            update_status(f"Deleted: {deleted_text}...")
            preview_frame.pack_forget()

delete_button = tk.Button(button_frame, text="Delete Selected", command=delete_selected,
                         bg="#e67e22", fg="white", font=("Arial", 9), padx=10)
delete_button.pack(side=tk.LEFT, padx=5)

def toggle_pin():
    global full_history
    selection = history_list.curselection()
    if selection:
        index = get_actual_index(selection[0])
        if index is not None:
            full_history[index]['pinned'] = not full_history[index].get('pinned', False)
            save_history()
            refresh_display()
            status = "Pinned" if full_history[index]['pinned'] else "Unpinned"
            update_status(f"{status} item")

pin_button = tk.Button(button_frame, text="Pin/Unpin", command=toggle_pin,
                      bg="#9b59b6", fg="white", font=("Arial", 9), padx=10)
pin_button.pack(side=tk.LEFT, padx=5)

# Lock/Unlock button
lock_button = tk.Button(button_frame, text="🔓 Unlocked", command=toggle_lock,
                       bg="#27ae60", fg="white", font=("Arial", 9), padx=10)
lock_button.pack(side=tk.LEFT, padx=5)

# Settings button
settings_button = tk.Button(button_frame, text="⚙️ Settings", command=open_settings,
                           bg="#95a5a6", fg="white", font=("Arial", 9), padx=10)
settings_button.pack(side=tk.LEFT, padx=5)

# Minimize and Close buttons (only shown when locked)
def minimize_to_tray():
    hide_window()

def close_app():
    quit_app()

minimize_btn = tk.Button(button_frame, text="➖ Minimize", command=minimize_to_tray,
                        bg="#3498db", fg="white", font=("Arial", 9), padx=10)

close_btn = tk.Button(button_frame, text="✖ Close", command=close_app,
                     bg="#c0392b", fg="white", font=("Arial", 9), padx=10)

# Search frame
search_frame = tk.Frame(root, bg="#ecf0f1")
search_frame.pack(fill=tk.X, padx=10, pady=5)

search_label = tk.Label(search_frame, text="Search:", bg="#ecf0f1", font=("Arial", 9))
search_label.pack(side=tk.LEFT, padx=5)

search_var = tk.StringVar()
search_var.trace('w', lambda *args: refresh_display())

search_entry = tk.Entry(search_frame, textvariable=search_var, font=("Arial", 10))
search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

# Main content frame
main_content_frame = tk.Frame(root)
main_content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Left side: List frame
list_container = tk.Frame(main_content_frame)
list_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

list_frame = tk.Frame(list_container)
list_frame.pack(fill=tk.BOTH, expand=True)

v_scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

h_scrollbar = tk.Scrollbar(list_frame, orient=tk.HORIZONTAL)
h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

history_list = tk.Listbox(list_frame, font=("Courier", 10),
                          yscrollcommand=v_scrollbar.set,
                          xscrollcommand=h_scrollbar.set,
                          bg="#ecf0f1", selectbackground="#3498db")
history_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

v_scrollbar.config(command=history_list.yview)
h_scrollbar.config(command=history_list.xview)

history_list.bind('<<ListboxSelect>>', update_preview)

# Right side: Preview pane
preview_frame = tk.Frame(main_content_frame, bg="#ecf0f1", relief=tk.RAISED, borderwidth=2)
preview_frame.config(width=420)

preview_label = tk.Label(preview_frame, text="Preview", bg="#2c3e50", fg="white",
                        font=("Arial", 11, "bold"), pady=5)
preview_label.pack(fill=tk.X)

# Canvas for preview
preview_canvas = tk.Canvas(preview_frame, bg="white", width=400, height=400)

# Metadata preview frame
preview_metadata_frame = tk.Frame(preview_frame, bg="white")

metadata_status = tk.Label(preview_metadata_frame, text="", bg="white", fg="gray", font=("Arial", 9))
metadata_status.pack(pady=5)

metadata_favicon = tk.Label(preview_metadata_frame, bg="white")
metadata_favicon.pack(pady=5)

metadata_title = tk.Label(preview_metadata_frame, text="", bg="white", fg="black",
                         font=("Arial", 11, "bold"), wraplength=300, justify=tk.LEFT)
metadata_title.pack(pady=5, padx=10, fill=tk.X)

metadata_desc = tk.Label(preview_metadata_frame, text="", bg="white", fg="#555",
                        font=("Arial", 9), wraplength=300, justify=tk.LEFT)
metadata_desc.pack(pady=5, padx=10, fill=tk.X)

metadata_url = tk.Label(preview_metadata_frame, text="", bg="white", fg="#3498db",
                       font=("Arial", 8), wraplength=300, justify=tk.LEFT, cursor="hand2")
metadata_url.pack(pady=5, padx=10, fill=tk.X)

# Status bar
status_frame = tk.Frame(root, bg="#34495e")
status_frame.pack(side=tk.BOTTOM, fill=tk.X)

status_label = tk.Label(status_frame, text="Ready", font=("Arial", 9), bg="#34495e", fg="white", anchor=tk.W)
status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

current_clipboard_label = tk.Label(status_frame, text="Currently copied: None", font=("Arial", 9), bg="#34495e", fg="#95a5a6", anchor=tk.E)
current_clipboard_label.pack(side=tk.RIGHT, padx=5)

def update_status(message):
    status_label.config(text=message)
    root.after(3000, lambda: status_label.config(text="Ready"))

def update_current_clipboard(text, item_type='text'):
    timestamp = datetime.now().strftime("%I:%M:%S %p")
    if item_type == 'image':
        current_clipboard_label.config(text=f"Currently copied: [IMAGE] at {timestamp}")
    else:
        display_text = text.replace('\n', ' ').replace('\r', '')[:40]
        if len(display_text) > 40:
            display_text = display_text[:40] + "..."
        current_clipboard_label.config(text=f"Currently copied: {display_text} at {timestamp}")

load_history()
load_window_settings()
apply_theme()

def image_to_base64(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def base64_to_image(base64_string):
    image_data = base64.b64decode(base64_string)
    return Image.open(io.BytesIO(image_data))

def check_clipboard():
    global last_clipboard, last_clipboard_image, full_history
    
    try:
        img = ImageGrab.grabclipboard()
        if img and img != last_clipboard_image:
            last_clipboard_image = img
            
            # Try to extract text from image using OCR
            ocr_text = ""
            try:
                ocr_text = pytesseract.image_to_string(img).strip()
                print(f"OCR extracted: {ocr_text[:50]}...")
            except Exception as e:
                print(f"OCR error: {e}")
            
            item = {
                'type': 'image',
                'image_data': image_to_base64(img),
                'ocr_text': ocr_text,
                'timestamp': datetime.now().timestamp(),
                'pinned': False
            }
            full_history.insert(0, item)
            
            unpinned = [x for x in full_history if not x.get('pinned', False)]
            pinned = [x for x in full_history if x.get('pinned', False)]
            
            if len(unpinned) > MAX_HISTORY:
                unpinned = unpinned[:MAX_HISTORY]
            
            full_history = pinned + unpinned
            
            save_history()
            refresh_display()
            
            if ocr_text:
                update_status(f"Captured: [IMAGE with text: {ocr_text[:30]}...]")
            else:
                update_status("Captured: [IMAGE]")
            update_current_clipboard("[IMAGE]", 'image')
                
            root.after(500, check_clipboard)
            return
    except:
        pass
    
    current = pyperclip.paste()
    
    if current != last_clipboard and current.strip():
        last_clipboard = current
        
        duplicate_found = False
        for item in full_history:
            if item.get('type', 'text') == 'text' and item.get('text') == current:
                duplicate_found = True
                break
        
        if not duplicate_found:
            item = {
                'type': 'text',
                'text': current,
                'timestamp': datetime.now().timestamp(),
                'pinned': False
            }
            full_history.insert(0, item)
            
            unpinned = [x for x in full_history if not x.get('pinned', False)]
            pinned = [x for x in full_history if x.get('pinned', False)]
            
            if len(unpinned) > MAX_HISTORY:
                unpinned = unpinned[:MAX_HISTORY]
            
            full_history = pinned + unpinned
            
            save_history()
            refresh_display()
            
            display_text = current.replace('\n', ' ').replace('\r', '')[:50]
            update_status(f"Captured: {display_text}...")
            update_current_clipboard(current)
    
    root.after(500, check_clipboard)

def is_url(text):
    text = text.strip().lower()
    # Check for URL patterns (http://, https://, www., or domain.extension format)
    if text.startswith(('http://', 'https://', 'www.', 'ftp://')):
        return True
    # Check if it looks like a domain (has a dot and no spaces)
    if '.' in text and ' ' not in text and len(text.split('.')) >= 2:
        # Make sure it has a valid TLD-like ending
        parts = text.split('.')
        if len(parts[-1]) >= 2:  # TLD should be at least 2 characters
            return True
    return False

def get_actual_index(display_index):
    search_term = search_var.get().lower()
    sorted_history = sorted(full_history, key=lambda x: (not x.get('pinned', False), -x.get('timestamp', 0)))
    
    current_display = 0
    for idx, item in enumerate(sorted_history):
        if item.get('type', 'text') == 'text':
            if search_term and search_term not in item.get('text', '').lower():
                continue
        if current_display == display_index:
            return full_history.index(item)
        current_display += 1
    return None

def item_clicked(event):
    global full_history, last_clipboard, last_clipboard_image
    selection = history_list.curselection()
    if selection:
        index = get_actual_index(selection[0])
        if index is not None:
            item = full_history[index]
            item_type = item.get('type', 'text')
            
            if item_type == 'image':
                # Check if image has OCR text - copy that instead
                ocr_text = item.get('ocr_text', '')
                if ocr_text:
                    # Copy OCR text to clipboard
                    pyperclip.copy(ocr_text)
                    last_clipboard = ocr_text
                    update_status(f"Copied OCR text: {ocr_text[:50]}...")
                    update_current_clipboard(ocr_text)
                else:
                    # Copy image to clipboard
                    img = base64_to_image(item['image_data'])
                    output = io.BytesIO()
                    img.convert('RGB').save(output, 'BMP')
                    data = output.getvalue()[14:]
                    output.close()
                    
                    import win32clipboard
                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                    win32clipboard.CloseClipboard()
                    
                    last_clipboard_image = img
                    update_status("Copied image to clipboard")
                    update_current_clipboard("[IMAGE]", 'image')
            else:
                full_text = item['text']
                if is_url(full_text):
                    full_text = normalize_url(full_text)
                    webbrowser.open(full_text)
                    update_status(f"Opening URL: {full_text[:50]}...")
                else:
                    pyperclip.copy(full_text)
                    last_clipboard = full_text
                    update_status(f"Copied: {full_text[:50]}...")
                    update_current_clipboard(full_text)

def show_context_menu(event):
    index = history_list.nearest(event.y)
    history_list.selection_clear(0, tk.END)
    history_list.selection_set(index)
    history_list.activate(index)
    
    update_preview()
    
    actual_index = get_actual_index(index)
    if actual_index is not None:
        is_image = full_history[actual_index].get('type', 'text') == 'image'
        
        if is_image:
            context_menu.entryconfig("Open Image", state="normal")
            # Check if image has OCR text
            if full_history[actual_index].get('ocr_text', ''):
                context_menu.entryconfig("Copy OCR Text", state="normal")
            else:
                context_menu.entryconfig("Copy OCR Text", state="disabled")
        else:
            context_menu.entryconfig("Open Image", state="disabled")
            context_menu.entryconfig("Copy OCR Text", state="disabled")
    
    context_menu.post(event.x_root, event.y_root)

def google_search_menu():
    global full_history
    selection = history_list.curselection()
    if selection:
        index = get_actual_index(selection[0])
        if index is not None:
            item = full_history[index]
            if item.get('type', 'text') == 'text':
                search_text = item['text']
                search_url = f"https://www.google.com/search?q={search_text}"
                webbrowser.open(search_url)
                update_status(f"Googling: {search_text[:50]}...")

def copy_menu():
    global full_history
    selection = history_list.curselection()
    if selection:
        index = get_actual_index(selection[0])
        if index is not None:
            item = full_history[index]
            if item.get('type', 'text') == 'text':
                full_text = item['text']
                pyperclip.copy(full_text)
                update_status(f"Copied: {full_text[:50]}...")
                update_current_clipboard(full_text)

def copy_ocr_text_menu():
    global full_history
    selection = history_list.curselection()
    if selection:
        index = get_actual_index(selection[0])
        if index is not None:
            item = full_history[index]
            if item.get('type') == 'image':
                ocr_text = item.get('ocr_text', '')
                if ocr_text:
                    pyperclip.copy(ocr_text)
                    update_status(f"Copied OCR text: {ocr_text[:50]}...")
                    update_current_clipboard(ocr_text)

def open_image_menu():
    global full_history
    selection = history_list.curselection()
    if selection:
        index = get_actual_index(selection[0])
        if index is not None:
            item = full_history[index]
            if item.get('type') == 'image':
                img = base64_to_image(item['image_data'])
                temp_path = os.path.abspath("temp_clipboard_image.png")
                img.save(temp_path)
                
                try:
                    os.startfile(temp_path)
                    update_status("Opening image...")
                except:
                    update_status("Error opening image")

context_menu = tk.Menu(root, tearoff=0)
context_menu.add_command(label="Copy", command=copy_menu)
context_menu.add_command(label="Copy OCR Text", command=copy_ocr_text_menu)
context_menu.add_command(label="Google This", command=google_search_menu)
context_menu.add_command(label="Open Image", command=open_image_menu)
context_menu.add_command(label="Pin/Unpin", command=toggle_pin)
context_menu.add_command(label="Delete", command=delete_selected)

history_list.bind("<Double-Button-1>", item_clicked)
history_list.bind("<Button-3>", show_context_menu)

def create_image():
    # Load your icon file for system tray
    try:
        # Get the correct path whether running as script or exe
        if getattr(sys, 'frozen', False):
            # Running as compiled exe
            base_path = sys._MEIPASS
        else:
            # Running as script
            base_path = os.path.dirname(__file__)
        
        icon_path = os.path.join(base_path, "bearded-skull-6.ico")
        icon_img = Image.open(icon_path)
        # Resize to 64x64 for tray
        icon_img = icon_img.resize((64, 64), Image.Resampling.LANCZOS)
        return icon_img
    except Exception as e:
        print(f"Icon loading error: {e}")
        # Fallback to simple icon if file not found
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), color='#3498db')
        dc = ImageDraw.Draw(image)
        dc.rectangle([width//4, height//4, 3*width//4, 3*height//4], fill='white')
        return image

def show_window(icon=None, item=None):
    root.after(0, root.deiconify)
    root.after(0, root.lift)
    root.after(0, root.focus_force)

def hide_window():
    root.withdraw()

def quit_app(icon=None, item=None):
    if icon:
        icon.stop()
    save_history()
    save_window_settings()
    root.quit()
    os._exit(0)  # Force complete exit

def setup_tray_icon():
    icon = pystray.Icon("clipboard_manager")
    icon.icon = create_image()
    icon.title = "Clipboard Manager"
    icon.menu = pystray.Menu(
        pystray.MenuItem("Show", show_window),
        pystray.MenuItem("Quit", quit_app)
    )
    icon.run()

# When window X is clicked (or close button when locked)
def on_closing():
    save_window_settings()
    hide_window()  # Minimize to system tray

root.protocol("WM_DELETE_WINDOW", on_closing)

def hotkey_callback():
    show_window()

keyboard.add_hotkey('ctrl+shift+v', hotkey_callback)

tray_thread = threading.Thread(target=setup_tray_icon, daemon=True)
tray_thread.start()

check_clipboard()

root.mainloop()