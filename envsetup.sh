# this file should be sourced (.), not run as a script

PARTS_BASE=$(readlink -f "$(dirname "${BASH_SOURCE[0]:-$0}")")

# define all of your libs here -- should be a CSV file for each lib
GPLMLIBS="ana cap con cpd dio ics ind mpu mcu pwr rfm res reg xtr osc opt art swi"

DBFILE=./database/parts.sqlite

parts_db_create() {
	for lib in ${GPLMLIBS}; do
		sqlite3 ${DBFILE} "DROP TABLE IF EXISTS ${lib}" || return 1
		sqlite3 --csv ${DBFILE} ".import ./database/g-${lib}.csv ${lib}" || return 1
	done
}

parts_db_watch() {
	echo "watching csv files for changes ..."
	while true; do
		FILE=$(inotifywait -q -e modify -e close_write --format '%w%f' ./database/)
		echo "csv file changed: $FILE"
		# debounce a bit as things might be moving around when libreofice is saving a file
		sleep 1
		if [[ $FILE == *.csv ]]; then
			#LIB=$(basename "${FILE%.*}")
			LIB=${FILE##*-}
			LIB=${LIB%%.*}
			echo "updating db: $LIB ..."
			sqlite3 ${DBFILE} "DROP TABLE IF EXISTS ${LIB}" || return 1
			sqlite3 --csv ${DBFILE} ".import ./database/g-${LIB}.csv ${LIB}" || return 1
		fi
	done
}

parts_db_edit() {
	sqlitebrowser ${DBFILE}
}

# Run the version of prettier pinned in .prettier-version, so formatting
# locally reaches the same verdict everywhere. A prettier release can add a rule
# and start failing a file that was passing.
parts_prettier() {
	local version
	version=$(cat "${PARTS_BASE}/.prettier-version") || return 1
	(cd "${PARTS_BASE}" && npx --yes "prettier@${version}" "$@") || return 1
}

parts_format() {
	parts_prettier --write "**/*.md" || return 1
}

parts_format_check() {
	parts_prettier --check "**/*.md" || return 1
}
