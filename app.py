from flask import Flask,render_template,session,request,flash
from flask_mail import Mail, Message
from datetime import timedelta
from flaskext.mysql import MySQL
import requests
import json
import os
import datetime
import traceback

app = Flask(__name__)
mysql = MySQL()


# mail notification enable
MAIL_NOTIFICATION = True

# Gmail Configuration
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'programmerlogs@gmail.com'
app.config['MAIL_PASSWORD'] = 'programmerLOCK8'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)



# MySQL configurations
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = '123456'
app.config['MYSQL_DATABASE_DB'] = 'mysql'
app.config['MYSQL_DATABASE_HOST'] = 'mysql'
mysql.init_app(app)

def sendemail(message):
	try:

		if(MAIL_NOTIFICATION):

			conn = mysql.connect()
			cursor = conn.cursor()

			rowcount = cursor.execute("select email from vacation.users ")
			rows = cursor.fetchall()

			emails = ''

			for row in rows:
				emails = emails +row[0]+';'

			cursor.close()
			conn.close()

			msg = Message('Vacation Info', sender = 'programmerlogs@gmail.com', recipients = [emails])
			msg.body = message
			mail.send(msg)

	except Exception:
		traceback.print_exc()



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/user/<access_token>')
def dologin(access_token):

	 try:

	 	# get access token json data file
	 	json_content=requests.get('https://www.googleapis.com/oauth2/v1/userinfo?alt=json&access_token='+access_token).text
	 	data = json.loads(json_content)

		 # when access token is valid set info to user session
	 	session['email'] = data['email']
	 	session['name'] = data['name']
	 	session['picture'] = data['picture']

	 	conn = mysql.connect()
	 	cursor = conn.cursor()

	 	rowcount = cursor.execute("select count(*) usercount from vacation.users where email='"+session['email']+"' ")
	 	firstrow = cursor.fetchone()
	 	usercount=firstrow[0]

	 	#if usercount is zero this means user does not exsist in this case, add new user to system on deactive mode and minimum group viewer
	 	if ( usercount == 0):
	 		cursor.execute("insert into vacation.users(email,active,user_group) values ('"+session['email']+"',0,'viewer')")
	 		session['active']=0
	 		session['user_group']='viewer'
	 		conn.commit()
	 		cursor.close()

	 	if( usercount > 0):
	 		cursor.execute("select active,user_group from vacation.users where email='"+session['email']+"'")
	 		firstrow = cursor.fetchone()
	 		session['active']=firstrow[0]
	 		session['user_group']=firstrow[1]
	 		cursor.close()

	 	conn.close()

	 	return render_template('home.html')
	 except Exception:
	 	traceback.print_exc()
	 	return render_template('error.html')


@app.route('/error')
def goError():
	return render_template('error.html')

@app.route('/get_denied_days')
def goDeinedDay():
	response_json='['

	conn = mysql.connect()
	cursor =conn.cursor()

	rowcount = cursor.execute("select date_format(date_,'%Y-%m-%d') from vacation.denied_days")
	days = cursor.fetchall()

	for row in days :
		response_json = response_json + '"'+row[0]+'",'

	cursor.close()
	conn.close()

	response_json=response_json[:-1]
	response_json=response_json+']'
	return response_json

@app.route('/get_vacation_days/<begin_date>')
def getCalendarDays(begin_date):
	response_json = '{'
	vDate = datetime.datetime.strptime(begin_date, "%d-%m-%Y")

	conn = mysql.connect()
	cursor = conn.cursor()

	for index in range(1,43):

		response_json = response_json  + '"'+vDate.strftime('%d-%m-%Y')+'":'

		rowcount = cursor.execute("select full_name,status from vacation.requests where STR_TO_DATE('"+vDate.strftime('%d-%m-%Y')+"', '%d-%m-%Y') between begin_date and end_date ")

		if(rowcount==0):
			response_json = response_json + '[],'

		if(rowcount > 0):
			vRequests = cursor.fetchall();
			response_json = response_json + '['

			for row in vRequests :
				response_json = response_json + '{ "name": "'+row[0]+'", "status": "'+row[1]+'" },'
			response_json = response_json[:-1]
			response_json = response_json + '],'
		vDate = vDate + datetime.timedelta(days=1)



	response_json = response_json[:-1]
	response_json = response_json + '}'


	cursor.close()
	conn.close()

	return response_json

@app.route('/logout')
def doLogout():
	session.clear()
	return redirect('https://accounts.google.com/Logout?')

@app.route('/users')
def goUsers():
	conn = mysql.connect()
	cursor = conn.cursor()

	action = request.args.get('action')

	if(action == 'activate'):
		userEmail = request.args.get('email')
		rowcount = cursor.execute("update vacation.users set active=1 where email='"+userEmail+"' ")
		flash('User activated successfully')
		sendemail('User activated successfully')
		conn.commit()

	if(action == 'lock'):
		userEmail = request.args.get('email')
		rowcount = cursor.execute("update vacation.users set active=0 where email='"+userEmail+"' ")
		flash('User blocked successfully')
		sendemail('User activated successfully')
		conn.commit()

	if(action == 'change'):
		userEmail = request.args.get('email')
		userGroup = request.args.get('user_group')
		rowcount = cursor.execute("update vacation.users set user_group='"+userGroup+"' where email='"+userEmail+"' ")
		flash('User group changed successfully')
		sendemail('User changed successfully')
		conn.commit()

	rowcount = cursor.execute('select email,active,user_group from vacation.users order by active asc ')
	users = cursor.fetchall()

	cursor.close()
	conn.close()

	return render_template('users_management.html',users=users)

@app.route('/calendar',methods = ['GET','POST'])
def doCalendar():
	conn = mysql.connect()
	cursor = conn.cursor()

	action = request.args.get('action')

	if(action == 'add'):
		categoryName = request.form.get('category')
		beginDate = request.form.get('begin')
		endDate = request.form.get('end')
		rowcount = cursor.execute("insert into vacation.requests(email,begin_date,end_date,status,full_name,leave_category) values ('"+session['email']+"',STR_TO_DATE('"+beginDate+"', '%d-%m-%Y'),STR_TO_DATE('"+endDate+"', '%d-%m-%Y'),'pending','"+session['name']+"','"+categoryName+"')")
		flash('Your leave request added successfully ')

		sendemail('New request created')
		conn.commit()

	cursor.execute('select * from vacation.categories ')
	categories = cursor.fetchall()



	cursor.close()
	conn.close()

	return render_template('calendar.html',categories=categories)

@app.route('/requests')
def goPendingRequest():
	conn = mysql.connect()
	cursor = conn.cursor()

	action = request.args.get('action')
	status = request.args.get('status')

	if(action=='accepted' or action == 'declined'):
		rowcount = cursor.execute("update vacation.requests set status='"+action+"' where id= "+request.args.get('id'))
		flash('selected leave request '+action+' successfully ')
		sendemail('selected leave request '+action+' successfully ')
		conn.commit()

	if(status == 'pending'):
		cursor.execute("select full_name,leave_category,begin_date,end_date,id,status from  vacation.requests where status='pending' order by id desc ")
		requests=cursor.fetchall()
	else:
		cursor.execute("select full_name,leave_category,begin_date,end_date,id,status from  vacation.requests where status<>'pending' order by id desc ")
		requests=cursor.fetchall()



	cursor.close()
	conn.close()

	return render_template('leave_requests.html',requests=requests)


@app.route('/categories',methods=['GET','POST'])
def goCategories():
	#if session set not email attribute redirect to index page to login
	#if(session['email']):
	#	return render_template('index.html')
	action = request.args.get('action')

	conn = mysql.connect()
	cursor = conn.cursor()

	if(action == 'add'):
		rowcount = cursor.execute("insert into vacation.categories(category) values ('"+request.form.get('category_name')+"') ")
		conn.commit()
	if(action == 'del'):
		rowcount = cursor.execute("delete from vacation.categories where ID= "+request.args.get('id'))
		conn.commit()

	cursor.execute('select * from vacation.categories ')
	categories = cursor.fetchall()


	cursor.close()
	conn.close()

	return render_template('leave_categories.html',categories=categories)

if __name__ == "__main__":
	app.secret_key = os.urandom(24)
app.run(host="0.0.0.0", debug=True)
