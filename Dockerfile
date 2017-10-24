FROM python:3.4-alpine
ADD . /code
WORKDIR /code
RUN pip install requests
RUN pip install -r requirements.txt
RUN pip install flask-mysql
RUN pip install pymysql
RUN pip install Flask-Mail
CMD ["python", "app.py"]