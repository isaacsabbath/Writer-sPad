from flask import Flask, render_template, flash, request, redirect, url_for, session,logging
#from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, PasswordField, validators, TextAreaField
from flask_wtf.file import FileField, FileAllowed
from werkzeug.utils import secure_filename
from passlib.hash import sha256_crypt
from functools import wraps
from flask_wtf import FlaskForm
hostname=myflaskapp.mysql.database.azure.com
port=3306
username=isaac
password={your-password}
ssl-mode=require


app = Flask(__name__)
app.secret_key = 'secret123'
#Config mySQL

app.config['MYSQL_HOST'] = 'myflaskapp.mysql.database.azure.com'
app.config ['MYSQL_USER'] = 'isaac'
app.config['MYSQL_PASSWORD'] = 'Richard002'
app.config['MYSQL_DB'] = 'myflaskapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Initialise mysql
mysql = MySQL(app)


# Articles = Articles()

@app.route('/')
def index():
	return render_template('home.html')



@app.route('/about')
def about():
	return render_template('about.html')

@app.route('/articles')
def articles():
	#create cursor
	cur = mysql.connection.cursor()

	#get articles
	result = cur.execute("SELECT * FROM articles")

	articles = cur.fetchall()

	if result > 0:
		return render_template('articles.html', articles=articles)

	else:
		msg = 'No article found'
		return render_template('articles.html', msg=msg)

	# close connection

	cur.close()


@app.route('/article/<string:id>/')
def article(id):
	cur = mysql.connection.cursor()

	#get articles
	result = cur.execute("SELECT * FROM articles WHERE id=%s", [id])

	articles = cur.fetchone()

	return render_template('article.html', article=article)


class RegisterForm(Form):
	name = StringField('Name', [validators.length(min=1, max=50)])
	username = StringField('Username', [validators.length(min=4, max=25)])
	email = StringField('Email', [validators.length(min=6, max=50)])
	password = PasswordField('Password', [
		validators.DataRequired(), 
		validators.EqualTo('confirm', message='Passwords do not match')
		
	])
	confirm = PasswordField('Confirm Password')

@app.route('/register', methods=['GET', 'POST'])
def register():
	form = RegisterForm(request.form)
	if request.method == 'POST' and form.validate():
		name = form.name.data
		email = form.email.data
		username = form.username.data
		password = sha256_crypt.hash(str(form.password.data))

		#cursor

		cur = mysql.connection.cursor()
		cur.execute("INSERT INTO users(name,email,username,password) VALUES(%s,%s,%s,%s)", (name, email,username,password))
		
		## commit to DB

		mysql.connection.commit()

		# Close connection
		cur.close()

		flash('You are now registered and can now log in', 'success')

	
		return redirect(url_for('login'))

	return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
	form = RegisterForm(request.form)
	if request.method == 'POST':
		#  get form fields
		username = request.form.get('username')
		password_candidate = request.form.get('password')

		print(f"Username from form: {username}")

		# Create cursor
		cur = mysql.connection.cursor()

		# Get user by username
		result = cur.execute("SELECT * FROM users WHERE username = %s",[username])

		if result > 0:
			#get stored hash
			data = cur.fetchone()
			password = data['password']

			#compare the passwords
			if sha256_crypt.verify(password_candidate, password):
				session['logged_in'] = True
				session['username'] = username


				flash('You are now logged in!', 'success')
				return redirect(url_for('dashboard'))
			else:
				error = 'Invalid login'
				return render_template('login.html', error=error)

			cur.close()
		else:
			error = 'Username not found'
			return render_template('login.html', error=error)
	

	return render_template('login.html')

def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorized, Please login', 'danger')
			return redirect(url_for('login'))
	return wrap

@app.route('/logout')
@is_logged_in
def logout():
	session.clear()
	flash('You are now logged out', 'success')
	return redirect(url_for('login'))



@app.route('/dashboard')
@is_logged_in
def dashboard():
	#create cursor
	cur = mysql.connection.cursor()

	#get articles
	result = cur.execute("SELECT * FROM articles")

	articles = cur.fetchall()

	if result > 0:
		return render_template('dashboard.html', articles=articles)

	else:
		msg = 'No article found'
		return render_template('dashboard.html')

	# close connection

	cur.close()


class ArticleForm(FlaskForm):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])
    image = FileField('Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])


#Add article
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        # Get the logged-in user's username from the session
        author = session.get('username')  # Or use session['username'] directly if you are sure it's set

        # Debugging: Print the values before inserting them
        print(f"Title: {title}, Body: {body}, Author: {author}")

        if not author:
            flash("You need to be logged in to submit an article.", "danger")
            return redirect(url_for('login'))  # Redirect to login if the user is not logged in

        # Ensure the title and body are valid strings
        if not title or not body:
            flash("Title and body are required.", "danger")
            return render_template('add_article.html', form=form)

        # Create a cursor object to interact with the database
        cur = mysql.connection.cursor()

        # Insert the article into the database
        try:
            cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)", (title, body, author))

            # Commit to the database
            mysql.connection.commit()
            flash('Article created successfully!', 'success')

        except MySQLdb.Error as e:
            print(f"Error executing query: {e}")
            flash('Error creating article. Please try again later.', 'danger')

        finally:
            # Close the cursor
            cur.close()

        # Redirect to the dashboard
        return redirect(url_for('dashboard'))

    return render_template('add_article.html', form=form)


@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    # Create a cursor
    cur = mysql.connection.cursor()

    # Get the article by ID
    result = cur.execute("SELECT * FROM articles WHERE id=%s", [id])

    if result > 0:
        # Article found, fetch data
        article = cur.fetchone()
        form = ArticleForm(request.form)

        # Prepopulate the form fields for GET request
        if request.method == 'GET':
            form.title.data = article['title']
            form.body.data = article['body']

        # Handle form submission for POST request
        if request.method == 'POST' and form.validate():
            title = form.title.data
            body = form.body.data

            try:
                # Update the article in the database
                cur.execute("UPDATE articles SET title=%s, body=%s WHERE id=%s", (title, body, id))
                mysql.connection.commit()
                flash('Article updated successfully!', 'success')
                return redirect(url_for('dashboard'))
            except Exception as e:
                print(f"Error updating article: {e}")
                flash('An error occurred. Please try again.', 'danger')
            finally:
                cur.close()
    else:
        flash('Article not found!', 'danger')
        return redirect(url_for('dashboard'))

    return render_template('edit_article.html', form=form, id=id)


@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
	# Create a cursor
    cur = mysql.connection.cursor()

    # Get the article by ID
    cur.execute("DELETE FROM articles WHERE id=%s", [id])

    mysql.connection.commit()

    cur.close()

    flash('Article Deleted!', 'success')

    return redirect(url_for('dashboard'))


if __name__ == '__main__' :
	print(f"SECRET_KEY is: {app.secret_key}")
	app.run(debug = True) 



