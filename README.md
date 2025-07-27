# Pakaneo Billing Automation

An intelligent automation system that downloads billing data from your Pakaneo platform automatically. Simply specify which users and date range you need - the system handles everything else.

## 🎯 What This Does

This tool automatically:
- **Logs into your Pakaneo account** (handles authentication seamlessly)
- **Downloads billing data** for specific API users and date ranges
- **Saves organized CSV files** with descriptive names
- **Handles errors automatically** (expired sessions, network issues, etc.)
- **Runs multiple downloads simultaneously** for faster processing

## ✨ Key Features

### 🔐 **Smart Authentication**
- Automatically handles login using your credentials
- Remembers session data to avoid repeated logins
- Auto-refreshes expired tokens without interruption

### 📊 **Flexible Data Export**
- Download data for any API user ID(s)
- Specify custom date ranges
- Supports multiple data types: stored products, packed orders, etc.

### ⚡ **High Performance**
- Downloads up to 20 files simultaneously
- Intelligent retry system for failed downloads
- Progress tracking and detailed logging

### 🛡️ **Robust Error Handling**
- Automatically recovers from network issues
- Handles expired authentication tokens
- Comprehensive logging for troubleshooting

## 🚀 Quick Start

### 1. Setup (One-time)

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install browser for automation
playwright install chromium

# Create your credentials file
copy .env.example .env
# Edit .env with your Pakaneo login details
```

### 2. Usage

**Basic command structure:**
```bash
python main.py --apiuser-ids [USER_IDS] --start-date [START] --end-date [END]
```

**Examples:**

```bash
# Download data for multiple users
python main.py --apiuser-ids 204,205,206 --start-date 2025-06-01 --end-date 2025-06-30

# Download data for single user
python main.py --apiuser-ids 207 --start-date 2025-07-01 --end-date 2025-07-15

# Use different Pakaneo URL
python main.py --apiuser-ids 204,205 --start-date 2025-06-01 --end-date 2025-06-30 --base-url https://millerbecker.pakaneo.com
```

### 3. Results

Downloaded files are saved in `billing_exports/` with descriptive names:
- `stored_products_export_204 (2025-06-01 to 2025-06-30).csv`
- `packed_orders_export_205 (2025-06-01 to 2025-06-30).csv`

## 📋 Requirements

- **API User IDs**: The specific user IDs you want to download data for
- **Date Range**: Start and end dates in YYYY-MM-DD format
- **Credentials**: Your Pakaneo login email and password (stored in `.env` file)

## 🔧 Configuration

### Environment Variables (`.env` file)
```env
EMAIL=your_email@example.com
PASSWORD=your_password
```

### Advanced Settings (`input/base_input.py`)
- `BASE_URL`: Your Pakaneo platform URL
- `MAX_CONCURRENT_REQUESTS`: Number of simultaneous downloads (default: 20)

## 📁 Output Structure

```
PakaneoBillingAutomation/
├── billing_exports/                # Downloaded CSV files
├── logs/general_Logs/              # System logs for troubleshooting
├── auth_details.json              # Saved authentication data
└── custom_profile/                 # Browser session data
```

## 🔍 What Happens When You Run It

1. **Authentication Check**: Verifies if you're already logged in
2. **Auto-Login**: If needed, opens browser and logs into Pakaneo automatically
3. **Data Collection**: Fetches available data for your specified users and dates
4. **Concurrent Download**: Downloads all files simultaneously for speed
5. **File Organization**: Saves files with clear, descriptive names
6. **Completion Report**: Shows success/failure summary

## 🛠️ Technical Architecture

### Core Components
- **Browser Automation**: Handles login and session management
- **API Integration**: Communicates with Pakaneo's internal APIs
- **Concurrent Processing**: Downloads multiple files simultaneously
- **Error Recovery**: Automatic retry and token refresh systems

### Security Features
- Credentials stored locally in encrypted format
- Session data cached securely
- No sensitive data transmitted externally

## 📞 Support

### Common Issues

**"Authentication failed"**
- Check your email/password in `.env` file
- Verify the Pakaneo URL is correct

**"No data found"**
- Verify API user IDs are valid
- Check if date range contains data

**"Download failed"**
- Check internet connection
- System will automatically retry failed downloads

### Logs
Detailed logs are saved in `logs/general_Logs/` for troubleshooting:
- `main.log`: Overall process logs
- `automation.log`: Download process details
- `bot.log`: Authentication process logs

## 🏆 Benefits

- **Time Saving**: Automates manual data export process
- **Reliable**: Handles errors and retries automatically  
- **Fast**: Concurrent downloads reduce processing time
- **User-Friendly**: Simple command-line interface
- **Maintainable**: Comprehensive logging for issue resolution

---

**Built with modern Python technologies for reliability and performance.**