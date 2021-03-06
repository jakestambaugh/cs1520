from flask import (
    Flask,
    Response,
    abort,
    render_template,
    request,
    jsonify,
    redirect,
    session,
)
from random import randint
from datetime import datetime
import json

from storage import (
    create_datastore_client,
    create_storage_client,
    list_slides,
    store_quiz_answer,
    store_survey,
)
import student
from user import UserCredential, UserProfile, UserStore
from quiz import Quiz, QuizStore
from video import VideoStore

app = Flask(__name__)
app.secret_key = b"20072012f35b38f51c782e21b478395891bb6be23a61d70a"

# Initialization code for our storage layer
datastore_client = create_datastore_client()
storage_client = create_storage_client()
userstore = UserStore(datastore_client, storage_client)

quiz_store = QuizStore(datastore_client)

video_store = VideoStore(datastore_client)


@app.route("/")
def root():
    """Generate the homepage

    The render_template function reads an HTML file from the "templates"
    directory and fills in any variables.
    """
    user = session.get("user")
    first_videos = video_store.fetch_videos("2020-04-03 06:00:00.000")
    second_videos = video_store.fetch_videos("2020-04-08 06:00:00.000")
    return render_template("index.html", first_videos=first_videos, second_videos=second_videos, homepage=True, user=user)


@app.route("/syllabus")
def syllabus():
    """Generate a page that contains the course syllabus

    Just like the root() function, but it's annotated with a different route.
    """
    return render_template("syllabus.html")


@app.route("/lecture")
def handle_lecture():
    """Generate a page with a list of lectures

    In this iteration, the data is read from Datastore. It generates links our to Object Storage.
    """
    lectures = list_slides(datastore_client)
    return render_template("lectures.html", lectures=lectures)


@app.route("/about")
def handle_about():
    """Generate a page with a description of how this website works.

    Includes a link to this website's GitHub page.
    """
    return render_template("about.html")


@app.route("/videos")
def handle_videos():
    videos = video_store.fetch_videos()
    return render_template("videos.html", videos=videos)


@app.route("/survey", methods=["GET"])
def show_survey():
    """Generate a page where students can give me feeback.

    Hopefully they are nice!
    """
    return render_template("survey.html")


@app.route("/survey", methods=["POST"])
def handle_survey():
    """Process the form fields from the survey"""
    store_survey(datastore_client, request.form)
    return render_template("survey_thanks.html")


@app.route("/quiz/<id>", methods=["GET"])
def show_quiz(id):
    """Presents a quiz to a user

    This is a hardcoded quiz, but in the future I will present different quizzes based on id
    """
    user = get_user()
    quiz = quiz_store.load_quiz(id)
    if not quiz:
        abort(404)
    return render_template("quiz.html", quiz=quiz, user=user)


@app.route("/quiz/<id>", methods=["POST"])
def process_quiz_answer(id):
    student_id = request.form.get("student-id", "No ID provided")
    store_quiz_answer(datastore_client, student_id, quiz_id=id, answers=request.form)
    return render_template(
        "quiz_response.html", quiz_title="Week 4 Quiz", answers=request.form
    )


@app.route("/student/<id>", methods=["GET"])
def show_student_api(id):
    if len(str(id)) != 7:
        return abort(404)
    s = student.read_student_info(datastore_client, id)
    if s is None:
        return abort(404)
    output = {"name": s.name, "email": s.email}
    return jsonify(output)


@app.route("/auth/signup", methods=["GET"])
def show_signup_form():
    user = get_user()
    if user:
        redirect("/")
    return render_template("signup.html", auth=True)


@app.route("/auth/signup", methods=["POST"])
def handle_signup():
    username = request.form.get("username")
    password = request.form.get("password")
    bio = request.form.get("bio")
    if username in userstore.list_existing_users():
        return render_template(
            "signup.html", auth=True, error="A user with that username already exists"
        )
    # TODO: make this transactional so that we don't have a user without a profile
    userstore.store_new_credentials(generate_creds(username, password))
    userstore.store_new_profile(UserProfile(username, bio, avatar_id=None))
    session["user"] = username
    return redirect("/")


@app.route("/auth/login", methods=["GET"])
def show_login_form():
    user = get_user()
    if user:
        redirect("/")
    return render_template("login.html", auth=True)


@app.route("/auth/login", methods=["POST"])
def handle_login():
    username = request.form.get("username")
    password = request.form.get("password")
    user = userstore.verify_password(username, password)
    if not user:
        return render_template("login.html", auth=True, error="Password did not match.")
    session["user"] = user.username
    return redirect("/")


@app.route("/auth/logout")
def handle_logout():
    session.clear()
    return redirect("/")


@app.route("/user")
def check_user_exists():
    """This is a weird one, I'm only really calling this function to check for duplicate usernames."""
    username = request.args.get("username")
    # TODO: make this faster than loading all users and iterating each time
    return jsonify({"exists": username in userstore.list_existing_users()})


@app.route("/profile")
def show_profile():
    user = get_user()
    if not user:
        redirect("/auth/login")
    profile = userstore.load_user_profile(user)
    return render_template("profile.html", profile=profile, user=user)


@app.route("/profile/edit", methods=["GET"])
def edit_profile():
    user = get_user()
    if not user:
        redirect("/auth/login")
    return render_template("profile_edit.html", user=user)


@app.route("/profile/edit", methods=["PUT"])
def generate_avatar_url():
    """This endpoint expects 1. a filename and 2. a content type
    """
    user = get_user()
    if not user:
        abort(403)
    if not request.is_json:
        abort(404)
    filename = request.json["filename"]
    content_type = request.json["contentType"]
    bio = request.json["bio"]
    if not (filename and content_type):
        # One of the fields was missing in the JSON request
        abort(404)
    avatar_url = userstore.create_avatar_upload_url(filename, content_type)
    userstore.store_new_profile(UserProfile(user, bio=bio, avatar_id=filename))
    return jsonify({"signedUrl": avatar_url})


def get_user():
    """If our session has an identified user (i.e., a user is signed in), then
    return that username."""
    return session.get("user", None)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
