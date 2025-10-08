# Powershell script for windows (not tested)
# Define all libraries as an array
$GPLMLIBS = @('ana', 'cap', 'con', 'cpd', 'dio', 'ics', 'ind', 'mpu', 'mcu', 'pwr', 'rfm', 'res', 'reg', 'xtr', 'osc', 'opt', 'art', 'swi')

# Path to the SQLite database file
$DBFILE = ".\database\parts.sqlite"

# Function to create the parts database
function Invoke-PartsDbCreate {
    foreach ($lib in $GPLMLIBS) {
        Write-Host "Processing library $lib..."

        # Drop table if exists
        sqlite3 $DBFILE "DROP TABLE IF EXISTS $lib"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Failed to drop table $lib"
            exit 1
        }

        # Import CSV
        sqlite3 -csv $DBFILE ".import .\database\g-$lib.csv $lib"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Failed to import CSV for $lib"
            exit 1
        }
    }
    exit 0
}

# Main script
Invoke-PartsDbCreate
