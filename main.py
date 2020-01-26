from flask import Flask, render_template, request
from random import randint

from storage import create_datastore_client, list_slides
from quiz import Quiz

app = Flask(__name__)

# Initialization code for our storage layer
datastore_client = create_datastore_client()


@app.route('/')
def root():
    """Generate the homepage

    Gets a random number from the randint function, passing it to the
    template.

    The render_template function reads an HTML file from the "templates"
    directory and fills in any variables.
    """
    fun_number = randint(45, 121)
    return render_template('index.html', num=fun_number)


@app.route('/syllabus')
def syllabus():
    """Generate a page that contains the course syllabus

    Just like the root() function, but it's annotated with a different route.
    """
    return render_template('syllabus.html')


@app.route('/lecture')
def handle_lecture():
    """Generate a page with a list of lectures

    In this iteration, the data is read from Datastore. It generates links our to Object Storage.
    """
    lectures = list_slides(datastore_client)
    return render_template('lectures.html', lectures=lectures)


@app.route('/about')
def handle_about():
    """Generate a page with a description of how this website works.

    Includes a link to this website's GitHub page.
    """
    return render_template('about.html')


@app.route('/quiz/<id>', methods=["GET"])
def show_quiz(id):
    """Presents a quiz to a user

    """
    quiz = Quiz("QUIZ TITLE", id, [{"description": "What markup language is describes the structure of web pages?"}, {
                "description": "What language is used to style web pages?"}])
    return render_template('quiz.html', quiz=quiz)


@app.route('/quiz/<id>', methods=["POST"])
def process_quiz_answer(id):
    student_id = request.form.get("student-id", "No ID provided")
    student_name = request.form.get("student-name", "No name provided")
    return "Processed results! {} {}".format(student_id, student_name)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
