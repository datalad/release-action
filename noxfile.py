import nox

nox.options.reuse_existing_virtualenvs = True


@nox.session
def typing(session):
    session.install("-r", "requirements.txt")
    session.install("mypy", "types-requests")
    session.run("mypy", "datalad_release_action")


@nox.session
def labels(session):
    repo, config = session.posargs
    session.install("-r", "requirements.txt")
    session.run("python", "-m", "datalad_release_action", "-c", config, repo, "labels")
