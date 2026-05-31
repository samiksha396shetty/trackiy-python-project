import csv

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    make_response
)

from flask_sqlalchemy import SQLAlchemy

from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from reportlab.pdfgen import canvas

from io import BytesIO


# =========================
# FLASK APP
# =========================

app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret123'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'


db = SQLAlchemy(app)


# =========================
# LOGIN MANAGER
# =========================

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):

    return User.query.get(int(user_id))


# =========================
# DATABASE TABLES
# =========================

class User(UserMixin, db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100)
    )

    email = db.Column(
        db.String(100),
        unique=True
    )

    password = db.Column(
        db.String(200)
    )


class Transaction(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    title = db.Column(
        db.String(100)
    )

    amount = db.Column(
        db.Float
    )

    category = db.Column(
        db.String(50)
    )

    type = db.Column(
        db.String(20)
    )

    date = db.Column(
        db.String(50)
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id')
    )


# =========================
# HOME PAGE
# =========================

@app.route('/')
def home():

    return render_template('home.html')


# =========================
# SIGNUP PAGE
# =========================

@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        name = request.form['name']

        email = request.form['email']

        password = generate_password_hash(
            request.form['password']
        )

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:

            flash(
                'Email already exists!',
                'danger'
            )

            return redirect(
                url_for('signup')
            )

        new_user = User(

            name=name,

            email=email,

            password=password

        )

        db.session.add(new_user)

        db.session.commit()

        flash(
            'Account created successfully!',
            'success'
        )

        return redirect(
            url_for('login')
        )

    return render_template('signup.html')


# =========================
# LOGIN PAGE
# =========================

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']

        password = request.form['password']

        user = User.query.filter_by(
            email=email
        ).first()

        if user and check_password_hash(
            user.password,
            password
        ):

            login_user(user)

            flash(
                'Login successful!',
                'success'
            )

            return redirect(
                url_for('dashboard')
            )

        else:

            flash(
                'Invalid email or password!',
                'danger'
            )

    return render_template('login.html')


# =========================
# DASHBOARD
# =========================

@app.route('/dashboard')
@login_required
def dashboard():

    search = request.args.get(
        'search',
        ''
    )

    selected_date = request.args.get(
        'date',
        ''
    )

    filter_type = request.args.get(
        'type',
        'All'
    )

    page = request.args.get(
        'page',
        1,
        type=int
    )

    # =========================
    # BASE QUERY
    # =========================

    transactions_query = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.title.contains(search)
    )

    # =========================
    # DATE FILTER
    # =========================

    if selected_date != '':

        transactions_query = transactions_query.filter(
            Transaction.date == selected_date
        )

    # =========================
    # TYPE FILTER
    # =========================

    if filter_type != 'All':

        transactions_query = transactions_query.filter(
            Transaction.type == filter_type
        )

    # =========================
    # ALL TRANSACTIONS
    # =========================

    all_transactions = transactions_query.order_by(
        Transaction.id.desc()
    ).all()

    # =========================
    # PAGINATION
    # =========================

    transactions = transactions_query.order_by(
        Transaction.id.desc()
    ).paginate(
        page=page,
        per_page=5
    )

    # =========================
    # TOTALS
    # =========================

    total_income = 0

    total_expense = 0

    for transaction in all_transactions:

        if transaction.type == 'Income':

            total_income += float(
                transaction.amount
            )

        else:

            total_expense += float(
                transaction.amount
            )

    total_balance = (
        total_income - total_expense
    )

    # =========================
    # EXTRA STATISTICS
    # =========================

    total_transactions = len(
        all_transactions
    )

    highest_expense = 0

    highest_income = 0

    for transaction in all_transactions:

        if transaction.type == 'Expense':

            if float(transaction.amount) > highest_expense:

                highest_expense = float(
                    transaction.amount
                )

        else:

            if float(transaction.amount) > highest_income:

                highest_income = float(
                    transaction.amount
                )

    # =========================
    # EXPENSE WARNING
    # =========================

    expense_limit = 10000

    warning_message = None

    if total_expense > expense_limit:

        warning_message = (
            f"Warning! Your expenses exceeded ₹{expense_limit}"
        )

    # =========================
    # MONTHLY GRAPH DATA
    # =========================

    monthly_labels = []

    monthly_amounts = []

    for transaction in all_transactions:

        month = transaction.date[:7]

        if month not in monthly_labels:

            monthly_labels.append(month)

            monthly_amounts.append(0)

        index = monthly_labels.index(month)

        if transaction.type == 'Expense':

            monthly_amounts[index] += float(
                transaction.amount
            )

    # =========================
    # CATEGORY GRAPH DATA
    # =========================

    category_data = {}

    for transaction in all_transactions:

        if transaction.type == 'Expense':

            category = transaction.category

            if category not in category_data:

                category_data[category] = 0

            category_data[category] += float(
                transaction.amount
            )

    category_labels = list(
        category_data.keys()
    )

    category_amounts = list(
        category_data.values()
    )

    return render_template(

        'dashboard.html',

        transactions=transactions,

        total_income=total_income,

        total_expense=total_expense,

        total_balance=total_balance,

        monthly_labels=monthly_labels,

        monthly_amounts=monthly_amounts,

        category_labels=category_labels,

        category_amounts=category_amounts,

        filter_type=filter_type,

        selected_date=selected_date,

        total_transactions=total_transactions,

        warning_message=warning_message,

        highest_expense=highest_expense,

        highest_income=highest_income

    )


# =========================
# ADD TRANSACTION
# =========================

@app.route(
    '/add_transaction',
    methods=['GET', 'POST']
)
@login_required
def add_transaction():

    if request.method == 'POST':

        transaction = Transaction(

            title=request.form['title'],

            amount=request.form['amount'],

            category=request.form['category'],

            type=request.form['type'],

            date=request.form['date'],

            user_id=current_user.id

        )

        db.session.add(transaction)

        db.session.commit()

        flash(
            'Transaction added successfully!',
            'success'
        )

        return redirect(
            url_for('dashboard')
        )

    return render_template(
        'add_transaction.html'
    )


# =========================
# DELETE TRANSACTION
# =========================

@app.route('/delete_transaction/<int:id>')
@login_required
def delete_transaction(id):

    transaction = Transaction.query.get_or_404(id)

    if transaction.user_id != current_user.id:

        return "Unauthorized Access"

    db.session.delete(transaction)

    db.session.commit()

    flash(
        'Transaction deleted successfully!',
        'danger'
    )

    return redirect(
        url_for('dashboard')
    )


# =========================
# EDIT TRANSACTION
# =========================

@app.route(
    '/edit_transaction/<int:id>',
    methods=['GET', 'POST']
)
@login_required
def edit_transaction(id):

    transaction = Transaction.query.get_or_404(id)

    if transaction.user_id != current_user.id:

        return "Unauthorized Access"

    if request.method == 'POST':

        transaction.title = request.form['title']

        transaction.amount = request.form['amount']

        transaction.category = request.form['category']

        transaction.type = request.form['type']

        transaction.date = request.form['date']

        db.session.commit()

        flash(
            'Transaction updated successfully!',
            'success'
        )

        return redirect(
            url_for('dashboard')
        )

    return render_template(

        'edit_transaction.html',

        transaction=transaction

    )


# =========================
# CSV DOWNLOAD
# =========================

@app.route('/download_csv')
@login_required
def download_csv():

    transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).all()

    output = BytesIO()

    data = "Title,Category,Type,Amount,Date\n"

    for transaction in transactions:

        formatted_date = transaction.date.replace(
            '-',
            '/'
        )

        data += (

            f"{transaction.title},"
            f"{transaction.category},"
            f"{transaction.type},"
            f"{transaction.amount},"
            f"{formatted_date}\n"

        )

    output.write(
        data.encode('utf-8')
    )

    output.seek(0)

    response = make_response(
        output.getvalue()
    )

    response.headers[
        "Content-Disposition"
    ] = (
        "attachment; filename=transactions.csv"
    )

    response.headers[
        "Content-type"
    ] = "text/csv"

    return response


# =========================
# PDF DOWNLOAD
# =========================

@app.route('/download_report')
@login_required
def download_report():

    buffer = BytesIO()

    pdf = canvas.Canvas(buffer)

    pdf.setTitle(
        "Expense Report"
    )

    pdf.setFont(
        "Helvetica-Bold",
        18
    )

    pdf.drawString(
        180,
        800,
        "Expense Tracker Report"
    )

    pdf.setFont(
        "Helvetica",
        12
    )

    pdf.drawString(
        50,
        760,
        f"User: {current_user.name}"
    )

    transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).all()

    y = 720

    total_income = 0

    total_expense = 0

    for transaction in transactions:

        text = (

            f"{transaction.title} | "
            f"{transaction.category} | "
            f"{transaction.type} | "
            f"₹ {transaction.amount}"

        )

        pdf.drawString(
            50,
            y,
            text
        )

        y -= 25

        if transaction.type == "Income":

            total_income += float(
                transaction.amount
            )

        else:

            total_expense += float(
                transaction.amount
            )

    y -= 20

    pdf.setFont(
        "Helvetica-Bold",
        14
    )

    pdf.drawString(
        50,
        y,
        f"Total Income: ₹ {total_income}"
    )

    y -= 25

    pdf.drawString(
        50,
        y,
        f"Total Expense: ₹ {total_expense}"
    )

    y -= 25

    pdf.drawString(
        50,
        y,
        f"Balance: ₹ {total_income - total_expense}"
    )

    pdf.save()

    buffer.seek(0)

    response = make_response(
        buffer.getvalue()
    )

    response.headers[
        'Content-Type'
    ] = 'application/pdf'

    response.headers[
        'Content-Disposition'
    ] = (
        'attachment; filename=expense_report.pdf'
    )

    return response


# =========================
# PROFILE PAGE
# =========================

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():

    if request.method == 'POST':

        new_password = request.form['password']

        current_user.password = generate_password_hash(
            new_password
        )

        db.session.commit()

        flash(
            'Password updated successfully!',
            'success'
        )

        return redirect(
            url_for('profile')
        )

    return render_template(
        'profile.html'
    )


# =========================
# LOGOUT
# =========================

@app.route('/logout')
@login_required
def logout():

    logout_user()

    flash(
        'Logged out successfully!',
        'warning'
    )

    return redirect(
        url_for('home')
    )


# =========================
# RUN WEBSITE
# =========================

if __name__ == "__main__":

    with app.app_context():

        db.create_all()

    app.run(debug=True)