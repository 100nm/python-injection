bold=$(tput bold)
reset=$(tput sgr0)
cyan=$(tput setaf 6)

title() {
  echo "${cyan}${bold}### $1 ###${reset}"
}

set -e

title "POETRY"
poetry check

title "RUFF"
ruff format
ruff check --fix

title "PYTEST"
pytest --cov=./ --cov-report term-missing:skip-covered
