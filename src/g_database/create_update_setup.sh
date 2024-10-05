# define all of your libs here -- should be a CSV file for each lib
GPLMLIBS="ana cap cnn cpd dio ics ind mpu mcu pwr rfm res reg xtr osc opt art swi"

parts_db_create() {
	for lib in ${GPLMLIBS}; do
		sqlite3 ./parts.sqlite "DROP TABLE IF EXISTS ${lib}" || return 1
		sqlite3 --csv ./parts.sqlite ".import ${lib}.csv ${lib}" || return 1
	done
}

parts_db_watch() {
	echo "watching csv files for changes ..."
	while true; do
		FILE=$(inotifywait -q -e modify -e close_write --format '%w%f' ./*.csv)
		echo "csv file changed: $FILE"
		# debounce a bit as things might be moving around when libreofice is saving a file
		sleep 1
		LIB=$(basename "${FILE%.*}")
		echo "updating db: $LIB ..."
		sqlite3 ./parts.sqlite "DROP TABLE IF EXISTS ${LIB}" || return 1
		sqlite3 --csv ./parts.sqlite ".import ${LIB}.csv ${LIB}" || return 1
	done
}

parts_db_edit() {
	sqlitebrowser parts.sqlite
}
