# Pakaneo Billing Automation

A comprehensive automation platform that streamlines billing data downloads from your Pakaneo system. Features both a modern web interface and powerful command-line tools for maximum flexibility.

## 🎯 What This Does

This platform automatically:
- **Logs into your Pakaneo account** with smart session management
- **Downloads billing data** for specific customers and date ranges
- **Organizes CSV files** with descriptive names and folder structure
- **Handles errors gracefully** with automatic retries and detailed reporting
- **Processes multiple downloads** simultaneously for optimal performance
- **Provides real-time progress** tracking through the web interface

## ✨ Key Features

### 🌐 **Modern Web Interface**
- **Intuitive 3-step wizard** - Select customers, set dates, download
- **Real-time progress tracking** - See download status as it happens
- **Smart date presets** - Today, This Week, This Month, etc.
- **Customer management** - Add, edit, and organize your customer list
- **Recent downloads history** - Quick access to past exports

### 🔐 **Smart Authentication**
- Automatically handles Pakaneo login using your credentials
- Remembers session data to avoid repeated logins
- Auto-refreshes expired tokens without interruption
- Secure credential storage in local environment files

### 📊 **Flexible Data Export**
- Download data for any combination of customers
- Custom date ranges with intelligent presets
- Multiple export types: stored products, packed orders, etc.
- Organized file naming with date ranges and customer info

### ⚡ **High Performance**
- Downloads up to 20 files simultaneously
- Intelligent retry system for failed downloads
- Concurrent browser sessions for faster authentication
- Progress tracking and detailed logging

### 🛡️ **Robust Error Handling**
- Automatically recovers from network issues
- Handles expired authentication gracefully
- Comprehensive logging for troubleshooting
- Detailed download reports in JSON format

## 🚀 Quick Start

### Option 1: Web Interface (Recommended)

**1. One-Click Setup:**
```bash
# Simply double-click this file:
run_ui.bat
```
This will automatically:
- Create virtual environment if needed
- Install all dependencies
- Launch the web interface
- Open your browser to the application

**2. Use the Web Interface:**
- **Step 1:** Select customers from your list
- **Step 2:** Choose date range (or use presets like "This Month")
- **Step 3:** Click download and watch real-time progress

### Option 2: Command Line Interface

**1. Setup (One-time):**
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install browser automation
playwright install

# Create your credentials file
copy .env.example .env
# Edit .env with your Pakaneo login details
```

**2. Usage:**
```bash
# Download data for single customer
python main.py --apiuser-ids 207 --start-date 2025-07-01 --end-date 2025-07-15

# Download data for multiple customers
python main.py --apiuser-ids 204,205,206 --start-date 2025-06-01 --end-date 2025-06-30

# Use different Pakaneo URLs
python main.py --apiuser-ids 204,205 --start-date 2025-06-01 --end-date 2025-06-30 --base-urls https://millerbecker2.pakaneo.com https://millerbecker.pakaneo.com 
```

## 📋 Requirements

### System Requirements
- **Python 3.8+** (Python 3.9+ recommended)
- **Windows 10/11** (tested) or **macOS/Linux** (should work)
- **Internet connection** for Pakaneo access
- **Modern web browser** (Chrome, Firefox, Edge, Safari)

### Pakaneo Requirements
- **Valid Pakaneo account** with billing data access
- **Customer API User IDs** you want to download data for
- **Login credentials** (email and password)

## 🔧 Configuration

### Environment Variables (`.env` file)
```env
EMAIL=your_email@example.com
PASSWORD=your_password
```

### Advanced Settings (`input/base_input.py`)
- `BASE_URLS`: List of Pakaneo platform URLs to try
- `MAX_CONCURRENT_REQUESTS`: Number of simultaneous downloads (default: 20)
- `MAX_BROWSER_SESSIONS`: Number of concurrent browser sessions (default: 5)

### Customer Management
Use the web interface to:
- Add new customers with ID and name
- Edit existing customer information
- Delete customers you no longer need
- Search and filter your customer list

## 📁 Output Structure

```
PakaneoBillingAutomation/
├── billing_exports/                    # Downloaded CSV files organized by date range
│   └── 2025-08-01 to 2025-08-09/     # Each download gets its own folder
│       ├── stored_products_export_205 (2025-08-01 to 2025-08-09).csv
│       ├── packed_orders_export_205 (2025-08-01 to 2025-08-09).csv
│       └── download_report_2025-08-01_to_2025-08-09.json
├── logs/General_Logs/                  # System logs for troubleshooting
├── input/customers.json               # Your customer database
├── auth_details.json                  # Saved authentication data
└── custom_profile/                    # Browser session data
```

## 🔍 What Happens When You Run It

### Web Interface Flow:
1. **Customer Selection**: Choose from your saved customer list
2. **Date Range**: Pick dates using smart presets or custom range
3. **Download Process**: Real-time progress with status updates
4. **Completion**: Files organized automatically, recent downloads updated

### Behind the Scenes:
1. **Authentication Check**: Verifies if you're already logged in
2. **Auto-Login**: Opens browser and logs into Pakaneo if needed
3. **Data Collection**: Fetches available data for your customers and dates
4. **Concurrent Download**: Downloads all files simultaneously for speed
5. **File Organization**: Saves files with clear, descriptive names
6. **Report Generation**: Creates detailed JSON reports for each download

## 🛠️ Technical Architecture

### Core Components
- **Flask Web Application**: Modern, responsive user interface
- **Browser Automation**: Handles login and session management using Playwright
- **API Integration**: Communicates with Pakaneo's internal APIs using aiohttp
- **Concurrent Processing**: Downloads multiple files simultaneously with semaphore control
- **Error Recovery**: Automatic retry system with comprehensive error handling

### Security Features
- Credentials stored locally in encrypted environment files
- Session data cached securely for reuse
- No sensitive data transmitted to external servers
- Browser automation runs in isolated profile

## 📞 Support & Troubleshooting

### Common Issues

**"Authentication failed"**
- Check your email/password in `.env` file
- Verify the Pakaneo URL is correct
- Try deleting `auth_details.json` to force fresh login

**"No data found"**
- Verify customer IDs are valid and have access to billing data
- Check if date range contains actual data
- Ensure you have proper permissions in Pakaneo

**"Download failed"**
- Check internet connection stability
- System will automatically retry failed downloads
- Check logs in `logs/General_Logs/` for detailed error information

**Web interface won't open**
- Ensure no other application is using port 5000
- Try running `python app.py` directly to see error messages
- Check if virtual environment is properly activated

### Logs and Debugging
Detailed logs are saved in `logs/General_Logs/` for troubleshooting:
- `main.log`: Overall process logs
- `automation.log`: CSV download process details
- `bot.log`: Browser automation and authentication logs
- `helpers.log`: Utility function logs

### Getting Help
1. Check the logs in `logs/General_Logs/` for error details
2. Verify your `.env` file has correct credentials
3. Ensure customer IDs exist and have data for the selected date range
4. Try running with a single customer first to isolate issues

## 🏆 Benefits

- **Time Saving**: Automates hours of manual data export work
- **Reliable**: Handles errors and retries automatically with detailed reporting
- **Fast**: Concurrent downloads reduce processing time significantly
- **User-Friendly**: Modern web interface requires no technical knowledge
- **Flexible**: Both web and command-line interfaces for different use cases
- **Maintainable**: Comprehensive logging and error reporting for easy troubleshooting
- **Scalable**: Handles multiple customers and large date ranges efficiently

## 🔄 Updates and Maintenance

The system automatically:
- Manages authentication sessions
- Retries failed operations
- Logs all activities for audit trails
- Organizes files with consistent naming

For updates:
- Pull latest changes from repository
- Run `pip install -r requirements.txt` to update dependencies
- Restart the application

---

**Built with modern Python technologies for reliability, performance, and ease of use.**

*Transform your Pakaneo billing workflow from manual exports to automated efficiency.*