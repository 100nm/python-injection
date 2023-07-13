bold=$(tput bold)
reset=$(tput sgr0)
cyan=$(tput setaf 6)

title() {
  if [ "$1" ]
  then
    entitled=$1
  else
    entitled="PLEASE PASS A TITLE"
  fi

  echo "${cyan}${bold}### $entitled ###${reset}"
}

set -e

title "POETRY"
poetry check

title "ISORT"
isort ./

title "BLACK"
black ./

title "FLAKE"
flake8

title "PYTEST"
pytest --cov=./ --cov-report term-missing:skip-covered
