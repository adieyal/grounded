#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

rm -rf pages-site
mkdir -p pages-site/todo

cp -R grounded/generated/docs/. pages-site/
cp -R examples/todo/site/. pages-site/todo/
touch pages-site/.nojekyll
