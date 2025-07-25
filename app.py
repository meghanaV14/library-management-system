from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from flask import Flask, request
import MySQLdb.cursors
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "your_secret_key"

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'library_db'

mysql = MySQL(app)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        if user and check_password_hash(user['password'], password):
            session['loggedin'] = True
            session['id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('member_dashboard'))
        flash('Incorrect username or password')
    return render_template('login.html')

@app.route('/admin')
def admin_dashboard():
    if 'loggedin' in session and session['role'] == 'admin':
        return render_template('admin_dashboard.html')
    return redirect(url_for('login'))

@app.route('/member')
def member_dashboard():
    if 'loggedin' in session and session['role'] == 'member':
        return render_template('member_dashboard.html')
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# -------- User Management (Admin) -------- #

@app.route('/users')
def users():
    if 'loggedin' in session and session['role'] == 'admin':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users')
        users = cursor.fetchall()
        return render_template('users.html', users=users)
    return redirect(url_for('login'))

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if 'loggedin' in session and session['role'] == 'admin':
        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            password = generate_password_hash(request.form['password'])
            role = request.form['role']
            cursor = mysql.connection.cursor()
            cursor.execute('INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)', (username, password, email, role))
            mysql.connection.commit()
            return redirect(url_for('users'))
        return render_template('add_user.html')
    return redirect(url_for('login'))

# -------- Book Management -------- #

@app.route('/books')
def books():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM books')
        books = cursor.fetchall()
        return render_template('books.html', books=books)
    return redirect(url_for('login'))

@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    if 'loggedin' in session and session['role'] == 'admin':
        if request.method == 'POST':
            title = request.form['title']
            author = request.form['author']
            isbn = request.form['isbn']
            total = int(request.form['total_copies'])
            cursor = mysql.connection.cursor()
            cursor.execute('INSERT INTO books (title, author, isbn, total_copies, available_copies) VALUES (%s, %s, %s, %s, %s)', (title, author, isbn, total, total))
            mysql.connection.commit()
            return redirect(url_for('books'))
        return render_template('add_book.html')
    return redirect(url_for('login'))

# -------- Member Management -------- #

@app.route('/members')
def members():
    if 'loggedin' in session and session['role'] == 'admin':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM members')
        members = cursor.fetchall()
        return render_template('members.html', members=members)
    return redirect(url_for('login'))

@app.route('/add_member', methods=['GET', 'POST'])
def add_member():
    if 'loggedin' in session and session['role'] == 'admin':
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            address = request.form['address']
            phone = request.form['phone']
            cursor = mysql.connection.cursor()
            cursor.execute('INSERT INTO members (name, email, address, phone) VALUES (%s, %s, %s, %s)', (name, email, address, phone))
            mysql.connection.commit()
            return redirect(url_for('members'))
        return render_template('add_member.html')
    return redirect(url_for('login'))

# -------- Issue & Return -------- #

@app.route('/issue_book', methods=['GET', 'POST'])
def issue_book():
    if 'loggedin' in session and session['role'] == 'admin':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        if request.method == 'POST':
            book_id = request.form['book_id']
            member_id = request.form['member_id']
            today = datetime.today().date()
            due = today + timedelta(days=14)
            cursor.execute('INSERT INTO issues (book_id, member_id, issue_date, due_date) VALUES (%s, %s, %s, %s)', (book_id, member_id, today, due))
            cursor.execute('UPDATE books SET available_copies = available_copies - 1 WHERE id = %s', (book_id,))
            mysql.connection.commit()
            return redirect(url_for('issues'))
        cursor.execute('SELECT id, title FROM books WHERE available_copies > 0')
        books = cursor.fetchall()
        cursor.execute('SELECT id, name FROM members')
        members = cursor.fetchall()
        return render_template('issue_book.html', books=books, members=members)
    return redirect(url_for('login'))

@app.route('/return_book', methods=['GET', 'POST'])
def return_book():
    if 'loggedin' in session and session['role'] == 'admin':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        if request.method == 'POST':
            issue_id = request.form['issue_id']
            today = datetime.today().date()
            cursor.execute('SELECT book_id FROM issues WHERE id = %s', (issue_id,))
            book_id = cursor.fetchone()['book_id']
            cursor.execute('UPDATE issues SET return_date = %s, status = "returned" WHERE id = %s', (today, issue_id))
            cursor.execute('UPDATE books SET available_copies = available_copies + 1 WHERE id = %s', (book_id,))
            mysql.connection.commit()
            return redirect(url_for('issues'))
        cursor.execute('SELECT id FROM issues WHERE status = "issued"')
        issues = cursor.fetchall()
        return render_template('return_book.html', issues=issues)
    return redirect(url_for('login'))

@app.route('/issues')
def issues():
    if 'loggedin' in session and session['role'] == 'admin':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT issues.*, books.title, members.name FROM issues JOIN books ON issues.book_id = books.id JOIN members ON issues.member_id = members.id')
        data = cursor.fetchall()
        return render_template('issues.html', issues=data)
    return redirect(url_for('login'))

@app.route('/example')
def example():
    cursor = mysql.connection.cursor()  # You can also use DictCursor for dict results
    cursor.execute('SELECT * FROM books')
    books = cursor.fetchall()
    cursor.close()
    return str(books)

if __name__ == "__main__":
    app.run(debug=True)
