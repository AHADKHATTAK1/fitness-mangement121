from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash, jsonify
from flask_compress import Compress
from werkzeug.utils import secure_filename
from gym_manager import GymManager
from auth_manager import AuthManager
import os
from datetime import datetime, timedelta
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import qrcode
import base64

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

# Enable compression for all responses
Compress(app)

# Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('gym_data', exist_ok=True)

# Initialize Auth Manager
auth_manager = AuthManager()

def get_gym():
    """Get GymManager instance for logged-in user"""
    if 'logged_in' not in session:
        return None
    username = session.get('username')
    data_file = auth_manager.get_user_data_file(username)
    return GymManager(data_file)

@app.context_processor
def inject_gym_details():
    context = {}
    gym = get_gym()
    if gym:
        details = gym.get_gym_details()
        if 'currency' not in details: details['currency'] = '$'
        context['gym_details'] = details
    else:
        context['gym_details'] = {'name': 'Gym Manager', 'logo': None, 'currency': '$'}
        
    # Inject User Plan info
    if 'logged_in' in session:
        user = auth_manager.users.get(session['username'], {})
        context['user_plan'] = user.get('plan', 'standard')
    
    return context

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    if 'logged_in' not in session:
        return redirect(url_for('auth'))
    return redirect(url_for('dashboard'))

import stripe

# STRIPE CONFIGURATION (YOU MUST REPLACE THESE WITH YOUR KEYS)
# Get them from https://dashboard.stripe.com/apikeys
app.config['STRIPE_PUBLIC_KEY'] = 'pk_test_TYooMQauvdEDq54NiTphI7jx' # Replace this!
app.config['STRIPE_SECRET_KEY'] = 'sk_test_4eC39HqLyjWDarjtT1zdp7dc' # Replace this!
stripe.api_key = app.config['STRIPE_SECRET_KEY']

@app.before_request
def check_subscription():
    # Public endpoints that don't need subscription
    public_endpoints = ['auth', 'google_login', 'static', 'subscription', 'logout', 'create_checkout_session', 'payment_success', 'payment_cancel']
    
    if request.endpoint in public_endpoints or not session.get('logged_in'):
        return

    username = session.get('username')
    if not auth_manager.is_subscription_active(username):
        session['needs_payment'] = True
        return redirect(url_for('subscription'))

@app.route('/subscription')
def subscription():
    username = session.get('username')
    if auth_manager.is_subscription_active(username):
        return redirect(url_for('dashboard'))
        
    # Check if user is pending approval
    user = auth_manager.users.get(username, {})
    if user.get('subscription_status') == 'pending':
        return render_template('payment_pending.html')
        
    return render_template('payment_select.html', key=app.config['STRIPE_PUBLIC_KEY'])

@app.route('/create_checkout_session', methods=['POST'])
def create_checkout_session():
    username = session.get('username')
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Gym Manager Pro Subscription',
                        'images': ['https://i.imgur.com/EHyR2nP.png'],
                    },
                    'unit_amount': 6000, # $60.00
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('payment_cancel', _external=True),
            client_reference_id=username,
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        flash(f'Error creating payment session: {str(e)}', 'error')
        return redirect(url_for('subscription'))

@app.route('/payment_success')
def payment_success():
    username = session.get('username')
    if not username: return redirect(url_for('auth'))
    
    # In a production app, verify the session_id with Stripe here
    # session_id = request.args.get('session_id')
    
    # Renew subscription
    auth_manager.renew_subscription(username)
    flash('Payment Successful! Thank you for your subscription. ✅', 'success')
    session.pop('needs_payment', None)
    return redirect(url_for('dashboard'))

@app.route('/payment_cancel')
def payment_cancel():
    flash('Payment cancelled.', 'info')
    return redirect(url_for('subscription'))

@app.route('/manual_payment', methods=['GET', 'POST'])
def manual_payment():
    username = session.get('username')
    if not username: return redirect(url_for('auth'))
    
    if request.method == 'POST':
        if 'payment_proof' in request.files:
            file = request.files['payment_proof']
            if file and file.filename:
                filename = secure_filename(f"proof_{username}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Update user status to pending
                auth_manager.set_payment_pending(username, filename)
                
                flash('Proof uploaded! Waiting for admin approval.', 'success')
                return redirect(url_for('subscription'))
                
    return render_template('payment_manual.html')

# Admin Access Control
ADMIN_EMAILS = ['admin@gym.com', 'mashalkhttak@gmail.com', 'test@admin.com']

@app.route('/super_admin')
def super_admin():
    if session.get('username') not in ADMIN_EMAILS:
        flash('Access Denied: Super Admin only.', 'error')
        return redirect(url_for('dashboard'))
    
    pending_users = auth_manager.get_pending_approvals()
    return render_template('super_admin.html', pending_users=pending_users)

@app.route('/approve_payment/<target_username>')
def approve_payment(target_username):
    if session.get('username') not in ADMIN_EMAILS:
        flash('Access Denied.', 'error')
        return redirect(url_for('dashboard'))
        
    # Verify admin here logic
    if auth_manager.approve_manual_payment(target_username):
        flash(f'User {target_username} approved!', 'success')
        
        # Optional: Add a real Stripe payment record or just the manual one (already done in AuthManager)
    else:
        flash('Approval failed.', 'error')
    return redirect(url_for('super_admin'))

@app.route('/auth', methods=['GET', 'POST'])
def auth():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        action = request.form.get('action')
        referral_code = request.form.get('referral_code')
        
        if action == 'signup':
            if auth_manager.create_user(username, password, referral_code):
                flash('Account created successfully! Please login.', 'success')
                return redirect(url_for('auth'))
            else:
                flash('Username already exists!', 'error')
        
        elif action == 'login':
            if auth_manager.verify_user(username, password):
                session['logged_in'] = True
                session['username'] = username
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid credentials!', 'error')
    
    return render_template('auth.html')

@app.route('/google_login', methods=['POST'])
def google_login():
    token = request.form.get('credential')
    try:
        # Specify the CLIENT_ID of the app that accesses the backend:
        client_id = "540149972190-pmr5d61g3jpj9j6c7h0qi4vs3vu6i0lr.apps.googleusercontent.com"
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), client_id)

        # ID token is valid. Get the user's Google Account ID from the decoded token.
        email = idinfo['email']

        # Ensure user exists in our system
        if not auth_manager.user_exists(email):
            # Auto-signup with "GOOGLE" referral/plan logic if needed, or default free?
            # User asked for: "referral mera jo hoga wo bs free ho single time use"
            # We'll treat Google signups as standard/free for now.
            auth_manager.create_user(email, "GOOGLE_AUTH_USER", referral_code="GOOGLE_SIGNUP")
            flash(f'Account created with Google! Welcome, {email}.', 'success')

        session['logged_in'] = True
        session['username'] = email

        if auth_manager.user_exists(email):
             flash(f'Logged in as {email}!', 'success')

        return redirect(url_for('dashboard'))
    except ValueError:
        # Invalid token
        flash('Google Login failed! Invalid token.', 'error')
        return redirect(url_for('auth'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/schedule', methods=['GET', 'POST'])
def schedule():
    gym = get_gym()
    if not gym: return redirect(url_for('auth'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        day = request.form.get('day')
        time = request.form.get('time')
        instructor = request.form.get('instructor')
        capacity = request.form.get('capacity')
        
        gym.add_class(name, day, time, instructor, capacity)
        flash('Class added successfully!', 'success')
        return redirect(url_for('schedule'))
        
    return render_template('schedule.html', classes=gym.get_classes(), members=gym.get_all_members())

@app.route('/expenses', methods=['GET', 'POST'])
def expenses():
    gym = get_gym()
    if not gym: return redirect(url_for('auth'))
    
    if request.method == 'POST':
        category = request.form.get('category')
        amount = float(request.form.get('amount') or 0)
        date = request.form.get('date')
        description = request.form.get('description', '')
        
        if gym.add_expense(category, amount, date, description):
            flash(f'Expense of {amount} recorded successfully!', 'success')
        else:
            flash('Failed to add expense!', 'error')
        
        return redirect(url_for('expenses'))
    
    # Get current month
    current_month = datetime.now().strftime('%Y-%m')
    
    # Get expenses for current month
    expenses_list = gym.get_expenses(current_month)
    
    # Calculate P&L
    pl_data = gym.calculate_profit_loss(current_month)
    
    # Available months for dropdown
    available_months = []
    for i in range(12):
        month_date = datetime.now() - timedelta(days=30*i)
        available_months.append({
            'value': month_date.strftime('%Y-%m'),
            'label': month_date.strftime('%B %Y')
        })
    
    return render_template('expenses.html',
                         expenses=expenses_list,
                         pl_data=pl_data,
                         current_month=current_month,
                         available_months=available_months,
                         gym_details=gym.get_gym_details())

@app.route('/delete_expense/<expense_id>', methods=['POST'])
def delete_expense(expense_id):
    gym = get_gym()
    if not gym: return redirect(url_for('auth'))
    
    if gym.delete_expense(expense_id):
        flash('Expense deleted successfully!', 'success')
    else:
        flash('Failed to delete expense!', 'error')
    
    return redirect(url_for('expenses'))

@app.route('/book_class/<class_id>', methods=['POST'])
def book_class(class_id):
    gym = get_gym()
    if not gym: return redirect(url_for('auth'))
    
    member_id = request.form.get('member_id')
    if gym.book_class(member_id, class_id):
        flash('Booking confirmed!', 'success')
    else:
        flash('Booking failed (Full or invalid)', 'error')
        
    return redirect(url_for('schedule'))

@app.route('/reports')
def reports():
    gym = get_gym()
    if not gym: return redirect(url_for('auth'))
    
    # Calculate stats
    total_members = len(gym.get_all_members())
    
    # Current month revenue
    current_month = datetime.now().strftime('%Y-%m')
    status = gym.get_payment_status(current_month)
    monthly_revenue = sum(m.get('amount', 0) for m in status['paid'])
    
    # Total check-ins
    total_checkins = 0
    if 'attendance' in gym.data:
        for visits in gym.data['attendance'].values():
            total_checkins += len(visits)
    
    # Revenue trend (last 6 months)
    revenue_months = []
    revenue_data = []
    for i in range(5, -1, -1):
        month = (datetime.now().replace(day=1) - timedelta(days=30*i)).strftime('%Y-%m')
        revenue_months.append(month)
        month_status = gym.get_payment_status(month)
        revenue_data.append(sum(m.get('amount', 0) for m in month_status['paid']))
    
    return render_template('reports.html',
                         total_members=total_members,
                         monthly_revenue=monthly_revenue,
                         total_checkins=total_checkins,
                         paid_count=len(status['paid']),
                         unpaid_count=len(status['unpaid']),
                         revenue_months=revenue_months,
                         revenue_data=revenue_data)

@app.route('/reset_admin')
def reset_admin():
    gym = get_gym()
    if gym:
        gym.reset_data()
        flash('All your data has been reset!', 'success')
    # Use referer check or just redirect dashboard to force re-login check? 
    # Actually, reset_data keeps the file but empties content. User is still logged in.
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    gym = get_gym()
    if not gym: return redirect(url_for('auth'))

    # Generate months for dropdown
    current_date = datetime.now()
    # Snap to first of current month, then go back 12 months
    start_date = current_date.replace(day=1) - pd.DateOffset(months=12)
    
    # Generate range and format as (value, label) tuples (12 past + current + 24 future = 37)
    dates = pd.date_range(start=start_date, periods=37, freq='MS')
    # Check if month requested
    selected_month = request.args.get('month')
    if not selected_month:
        current_month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    status = gym.get_payment_status(current_month)
    
    # Calculate revenue
    revenue = sum(m.get('amount', 0) for m in status['paid'])
    
    # Calculate revenue change vs last month
    last_month = (datetime.strptime(current_month, '%Y-%m') - timedelta(days=30)).strftime('%Y-%m')
    last_status = gym.get_payment_status(last_month)
    last_revenue = sum(m.get('amount', 0) for m in last_status['paid'])
    
    revenue_change = 0
    if last_revenue > 0:
        revenue_change = round(((revenue - last_revenue) / last_revenue) * 100, 1)
    
    # Count expiring memberships (next 3 days)
    expiring_count = 0
    today = datetime.now().date()
    all_members = gym.get_all_members()
    
    # Check if it's a dict or list
    if isinstance(all_members, dict):
        members_to_check = all_members.values()
    else:
        members_to_check = all_members
    
    for member in members_to_check:
        # Check if trial is expiring
        if member.get('trial_end'):
            trial_end = datetime.strptime(member['trial_end'], '%Y-%m-%d').date()
            days_until_expiry = (trial_end - today).days
            if 0 <= days_until_expiry <= 3:
                expiring_count += 1
    
    # Total members
    total_members = len(gym.get_all_members())
    
    # Available months for selector
    available_months = []
    for i in range(12):
        month_date = datetime.now() - timedelta(days=30*i)
        available_months.append({
            'value': month_date.strftime('%Y-%m'),
            'label': month_date.strftime('%B %Y')
        })
    
    return render_template('dashboard.html', 
                         paid=status['paid'], 
                         unpaid=status['unpaid'],
                         revenue=revenue,
                         revenue_change=revenue_change,
                         total_members=total_members,
                         expiring_count=expiring_count,
                         current_month=current_month,
                         available_months=available_months,
                         gym_details=gym.get_gym_details())

@app.route('/add_member', methods=['GET', 'POST'])
def add_member():
    gym = get_gym()
    if not gym: return redirect(url_for('auth'))
    
    # Generate months for dropdown
    current_date = datetime.now()
    # Snap to first of current month, then go back 12 months
    start_date = current_date.replace(day=1) - pd.DateOffset(months=12)
    
    # Generate range and format as (value, label) tuples (12 past + current + 24 future = 37)
    dates = pd.date_range(start=start_date, periods=37, freq='MS')
    available_months = [{'value': d.strftime('%Y-%m'), 'label': d.strftime('%B %Y')} for d in dates][::-1]
    
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        membership_type = request.form.get('membership_type', 'Gym')
        
        # Initial Payment data
        initial_month = request.form.get('initial_month')
        try:
            initial_amount = float(request.form.get('initial_amount', 0) or 0)
        except ValueError:
            initial_amount = 0
            
        photo_path = None
        
        # Handle file upload
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                photo_path = filename
        
        # Handle camera capture (base64 data)
        elif 'camera_photo' in request.form and request.form['camera_photo']:
            import base64
            photo_data = request.form['camera_photo'].split(',')[1]
            photo_bytes = base64.b64decode(photo_data)
            filename = f"camera_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            with open(filepath, 'wb') as f:
                f.write(photo_bytes)
            photo_path = filename
        
        try:
            membership_type = request.form.get('membership_type', 'Gym')
            joined_date = request.form.get('joined_date')
            email = request.form.get('email')
            start_trial = request.form.get('start_trial') == 'on'
            
            # If initial payment overrides trial, we can decide logic.
            # Here: If they pay, trial is False. If they don't and check trial, it's True.
            if initial_amount > 0:
                start_trial = False
                
            member_id = gym.add_member(name, phone, photo_path, membership_type, joined_date, is_trial=start_trial, email=email)
            
            # Record initial payment if amount > 0
            if initial_amount > 0 and initial_month:
                gym.pay_fee(member_id, initial_month, initial_amount)
                flash(f'Member {name} added and payment recorded for {initial_month}!', 'success')
            elif start_trial:
                flash(f'Member {name} added on 3-Day Free Trial! 🆓', 'success')
            else:
                flash(f'Member {name} added successfully! (ID: {member_id})', 'success')
                
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash(f'Error adding member: {str(e)}', 'error')
            return redirect(url_for('add_member'))
    
    return render_template('add_member.html', 
                         available_months=available_months, 
                         current_month=current_date.strftime('%Y-%m'),
                         today=current_date.strftime('%Y-%m-%d'))

@app.route('/fees', methods=['GET', 'POST'])
def fees():
    gym = get_gym()
    if not gym: return redirect(url_for('auth'))
    
    # Generate months for dropdown (12 past + current + 24 future = 37)
    current_date = datetime.now()
    start_date = current_date.replace(day=1) - pd.DateOffset(months=12)
    dates = pd.date_range(start=start_date, periods=37, freq='MS')
    available_months = [{'value': d.strftime('%Y-%m'), 'label': d.strftime('%B %Y')} for d in dates][::-1]
    
    if request.method == 'POST':
        member_id = request.form.get('member_id')
        month = request.form.get('month')
        amount = float(request.form.get('amount') or 0)
        
        if gym.pay_fee(member_id, month, amount):
            member = gym.get_member(member_id)
            flash(f'Fee recorded for {member["name"]} for {month}', 'success')
        else:
            flash('Member not found!', 'error')
        
        return redirect(url_for('fees'))
    
    members = gym.get_all_members()
    current_month = datetime.now().strftime('%Y-%m')
    return render_template('fees.html', members=members, current_month=current_month, available_months=available_months)

@app.route('/download_excel')
def download_excel():
    gym = get_gym()
    if not gym: return redirect(url_for('auth'))
    
    current_month = datetime.now().strftime('%Y-%m')
    status = gym.get_payment_status(current_month)
    
    # Prepare data for Excel
    data = []
    for member in status['paid']:
        data.append({
            'ID': member['id'],
            'Name': member['name'],
            'Phone': member['phone'],
            'Status': 'PAID',
            'Last Payment': member.get('last_paid', 'N/A')
        })
    
    for member in status['unpaid']:
        data.append({
            'ID': member['id'],
            'Name': member['name'],
            'Phone': member['phone'],
            'Status': 'UNPAID',
            'Last Payment': 'N/A'
        })
    
    df = pd.DataFrame(data)
    
    # Create Excel file
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Members')
    output.seek(0)
    
    filename = f'gym_members_{current_month}.xlsx'
    return send_file(output, download_name=filename, as_attachment=True)

@app.route('/card/<member_id>')
def generate_card(member_id):
    gym = get_gym()
    if not gym: return redirect(url_for('auth'))
    
    member = gym.get_member(member_id)
    if not member:
        flash('Member not found!', 'error')
        return redirect(url_for('dashboard'))
    
    # Create PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Card background
    c.setFillColorRGB(0.1, 0.1, 0.2)
    c.rect(50, height - 350, 300, 200, fill=True)
    
    # Title
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(70, height - 180, "GYM MEMBER CARD")
    
    # Member photo
    if member.get('photo'):
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], member['photo'])
        if os.path.exists(photo_path):
            try:
                img = ImageReader(photo_path)
                c.drawImage(img, 70, height - 330, width=80, height=100, preserveAspectRatio=True)
            except:
                pass
    
    # QR Code
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(member_id)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Save QR to buffer to draw
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer)
    qr_buffer.seek(0)
    
    # Draw QR Code on card
    c.drawImage(ImageReader(qr_buffer), 270, height - 330, width=70, height=70)
    
    # Member details
    c.setFont("Helvetica", 12)
    c.drawString(170, height - 230, f"ID: {member['id']}")
    c.drawString(170, height - 250, f"Name: {member['name']}")
    c.drawString(170, height - 270, f"Phone: {member['phone']}")
    c.drawString(170, height - 290, f"Joined: {member['joined_date']}")
    
    c.save()
    buffer.seek(0)
    
    return send_file(buffer, download_name=f'card_{member_id}.pdf', as_attachment=True, mimetype='application/pdf')

@app.route('/scanner')
def scanner():
    gym = get_gym()
    if not gym: return redirect(url_for('auth'))
    return render_template('scanner.html')

@app.route('/scan_check/<member_id>')
def scan_check(member_id):
    gym = get_gym()
    if not gym: return redirect(url_for('auth'))
    
    # Determine status
    current_month = datetime.now().strftime('%Y-%m')
    is_paid = gym.is_fee_paid(member_id, current_month)
    member = gym.get_member(member_id)
    
    if not member:
        flash('Invalid Member ID!', 'error')
        return redirect(url_for('scanner'))
        
    status = 'GRANTED' if is_paid else 'DENIED'
    status = ''
    if is_paid:
        status = 'ACCESS GRANTED'
        # Log attendance automatically
        gym.log_attendance(member_id)
    # Special check for trial
    elif not is_paid and member.get('is_trial'):
        today = datetime.now().strftime('%Y-%m-%d')
        if member.get('trial_end_date') >= today:
             status = 'TRIAL'
        else:
            status = 'ACCESS DENIED - TRIAL EXPIRED'
    else:
        status = 'ACCESS DENIED - FEE PENDING'
    
    # Get attendance history
    attendance_history = gym.get_attendance(member_id)
    
    # Get payment details
    payment_history = gym.get_payment_history(member_id)
    last_payment = payment_history[0] if payment_history else None
             
    return render_template('scan_result.html', 
                         member=member, 
                         status=status, 
                         month=current_month,
                         attendance_history=attendance_history,
                         last_payment=last_payment,
                         is_paid=is_paid,
                         gym_details=gym.get_gym_details())

@app.route('/member/<member_id>', methods=['GET', 'POST'])
def member_details(member_id):
    gym = get_gym()
    if not gym: return redirect(url_for('auth'))
    
    member = gym.get_member(member_id)
    if not member:
        flash('Member not found!', 'error')
        return redirect(url_for('dashboard'))
        
    attendance_history = gym.get_attendance(member_id)
        
    if request.method == 'POST':
        month = request.form.get('month')
        amount = float(request.form.get('amount') or 0)
        payment_date = request.form.get('payment_date')
        notes = request.form.get('notes')
        
        if gym.pay_fee(member_id, month, amount, payment_date, notes):
            flash(f'Payment recorded successfully for {month}!', 'success')
        else:
            flash('Payment failed!', 'error')
        return redirect(url_for('member_details', member_id=member_id))
    
        return redirect(url_for('member_details', member_id=member_id))
    
    history = gym.get_member_fee_history(member_id)
    
    # Generate months for payment dropdown (12 past + current + 24 future = 37)
    current_date = datetime.now()
    start_date = current_date.replace(day=1) - pd.DateOffset(months=12)
    dates = pd.date_range(start=start_date, periods=37, freq='MS')
    available_months = [{'value': d.strftime('%Y-%m'), 'label': d.strftime('%B %Y')} for d in dates][::-1]
    
    return render_template('member_details.html', 
                         member=member, 
                         gym_details=gym.get_gym_details(), 
                         history=gym.get_payment_history(member_id),
                         attendance_history=attendance_history,
                         current_month=datetime.now().strftime('%Y-%m'),
                         today=datetime.now().strftime('%Y-%m-%d'),
                         available_months=available_months)

@app.route('/member/<member_id>/delete_fee/<month>', methods=['POST'])
def delete_fee_record(member_id, month):
    gym = get_gym()
    if not gym: return redirect(url_for('auth'))
    
    if gym.delete_fee(member_id, month):
        flash(f'Payment for {month} deleted!', 'success')
    else:
        flash('Delete failed!', 'error')
        
    return redirect(url_for('member_details', member_id=member_id))

@app.route('/member/<member_id>/edit_fee/<month>', methods=['GET', 'POST'])
def edit_fee_record(member_id, month):
    gym = get_gym()
    if not gym: return redirect(url_for('auth'))
    
    member = gym.get_member(member_id)
    if not member or not gym.is_fee_paid(member_id, month):
        flash('Fee record not found!', 'error')
        return redirect(url_for('member_details', member_id=member_id))
        
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount') or 0)
            date = request.form.get('date') # Expecting YYYY-MM-DD HH:MM:SS or just date
            
            if gym.update_fee(member_id, month, amount, date):
                flash(f'Payment for {month} updated!', 'success')
                return redirect(url_for('member_details', member_id=member_id))
            else:
                flash('Update failed!', 'error')
        except ValueError:
            flash('Invalid amount!', 'error')
            
    # Get current fee data
    fee_info = gym.data['fees'][member_id][month]
    return render_template('edit_fee.html', member=member, month=month, fee=fee_info)

@app.route('/member/<member_id>/edit', methods=['GET', 'POST'])
def edit_member(member_id):
    gym = get_gym()
    if not gym: return redirect(url_for('auth'))
    
    member = gym.get_member(member_id)
    if not member:
        flash('Member not found!', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        membership_type = request.form.get('membership_type')
        joined_date = request.form.get('joined_date')
        
        if gym.update_member(member_id, name, phone, membership_type, joined_date, email):
            flash('Member updated successfully!', 'success')
            return redirect(url_for('member_details', member_id=member_id))
        else:
            flash('Update failed!', 'error')
    
    return render_template('edit_member.html', member=member)

@app.route('/member/<member_id>/delete', methods=['POST'])
def delete_member(member_id):
    gym = get_gym()
    if not gym: return redirect(url_for('auth'))
    
    if gym.delete_member(member_id):
        flash('Member deleted successfully!', 'success')
    else:
        flash('Delete failed!', 'error')
        
    return redirect(url_for('dashboard'))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    gym = get_gym()
    if not gym: return redirect(url_for('auth'))
    
    if request.method == 'POST':
        name = request.form.get('gym_name')
        currency = request.form.get('currency', '$')
        logo_path = None
        
        if 'gym_logo' in request.files:
            file = request.files['gym_logo']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"logo_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                logo_path = filename
        
        if gym.update_gym_details(name, logo_path, currency):
            flash('Gym settings updated successfully!', 'success')
        else:
            flash('Failed to update settings!', 'error')
        return redirect(url_for('settings'))
            
    payments = []
    if 'logged_in' in session:
        user = auth_manager.users.get(session['username'], {})
        payments = user.get('payments', [])
        
    return render_template('settings.html', details=gym.get_gym_details(), payments=payments)

@app.route('/receipt/<member_id>/<month>')
def generate_receipt(member_id, month):
    gym = get_gym()
    if not gym: return redirect(url_for('auth'))
    
    member = gym.get_member(member_id)
    if not member or not gym.is_fee_paid(member_id, month):
        flash('Fee record not found!', 'error')
        return redirect(url_for('member_details', member_id=member_id))
    
    # Get fee data
    # We need to access fee details directly since get_member doesn't have it
    # This is a bit of a hack, optimally we should have a get_fee method
    if member_id in gym.data['fees'] and month in gym.data['fees'][member_id]:
        fee_info = gym.data['fees'][member_id][month]
    else:
        return redirect(url_for('dashboard'))

    # Create PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    gym_details = gym.get_gym_details()
    
    # Header
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, height - 50, gym_details['name'])
    
    if gym_details.get('logo'):
        logo_path = os.path.join(app.config['UPLOAD_FOLDER'], gym_details['logo'])
        if os.path.exists(logo_path):
            try:
                img = ImageReader(logo_path)
                c.drawImage(img, width - 100, height - 80, width=50, height=50, preserveAspectRatio=True)
            except:
                pass

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 100, "PAYMENT RECEIPT")
    
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 130, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    c.drawString(50, height - 150, f"Receipt #: {member_id}-{month.replace('-', '')}")
    
    # Details
    y = height - 200
    c.drawString(50, y, f"Member: {member['name']} (ID: {member_id})")
    c.drawString(50, y - 20, f"Month Paid: {month}")
    c.drawString(50, y - 40, f"Amount Paid: ${fee_info['amount']}")
    c.drawString(50, y - 60, f"Payment Date: {fee_info['paid_date']}")
    
    # Footer
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, y - 120, "Thank you for your business!")
    
    c.save()
    buffer.seek(0)
    
    return send_file(buffer, download_name=f'receipt_{member_id}_{month}.pdf', as_attachment=True, mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
