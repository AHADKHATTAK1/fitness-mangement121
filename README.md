# 💪 Gym Manager - Complete Gym Software

A modern, feature-rich web application for managing gym members, fees, and generating ID cards.

## ✨ Features

- ✅ **Admin Authentication** - Secure signup/login/logout
- 👥 **Member Management** - Add members with photos
- 📷 **Camera Support** - Capture photos directly from webcam
- 📁 **Photo Upload** - Upload member photos from files
- 💰 **Fee Tracking** - Record monthly fees
- 📊 **Excel Export** - Download member data as Excel
- 📄 **PDF ID Cards** - Generate printable member cards
- 🎨 **Modern UI** - Dark theme with glassmorphism effects
- 💾 **Data Persistence** - All data saved in JSON

## 🚀 Installation

1. **Install Python** (3.8 or higher recommended)

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure Environment Variables:**

   **IMPORTANT**: Create a `.env` file in the project root directory:
   
   ```bash
   # Copy the example file
   cp .env.example .env
   ```
   
   Then edit `.env` and add your actual API keys:
   
   - **FLASK_SECRET_KEY**: Generate a random secret key
     ```bash
     python -c "import secrets; print(secrets.token_hex(32))"
     ```
   
   - **STRIPE_PUBLIC_KEY & STRIPE_SECRET_KEY**: 
     - Get from https://dashboard.stripe.com/apikeys
     - Use test keys (pk_test_... and sk_test_...) for development
   
   - **GOOGLE_CLIENT_ID**: 
     - Get from https://console.cloud.google.com/apis/credentials
     - Create OAuth 2.0 Client ID for web application
   
   - **ADMIN_EMAILS**: 
     - Comma-separated list of admin email addresses
     - Example: `admin@gym.com,youremail@example.com`

   **Example `.env` file:**
   ```env
   FLASK_SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
   STRIPE_PUBLIC_KEY=pk_test_your_actual_stripe_public_key
   STRIPE_SECRET_KEY=sk_test_your_actual_stripe_secret_key
   GOOGLE_CLIENT_ID=123456789-abc.apps.googleusercontent.com
   ADMIN_EMAILS=admin@gym.com,youremail@example.com
   ```

## 🏃 Running the Application

1. **Start the server:**
```bash
python app.py
```

2. **Open your browser** and go to:
```
http://localhost:5000
```

3. **First Time Setup:**
   - Create your admin account (signup page appears on first run)
   - Login with your credentials

## 📖 Usage Guide

### Admin Authentication
- **First run**: Create admin account (username + password)
- **Subsequent runs**: Login with your credentials
- **Logout**: Click "Logout" in navigation (ogoto option)

### Adding Members
1. Click **"Add Member"** in navigation
2. Fill in member name and phone
3. Add photo (choose one):
   - 📁 Upload from file
   - 📷 Use camera to capture
4. Click **"Add Member"**

### Recording Fees
1. Click **"Fees"** in navigation
2. Select member from dropdown
3. Choose month
4. Enter amount (optional)
5. Click **"Record Payment"**

### Dashboard
- View all members
- See paid/unpaid status
- Download Excel report
- Generate PDF ID cards

### Downloads
- **Excel**: Click "Download Excel" button
- **PDF Card**: Click "Card" button next to any member

## 📁 File Structure

```
tracker software/
├── app.py                 # Main Flask application
├── gym_manager.py         # Data management class
├── requirements.txt       # Python dependencies
├── gym_data.json         # Data storage (auto-created)
├── templates/            # HTML templates
│   ├── base.html
│   ├── auth.html
│   ├── dashboard.html
│   ├── add_member.html
│   └── fees.html
└── static/
    └── uploads/          # Member photos (auto-created)
```

## 🔒 Security Notes

- ✅ **Environment Variables**: All sensitive data is now stored in `.env` file
- ⚠️ **Never commit `.env`**: The `.env` file is gitignored and should NEVER be pushed to GitHub
- 🔑 **API Keys**: Get your own Stripe and Google OAuth keys - don't use example keys in production
- 🔐 **Secret Key**: Generate a strong random secret key for Flask sessions
- 🔒 **HTTPS**: Always use HTTPS in production environment
- 🛡️ **Passwords**: Consider implementing bcrypt hashing for production use

## 🛠️ Technologies Used

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript
- **Storage**: JSON file-based
- **PDF**: ReportLab
- **Excel**: Pandas + OpenPyXL
- **Camera**: WebRTC (getUserMedia API)

## 📝 Data Storage

All data is stored in `gym_data.json`:
- Admin credentials
- Member information
- Fee records
- Photos stored in `static/uploads/`

## 🎨 Design Features

- Modern dark theme
- Glassmorphism effects
- Smooth animations
- Responsive design
- Google Fonts (Inter)
- Gradient accents

## 📱 Browser Compatibility

- Chrome/Edge (recommended)
- Firefox
- Safari
- Camera feature requires HTTPS for production deployment

Enjoy managing your gym! 💪
