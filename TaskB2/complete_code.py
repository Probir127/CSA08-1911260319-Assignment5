import sqlite3
readings = [("Adyar", "2026-10-01", 48.0), ("Guindy", "2026-10-01", 95.0),
            ("Guindy", "2026-10-03", 121.0), ("Adyar", "2026-10-04", 60.0)]
con = sqlite3.connect(":memory:")
con.execute("CREATE TABLE aq (station TEXT, day TEXT, pm25 REAL)")
con.executemany('INSERT INTO aq VALUES (?,?,?)',readings)
con.commit()
def station_average(name):
    return con.execute('SELECT AVG(pm25) FROM aq WHERE station = ?',(name,)).fetchone()[0]

print(station_average("Adyar"), station_average("Guindy"))
print(station_average("Adyar' OR '1'='1"))      # an injection attempt finds nothing
con.close()
