This repository provides two custom GitHub Actions for working with changelogs
& releases in the flow used by [DataLad](https://github.com/datalad/datalad)
and related projects.

Both actions operate on a repository that must already be using
[scriv](https://github.com/nedbat/scriv) to manage changelog entries.  In
addition, the repository must contain a YAML configuration file (named
"`.datalad-release-action.yaml`" by default) for use by the actions containing
the following keys:

- `fragment-directory` — the path to scriv's fragment directory relative to the
  root of the repository (which must also be the directory in which the action
  is invoked); defaults to `changelog.d`

- `tag-prefix` — string to prepend to the names of created tags and which all
  previous versioned tags in the repository must begin with; defaults to the
  empty string

- `categories` — *(required)* a list of mappings describing the changelog
  categories used by the project; the mapping keys are:
    - `name` — *(required)* the category name as it will appear in changelog
      headers; this must match a corresponding category name in `scriv.ini`
      exactly
    - `label` — a GitHub label; any pull requests with this label will be
      placed under the given category by the `add-changelog-snippet` action.
      If a pull request has multiple category labels, the first matching
      category listed in the config file is used.
    - `label-color` — the color for the GitHub label, as a six-digit
      hexadecimal string (case insensitive) without a leading '#'; this color
      will be used when the label is added or updated via the "labels" command
    - `label-description` — the description for the GitHub label; this
      description will be used when the label is added or updated via the
      "labels" command
    - `bump` — the version bump level to use when a PR with the associated
      label is included in a release; can be `major`, `minor`, or `patch`
      (default)

- `extra-labels` — a list of mappings describing additional labels for the
  "labels" command to create or update; the mapping keys are:
    - `name` *(required)*
    - `color` — a six-digit hexadecimal string (case insensitive) without a
      leading '#'
    - `description`

An example configuration file:

```yaml
fragment-directory: changelog.d

tag-prefix: v

categories:
  - name: 💥 Breaking Changes
    bump: major
    label: major
    label-color: C5000B
    label-description: Increment the major version when merged
  - name: 🚀 Enhancements and New Features
    bump: minor
    label: minor
    label-color: F1A60E
    label-description: Increment the minor version when merged
  - name: 🐛 Bug Fixes
    label: patch
    label-color: "870048"
    label-description: Increment the patch version when merged
  - name: 🔩 Dependencies
    label: dependencies
    label-color: 8732bc
    label-description: Update one or more dependencies' versions
  - name: 📝 Documentation
    label: documentation
    label-color: cfd3d7
    label-description: Changes only affect the documentation
  - name: 🏠 Internal
    label: internal
    label-color: "696969"
    label-description: Changes only affect the internal API
  - name: 🏎 Performance
    label: performance
    label-color: f4b2d8
    label-description: Improve performance of an existing feature
  - name: 🧪 Tests
    label: tests
    label-color: ffd3cc
    label-description: Add or improve existing tests

extra-labels:
  - name: release
    color: 007f70
    description: Create a release when this pr is merged
  - name: CHANGELOG-missing
    color: 5B0406
    description: When a PR does not contain add a changelog item, yet
```


# Action: `add-changelog-snippet`

This action creates a `pr-PRNUM.md` file in the fragment directory for a pull
request.  The pull request must be labelled with at least one changelog
category label.

If the PR already adds a file at the expected path, nothing is done.
Otherwise, if the PR adds to the fragment directory exactly one file with a
name of the form `*[-_]*.md`, that file is renamed to `pr-PRNUM.md`; if there
are multiple such files, an error occurs.

## Usage

```yaml
- name: Add changelog snippet
  uses: datalad/release-action/add-changelog-snippet@v1
  with:
    # See "Inputs" below
```

The action will operate on the pull request identified by `${{
github.event.pull_request.number }}`.

## Inputs

| Key | Meaning | Default |
| --- | ------- | ------- |
| `config` | Path to the action configuration file | `.datalad-release-action.yaml` |
| `git-author-email` | E-mail address to use when committing the changelog snippet | `bot@datalad.org` |
| `git-author-name` | Name to use when committing the changelog snippet | `DataLad Bot` |
| `rm-labels` | Names of labels (on separate lines) to remove from the pull request after generating the fragment | [empty] |
| `token` | GitHub token to use for querying the GitHub API; just using `${{ secrets.GITHUB_TOKEN }}` is recommended | *(required)* |

## Sample Workflow Usage

```yaml
name: Add changelog.d snippet

on:
  # This action should be run in workflows triggered by `pull_request_target`
  # (not by regular `pull_request`!)
  pull_request_target:
    # Run whenever the PR is pushed to, receives a label, or is created with
    # one or more labels:
    types: [synchronize, labeled]

# Prevent the workflow from running multiple jobs at once when a PR is created
# with multiple labels:
concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.head.label }}
  cancel-in-progress: true

jobs:
  add:
    runs-on: ubuntu-latest
    # Only run on PRs that have the "CHANGELOG-missing" label:
    if: contains(github.event.pull_request.labels.*.name, 'CHANGELOG-missing')
    steps:
      - name: Check out repository
        uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.ref }}
          repository: ${{ github.event.pull_request.head.repo.full_name }}

      - name: Add changelog snippet
        uses: datalad/release-action/add-changelog-snippet@v1
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          rm-labels: CHANGELOG-missing
```


# Action: `release`

This action prepares a release by performing the following:

- All pull requests that have files in the fragments directory with names of
  the form `pr-PRNUM.md` or `pr-PRNUM.rst` are inspected in order to determine
  the maximum version bump level.

- The highest-versioned tag of the form `N.N.N` after stripping `tag-prefix`
  (It is an error if there are no such tags) is used as the previous release
  version, and it is bumped by the version bump level to obtain the version for
  the new release.

- A comment is made on all pull requests from step 1 and on the issues that
  they close mentioning the new release.

- `scriv collect` is run to create a new changelog section, and the results are
  committed.

- If the `pre-tag` input is not empty, it is executed as a series of Bash
  commands.  These commands will have access to the following environment
  variables:

    - `GITHUB_TOKEN` — same as the `token` input
    - `GIT_AUTHOR_NAME` — same as the `git-author-name` input
    - `GIT_AUTHOR_EMAIL` — same as the `git-author-email` input
    - `GIT_COMMITTER_NAME` — same as the `git-author-name` input
    - `GIT_COMMITTER_EMAIL` — same as the `git-author-email` input
    - `new_version` — the version of the new release (without leading prefix)
    - `new_tag` — the tag of the new release (i.e., `tag-prefix` plus
      `new_version`)

- The repository HEAD is tagged with an annotated tag named with the version of
  the new release prefixed with `tag-prefix`, the tag is pushed to GitHub, and
  `scriv github-release` is run.

- If the `pypi-token` input is not empty, then `python -m build` is run,
  followed by `twine upload dist/*`

## Usage

```yaml
- name: Add changelog snippet
  uses: datalad/release-action/release@v1
  with:
    # See "Inputs" below
```

## Inputs

| Key | Meaning | Default |
| --- | ------- | ------- |
| `config` | Path to the action configuration file | `.datalad-release-action.yaml` |
| `git-author-email` | E-mail address to use when committing | `bot@datalad.org` |
| `git-author-name` | Name to use when committing | `DataLad Bot` |
| `pre-tag` | A series of Bash commands to run after updating the changelog and before tagging | [empty] |
| `pypi-token` | A token for uploading a project to PyPI; supplying this will cause the project to be built & uploaded as a Python project to PyPI | [empty] |
| `token` | GitHub token to use for interacting with the GitHub API; just using `${{ secrets.GITHUB_TOKEN }}` is recommended | *(required)* |

## Output

| Key           | Meaning |
| ------------- | ------- |
| `new-tag`     | The tag of the new release (includes prefix) |
| `new-version` | The version of the new release (without leading prefix) |

## Sample Workflow Usage

```yaml
name: Auto-release on PR merge

on:
  # This action should be run in workflows triggered by `pull_request_target`
  # (not by regular `pull_request`!)
  pull_request_target:
    branches:
      # Create a release whenever a PR is merged into one of these branches:
      - master
      - maint
    types:
      - closed
  # Allow manually triggering a release via a "Run workflow" button on the
  # workflow's page:
  workflow_dispatch:

jobs:
  release:
    runs-on: ubuntu-latest
    # Only run for manual runs or merged PRs with the "release" label:
    if: >
      github.event_name == 'workflow_dispatch'
         || (github.event.pull_request.merged == true && contains(github.event.pull_request.labels.*.name, 'release'))
    steps:
      - name: Checkout source
        uses: actions/checkout@v4
        with:
          # Check out all history so that the previous release tag can be
          # found:
          fetch-depth: 0

      - name: Prepare release
        uses: datalad/release-action/release@v1
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
```


# Command: `labels`

This repository also provides a command for creating or updating the GitHub
labels used by the actions and their workflows in a repository.  The
recommended way to invoke this command is via
[nox](https://pypi.org/project/nox/); after installing nox, the "labels"
command can be invoked by running the following in a clone of this repository:

    GITHUB_TOKEN=... nox -e labels -- repo-owner/repo-name path/to/config/file

where `GITHUB_TOKEN` is set to a GitHub API token with permission to modify
labels in the desired repository, `repo-owner/repo-name` is replaced with the
owner & name of the GitHub repository whose labels you want to update, and
`path/to/config/file` is a path to a `.datalad-release-action.yaml`
configuration file for the desired repository.


# Command: `populate-workflows.sh`

This repository also includes a shell script, `populate-workflows.sh`, for
automatically creating or updating the sample workflows shown above in a
repository.  Run it with `./populate-workflows.sh path/to/local/repo/clone`.
