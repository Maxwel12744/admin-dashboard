import pymysql

# Lets Django use PyMySQL (pure Python) instead of mysqlclient, which usually
# cannot be built on Vercel.
pymysql.version_info = (2, 2, 1, "final", 0)
pymysql.install_as_MySQLdb()
