from flask import Flask, render_template, request, redirect, url_for, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from PIL import Image
from wtforms import FileField, SubmitField
from werkzeug.utils import secure_filename
import os
from wtforms.validators import InputRequired
import sys

admins = ["God", "Vilm"]

app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['SECRET_KEY'] = '69420'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/profiles'

db = SQLAlchemy(app)


class Users(db.Model):
    token = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(15), nullable=False, unique=True)
    password = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(50), nullable=False, unique=True)
    profile_pic = db.Column(db.String(100))


def getUser():
    if "user" in request.cookies:
        token = request.cookies.get("user")
        current_user = usernamesByToken(token)
        return current_user

    else:
        return ""


def usernamesByToken(token):
    for user in Users.query.all():
        if str(token) == str(user.token):
            return user.username
    return ""

def profilePicByToken(token):
    for user in Users.query.all():
        if str(token) == str(user.token):
            return user.profile_pic
    return ""


def resize_image(image: Image, length: int) -> Image:
    """
    Resize an image to a square. Can make an image bigger to make it fit or smaller if it doesn't fit. It also crops
    part of the image.

    :param self:
    :param image: Image to resize.
    :param length: Width and height of the output image.
    :return: Return the resized image.
    """

    """
    Resizing strategy : 
     1) We resize the smallest side to the desired dimension (e.g. 1080)
     2) We crop the other side so as to make it fit with the same length as the smallest side (e.g. 1080)
    """
    if image.size[0] < image.size[1]:
        # The image is in portrait mode. Height is bigger than width.

        # This makes the width fit the LENGTH in pixels while conserving the ration.
        resized_image = image.resize((length, int(image.size[1] * (length / image.size[0]))))

        # Amount of pixel to lose in total on the height of the image.
        required_loss = (resized_image.size[1] - length)

        # Crop the height of the image so as to keep the center part.
        resized_image = resized_image.crop(
            box=(0, required_loss / 2, length, resized_image.size[1] - required_loss / 2))

        # We now have a length*length pixels image.
        return resized_image
    else:
        # This image is in landscape mode or already squared. The width is bigger than the heihgt.

        # This makes the height fit the LENGTH in pixels while conserving the ration.
        resized_image = image.resize((int(image.size[0] * (length / image.size[1])), length))

        # Amount of pixel to lose in total on the width of the image.
        required_loss = resized_image.size[0] - length

        # Crop the width of the image so as to keep 1080 pixels of the center part.
        resized_image = resized_image.crop(
            box=(required_loss / 2, 0, resized_image.size[0] - required_loss / 2, length))

        # We now have a length*length pixels image.
        return resized_image


class UploadFileForm(FlaskForm):
    file = FileField("File", validators=[InputRequired()])
    submit = SubmitField("Upload File")


@app.route("/user", methods=["GET", "POST"])
def user():
    user = request.cookies.get('user')
    user = usernamesByToken(user)
    form = UploadFileForm()

    if form.validate_on_submit():
        file = form.file.data
        file.save(os.path.join(os.path.abspath(os.path.dirname(__file__)),app.config['UPLOAD_FOLDER'],secure_filename(file.filename)))
        file_name, file_extension  = os.path.splitext(file.filename)
        if file_extension not in ['.png', '.jpg', '.jpeg', '.gif']:
            if os.path.exists(f"static/profiles/{file.filename}"):
                os.remove(f"static/profiles/{file.filename}")
                return make_response("Filetype was wrong! <a href='/user'>Try again</a>")
            else:
                return "filetype was wrong but could not delete!\nCheck the user() function in app.py"
        else:
            for this_user in Users.query.all():
                if str(user) == str(this_user.username):

                    old_pic = this_user.profile_pic
                    if os.path.exists(old_pic):
                        os.remove(old_pic)

                    setattr(this_user, 'profile_pic', (f"static/profiles/{file.filename}"))
                    db.session.commit()

            return redirect(url_for("home"))
    if os.path.exists(profilePicByToken(request.cookies.get('user'))):
        exists = True
    else:
        exists = False
    return render_template('user.html', exists=exists, user=user, form=form, pic=profilePicByToken(request.cookies.get('user')))


@app.route("/home")
@app.route("/")
def home():
    global admins
    if "user" in request.cookies:
        token = request.cookies.get("user")
        current_user = usernamesByToken(token)
        return render_template('home.html', user=current_user, admins=admins)

    else:
        return render_template('home.html', user="", admins=admins)


@app.route("/login")
def login():
    return render_template('login.html', user=getUser())


@app.route("/register")
def register():
    return render_template('register.html', user=getUser())


@app.route("/adduser", methods=["POST"])
def adduser():
    global Users
    duplicate_user = False
    duplicate_email = False

    username = request.form.get("username")
    password = request.form.get("password")
    email = request.form.get("email")

    for user in Users.query.all():
        ex_username = user.username
        ex_email = user.email

        if ex_username.lower() == username.lower():
            duplicate_user = True
        if ex_email.lower() == email.lower():
            duplicate_email = True

    if duplicate_user or duplicate_email:
        if duplicate_user:
            return render_template("duplicate.html", duplicate="username", user=getUser())
        elif duplicate_email:
            return render_template("duplicate.html", duplicate="email", user=getUser())
    else:
        new_user = Users(username=username, password=password, email=email, profile_pic="static/profiles/default.jpg")

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))


@app.route("/otherlogin", methods=["POST"])
def otherlogin():
    error = ""
    username = request.form.get("username")
    password = request.form.get("password")

    for user in Users.query.all():
        if username == user.username:

            if user.password == password:
                resp = make_response(redirect(url_for('home')))
                resp.set_cookie('user', str(user.token))
                return resp
            else:
                error = "wrong password"
        else:
            error = "no user with that username"
    return render_template('loginerror.html', error=error, user=getUser())


@app.route("/debug")
def debug():
    return render_template('debug.html', all=Users.query.all(), user=getUser())


@app.route("/logout")
def logout():
    resp = make_response(redirect(url_for('home')))
    resp.set_cookie('user', '', expires=0)
    return resp


@app.route("/delete", methods=["GET"])
def myDeleteOption():
    return render_template('delete.html', user=getUser())


@app.route("/delete", methods=["POST"])
def myDelete():
    current_user = request.cookies.get('user')
    db.session.query(Users).filter(Users.token == int(current_user)).delete()
    resp = make_response(redirect(url_for('home')))
    resp.set_cookie('user', '', expires=0)
    db.session.commit()
    return resp



if __name__ == "__main__":
    db.create_all()
    app.run(debug=True)
