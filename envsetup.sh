# define all of your libs here -- should be a CSV file for each lib
GPLMLIBS="ana cap con cpd dio ics ind mpu mcu pwr rfm res reg xtr osc opt art"

parts_db_create() {
	for lib in ${GPLMLIBS}; do
		sqlite3 ./parts.sqlite "DROP TABLE IF EXISTS ${lib}" || return 1
		sqlite3 --csv ./parts.sqlite ".import ${lib}.csv ${lib}" || return 1
	done
}

parts_db_edit() {
	sqlitebrowser parts.sqlite
}
