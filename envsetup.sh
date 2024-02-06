parts_db_create() {
	rm parts.sqlite

	# define all of your libs here -- should be a CSV file for each lib
	libs="cap con dio ind mpu res reg"

	for lib in $libs; do
		sqlite3 --csv ./parts.sqlite ".import ${lib}.csv ${lib}" || return 1
	done
}

parts_db_edit() {
	sqlitebrowser parts.sqlite
}
