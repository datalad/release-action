import nox

nox.options.reuse_existing_virtualenvs = True


@nox.session
def run(session):
    session.install("-r", "requirements.txt")
    session.run("python", "-m", "datalad_release_action", *session.posargs)
