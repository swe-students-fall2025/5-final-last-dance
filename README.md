[![Build and Deploy Flask App](https://github.com/swe-students-fall2025/5-final-last-dance/actions/workflows/flask-app.yml/badge.svg?branch=main)](https://github.com/swe-students-fall2025/5-final-last-dance/actions/workflows/flask-app.yml) [![Test Coverage](https://codecov.io/gh/swe-students-fall2025/5-final-last-dance/branch/main/graph/badge.svg?flag=codecov-umbrella)](https://codecov.io/gh/swe-students-fall2025/5-final-last-dance)

# PitchDeck

Pitchdeck scrapes top tech companies, ranks openings to your preferences, and keeps a live shortlist so you can spend time on the right applications.

### Container Images

[This](https://hub.docker.com/r/alfardil28/pitchdeck) container runs the entire application.

- [Alif](https://github.com/Alif-4)
- [Alfardil](https://github.com/alfardil)
- [Abdul](https://github.com/amendahawi)
- [Sam](https://github.com/SamRawdon)
- [Galal](https://github.com/gkbichara)

### Requirements:

- Python 3.12+
- MongoDB 4.0+
- pipenv

### Installation

##### Set up environment

Edit your `.env` to match `.env.example`

Then install dependencies and run
`pipenv install`
`pipenv shell`
`python app.py` or `flask run`

Visit: http://127.0.0.1:5000

### Running

You may either `flask run` after installing all dependencies or simply run the docker container and choose a port to host it on.
