# 🛒 Smart Barcode Scanner

A lightweight, offline-first desktop application that transforms a standard webcam into a high-speed retail scanner and inventory management system.

## 🚀 Key Features

*   **Hardware-Free Scanning**: Uses computer vision to scan retail barcodes via webcam.
*   **Offline-First Architecture**: Stores all stock data locally using an SQLite database.
*   **All-in-One Dashboard**: Features a secure login, product profiling, and live stock tracking.
*   **Loss Prevention**: Tracks expiration dates, low quantities, and supplier details.

## 🛠️ Tech Stack

*   **Language**: Python 3
*   **GUI Framework**: Tkinter
*   **Database**: SQLite
*   **Libraries**: OpenCV (Camera Integration)

## 📂 Project Structure

```text
SmartBarcodeScanner/
├── database/        # Database initialization & helper scripts
├── gui/            # Modular Tkinter interface layouts
├── reports/        # Sales metrics & export modules
├── scanner/        # Computer vision camera tracking
├── inventory.db    # Local SQLite database file
├── app.py          # Main application entry point
└── requirements.txt# Project library dependencies
```

## 💻 Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com
   cd SmartBarcodeScanner
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python app.py
   ```
