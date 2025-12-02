# Final Project

An exercise to put to practice software development teamwork, subsystem communication, containers, deployment, and CI/CD pipelines. See [instructions](./instructions.md) for details.

Test website:

1. `pipenv install` (creates the lockfile and puts Flask in your virtualenv).
2. `pipenv shell`
3. `flask run`

Points to `http://127.0.0.1:5000` to see the updated job board UI.

(if that doesn't work try 3. `$env:FLASK_APP="app.py"; $env:FLASK_ENV="development"`) after running `pipenv shell`
