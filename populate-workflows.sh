#!/bin/bash
set -ex
cd "${1:?Usage: $0 repo-dir}"
test -e .git
mkdir -p .github/workflows

cat > add-changelog-snippet.yml <<'EOT'
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
EOT

cat > .github/workflows/release.yml <<'EOT'
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
EOT
