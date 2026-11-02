import random
import time

import pyodbc
from pymongo import MongoClient

mongo = MongoClient("mongodb://localhost:27017")["uni_portfolio"]["portfolios"]

conn = pyodbc.connect(
    r"DRIVER={ODBC Driver 18 for SQL Server};"
    r"SERVER=(localdb)\MSSQLLocalDB;"
    r"DATABASE=Uni;"
    r"Trusted_Connection=yes;"
    r"TrustServerCertificate=yes;"
)
sql = conn.cursor()

sql.execute("SELECT StudentID FROM Portfolio")
all_ids = [row[0] for row in sql.fetchall()]
random.seed(1)
student_ids = random.sample(all_ids, 5000)
print("Портфоліо в SQL Server:", len(all_ids))
print("Портфоліо в MongoDB:", mongo.count_documents({}))


def time_ms(func):
    start = time.perf_counter()
    func()
    return (time.perf_counter() - start) * 1000


def mongo_read():
    for sid in student_ids:
        mongo.find_one({"studentId": sid})


def sql_read():
    for sid in student_ids:
        sql.execute(
            "SELECT t.Code, a.Title, a.[Year] "
            "FROM Portfolio p "
            "LEFT JOIN Achievement a ON a.PortfolioID = p.ID "
            "LEFT JOIN AchievementType t ON t.ID = a.TypeID "
            "WHERE p.StudentID = ?", sid)
        sql.fetchall()
        sql.execute(
            "SELECT ps.SkillName FROM Portfolio p "
            "JOIN PortfolioSkill ps ON ps.PortfolioID = p.ID "
            "WHERE p.StudentID = ?", sid)
        sql.fetchall()


mongo_read()
sql_read()
t_mongo = time_ms(mongo_read)
t_sql = time_ms(sql_read)
print("\nТест 1. Прочитати портфоліо 5000 студентів")
print(f"  SQL Server: {t_sql:.0f} мс (в середньому {t_sql / 5000:.3f} мс на студента)")
print(f"  MongoDB:    {t_mongo:.0f} мс (в середньому {t_mongo / 5000:.3f} мс на студента)")


def mongo_count():
    return list(mongo.aggregate([
        {"$unwind": "$achievements"},
        {"$group": {"_id": "$achievements.type", "count": {"$sum": 1}}},
    ]))


def sql_count():
    sql.execute(
        "SELECT t.Code, COUNT(*) FROM Achievement a "
        "JOIN AchievementType t ON t.ID = a.TypeID "
        "GROUP BY t.Code")
    return sql.fetchall()


mongo_count()
sql_count()
t_mongo = time_ms(mongo_count)
t_sql = time_ms(sql_count)
print("\nТест 2. Порахувати досягнення за типами по всій базі")
print(f"  SQL Server: {t_sql:.0f} мс")
print(f"  MongoDB:    {t_mongo:.0f} мс")

conn.close()
