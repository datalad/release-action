import nox

nox.options.reuse_existing_virtualenvs = True


@nox.session
def typing(session):
    session.install("-r", "requirements.txt")
    session.install("mypy", "types-requests")
    session.run("mypy", "datalad_release_action")
