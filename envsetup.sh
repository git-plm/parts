# define all of your libs here -- should be a CSV file for each lib
GPLMLIBS=(ana cap con cpd dio ics ind mpu mcu pwr rfm res reg xtr osc opt art swi)

DBFILE=./database/parts.sqlite

parts_db_create() {
  printf "Will process these libs:\n"
  for lib in "${GPLMLIBS[@]}"; do
    echo "- $lib"
  done

  for lib in "${GPLMLIBS[@]}"; do
    if [[ ! -f "$CSVFILE" ]]; then
      CSVFILE="./database/g-${lib}.csv"
      echo "CSV file not found: $CSVFILE"
      continue
    fi
    sqlite3 "$DBFILE" "DROP TABLE IF EXISTS ${lib}" || return 1
    sqlite3 --csv "$DBFILE" ".import ./database/g-${lib}.csv ${lib}" || return 1
  done
  echo "generated $DBFILE"
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
      sqlite3 "$DBFILE" "DROP TABLE IF EXISTS ${LIB}" || return 1
      sqlite3 --csv "$DBFILE" ".import ./database/g-${LIB}.csv ${LIB}" || return 1
    fi
  done
}

parts_db_edit() {
  sqlitebrowser "$DBFILE"
}
