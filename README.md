This repository provides two custom GitHub Actions for working with changelogs
& releases in the flow used by [DataLad](https://github.com/datalad/datalad)
and related projects.

Both actions operate on a repository that must already be using
[scriv](https://github.com/nedbat/scriv) to manage changelog entries.  In
addition, the repository must contain a YAML configuration file (named
"`.datalad-release-action.yaml`" by default) for use by the actions containing
the following keys:

- `fragment_directory` — the path to scriv's fragment directory relative to the
  root of the repository (which must also be the directory in which the action
  is invoked); defaults to `changelog.d`

- `categories` — *(required)* a list of mappings describing the changelog
  categories used by the project; the mapping keys are:
    - `name` — *(required)* the category name as it will appear in changelog
      headers; this must match a corresponding category name in `scriv.ini`
      exactly
    - `label` — a GitHub label; any pull requests with this label will be
      placed under the given category by the `add-changelog-snippet` action.
      If a pull request has multiple category labels, the first matching
      category listed in the config file is used.
    - `bump` — the version bump level to use when a PR with the associated
      label is included in a release; can be `major`, `minor`, or `patch`
      (default)

An example configuration file:

```yaml
fragment_directory: changelog.d

categories:
  - name: 💥 Breaking Changes
    bump: major
    label: major
  - name: 🚀 Enhancements and New Features
    bump: minor
    label: minor
  - name: 🐛 Bug Fixes
    label: patch
  - name: 🔩 Dependencies
    label: dependencies
  - name: 📝 Documentation
    label: documentation
  - name: 🏠 Internal
    label: internal
  - name: 🏎 Performance
    label: performance
  - name: 🧪 Tests
    label: tests
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
  uses: datalad/release-action/add-changelog-snippet@master
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
  group: ${{ github.workflow }}-${{ github.ref_name }}
  cancel-in-progress: true

jobs:
  add:
    runs-on: ubuntu-latest
    # Only run on PRs that have the "CHANGELOG-missing" label:
    if: contains(github.event.pull_request.labels.*.name, 'CHANGELOG-missing')
    steps:
      - name: Check out repository
        uses: actions/checkout@v3
        with:
          ref: ${{ github.event.pull_request.head.ref }}
          repository: ${{ github.event.pull_request.head.repo.full_name }}

      - name: Add changelog snippet
        uses: datalad/release-action/add-changelog-snippet@master
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          rm-labels: CHANGELOG-missing
```


# Action: `release`

This action prepares a release by performing the following:

- All pull requests that have files in the fragments directory with names of
  the form `pr-PRNUM.md` or `pr-PRNUM.rst` are inspected in order to determine
  the maximum version bump level.

- The highest-versioned tag of the form `[v]N.N.N` (It is an error if there are
  no such tags) is used as the previous release version, and it is bumped by
  the version bump level to obtain the version for the new release.

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
    - `new_version` — the version of the new release (without leading `v`)

- The repository HEAD is tagged with an annotated tag named with the version of
  the new release prefixed with `tag-prefix`, the tag is pushed to GitHub, and
  `scriv github-release` is run.

- If the `pypi-token` input is not empty, then `python -m build` is run,
  followed by `twine upload dist/*`

## Usage

```yaml
- name: Add changelog snippet
  uses: datalad/release-action/release@master
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
| `tag-prefix` | String to prepend to the name of the created tag | [empty] |
| `token` | GitHub token to use for interacting with the GitHub API; just using `${{ secrets.GITHUB_TOKEN }}` is recommended | *(required)* |

## Output

| Key           | Meaning |
| ------------- | ------- |
| `new-version` | The version of the new release (without leading `v`) |

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

jobs:
  release:
    runs-on: ubuntu-latest
    # Only run for merged PRs with the "release" label:
    if: github.event.pull_request.merged == true && contains(github.event.pull_request.labels.*.name, 'release')
    steps:
      - name: Checkout source
        uses: actions/checkout@v3
        with:
          # Check out all history so that the previous release tag can be
          # found:
          fetch-depth: 0

      - name: Prepare release
        uses: datalad/release-action/release@master
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
```
