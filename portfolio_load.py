
# наповнення MongoDB і SQL Server однаковими даними портфоліо.
import random
import time

import pyodbc
from pymongo import MongoClient, ASCENDING

SQL_SERVER = r"(localdb)\MSSQLLocalDB"
SQL_DATABASE = "Uni"
MONGO_URI = "mongodb://localhost:27017"
MONGO_DB = "uni_portfolio"
MONGO_COLLECTION = "portfolios"

TEST_STUDENTS = 20000            
TEST_GROUP = "ТЕСТ-ПОРТФОЛІО"    
SPECIALIZATION_ID = 2            

BATCH = 5000                     
random.seed(42)                 


FIRST_NAMES = ["Олександр", "Андрій", "Максим", "Дмитро", "Іван", "Тарас", "Богдан", "Артем",
               "Олена", "Марія", "Анна", "Софія", "Наталія", "Катерина", "Юлія", "Вікторія"]
LAST_NAMES = ["Шевченко", "Коваленко", "Бондаренко", "Ткаченко", "Кравченко", "Мельник",
              "Мазур", "Савченко", "Петренко", "Гончар", "Лисенко", "Руденко", "Мороз", "Білик"]
MIDDLE_NAMES = ["Петрович", "Іванович", "Олексійович", "Андріївна", "Іванівна", "Сергіївна"]

SKILLS = ["C#", "SQL", "Python", "Java", "JavaScript", "C++", "HTML/CSS", "Git", "Docker",
          "Linux", "Excel", "Power BI", "англійська B2", "англійська C1", "аналітика даних",
          "тестування ПЗ", "робота в команді", "презентації"]

TYPES = {
    "olympiad": {
        "titles": ["Олімпіада з інформатики", "Олімпіада з математики", "Хакатон університету",
                   "Олімпіада з програмування", "Конкурс студентських робіт"],
        "attrs": lambda: {"place": random.randint(1, 10)},
    },
    "certificate": {
        "titles": ["SQL for Data Analysis", "Python для початківців", "C# Fundamentals",
                   "Основи Git", "Англійська для IT", "Web Development Basics"],
        "attrs": lambda: {"issuer": random.choice(["Coursera", "Udemy", "Prometheus", "EPAM", "Cisco"]),
                          "hours": random.randint(8, 120)},
    },
    "internship": {
        "titles": ["SoftServe", "EPAM", "GlobalLogic", "Ciklum", "Luxoft", "Нова пошта"],
        "attrs": lambda: {"position": random.choice(["Junior Developer", "QA Trainee", "Data Analyst Intern",
                                                     "Support Engineer"]),
                          "months": random.randint(1, 6)},
    },
    "publication": {
        "titles": ["Огляд NoSQL баз даних", "Аналіз алгоритмів сортування", "Системи управління навчанням",
                   "Оптимізація SQL запитів", "Застосування машинного навчання"],
        "attrs": lambda: {"journal": random.choice(["Студентський вісник", "Науковий журнал університету",
                                                    "Збірник тез конференції"])},
    },
}
TYPE_CODES = list(TYPES.keys())


#  генерація 
def make_portfolio(student_id):  
    count = random.choices([0, 1, 2, 3, 4, 5], weights=[10, 20, 25, 20, 15, 10])[0]
    achievements = []
    for _ in range(count):
        code = random.choice(TYPE_CODES)
        spec = TYPES[code]
        item = {"type": code, "title": random.choice(spec["titles"]), "year": random.randint(2022, 2026)}
        item.update(spec["attrs"]())
        achievements.append(item)
    skills = random.sample(SKILLS, k=random.randint(3, 8))
    return {"studentId": student_id, "achievements": achievements, "skills": skills}


# sql
def pick_driver():
    drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
    odbc = sorted([d for d in drivers if d.startswith("ODBC Driver")], reverse=True)
    if odbc:
        return odbc[0]
    if drivers:
        return drivers[0]
    raise SystemExit("Не знайдено ODBC-драйвер для SQL Server")


def sql_connect():
    driver = pick_driver()
    print("Драйвер SQL:", driver)
    conn_str = (f"DRIVER={{{driver}}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
                "Trusted_Connection=yes;TrustServerCertificate=yes;")
    return pyodbc.connect(conn_str)


def ensure_test_students(conn):
   
    cur = conn.cursor()
    cur.execute("SELECT ID FROM SGroup WHERE Name = ?", TEST_GROUP)
    row = cur.fetchone()
    if row is None:
        cur.execute("INSERT INTO SGroup (SpecializationID, Name, StartYear, EndYear) VALUES (?, ?, 2026, 2030)",
                    SPECIALIZATION_ID, TEST_GROUP)
        cur.execute("SELECT ID FROM SGroup WHERE Name = ?", TEST_GROUP)
        row = cur.fetchone()
    group_id = row[0]

    cur.execute("SELECT COUNT(*) FROM Student WHERE GroupID = ?", group_id)
    have = cur.fetchone()[0]
    need = TEST_STUDENTS - have
    if need > 0:
        rows = [(group_id, random.choice(FIRST_NAMES), random.choice(MIDDLE_NAMES), random.choice(LAST_NAMES))
                for _ in range(need)]
        cur.fast_executemany = True
        cur.executemany("INSERT INTO Student (GroupID, FirstName, MiddleName, LastName) VALUES (?, ?, ?, ?)", rows)
    conn.commit()
    print(f"Тестових студентів у групі {TEST_GROUP}: {max(have, TEST_STUDENTS)} (додано {max(need, 0)})")


def load_sql(conn, portfolios):
    cur = conn.cursor()
    cur.fast_executemany = True

    cur.execute("DELETE FROM Achievement")
    cur.execute("DELETE FROM PortfolioSkill")
    cur.execute("DELETE FROM Portfolio")

    cur.execute("SELECT Code, ID FROM AchievementType")
    type_ids = {code: type_id for code, type_id in cur.fetchall()}

    portfolio_rows, achievements, skills = [], [], []
    achievement_id = 0
    for portfolio_id, p in enumerate(portfolios, start=1):
        portfolio_rows.append((portfolio_id, p["studentId"]))
        for a in p["achievements"]:
            achievement_id += 1         
            achievements.append((achievement_id, portfolio_id, type_ids[a["type"]], a["title"], a["year"],
                                 a.get("place"), a.get("issuer"), a.get("hours"),
                                 a.get("position"), a.get("months"), a.get("journal")))
        for s in p["skills"]:
            skills.append((portfolio_id, s))

    cur.execute("SET IDENTITY_INSERT Portfolio ON")
    for i in range(0, len(portfolio_rows), BATCH):
        cur.executemany("INSERT INTO Portfolio (ID, StudentID) VALUES (?, ?)", portfolio_rows[i:i + BATCH])
    cur.execute("SET IDENTITY_INSERT Portfolio OFF")

    cur.fast_executemany = False
    cur.execute("SET IDENTITY_INSERT Achievement ON")
    for i in range(0, len(achievements), BATCH):
        cur.executemany(
            "INSERT INTO Achievement (ID, PortfolioID, TypeID, Title, [Year], Place, Issuer, Hours, Position, Months, Journal) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", achievements[i:i + BATCH])
    cur.execute("SET IDENTITY_INSERT Achievement OFF")
    cur.fast_executemany = True

    for i in range(0, len(skills), BATCH):
        cur.executemany("INSERT INTO PortfolioSkill (PortfolioID, SkillName) VALUES (?, ?)", skills[i:i + BATCH])
    conn.commit()
    return len(portfolio_rows), len(achievements), len(skills)

def load_mongo(portfolios):
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[MONGO_DB]
    db.drop_collection(MONGO_COLLECTION)

    validator = {"$jsonSchema": {
        "bsonType": "object",
        "required": ["studentId", "achievements", "skills"],
        "properties": {
            "studentId": {"bsonType": "int"},
            "achievements": {
                "bsonType": "array",
                "items": {
                    "bsonType": "object",
                    "required": ["type", "title", "year"],
                    "properties": {
                        "type": {"enum": TYPE_CODES},
                        "title": {"bsonType": "string"},
                        "year": {"bsonType": "int", "minimum": 2000, "maximum": 2100},
                    },
                },
            },
            "skills": {"bsonType": "array", "items": {"bsonType": "string"}},
        },
    }}
    db.create_collection(MONGO_COLLECTION, validator=validator)
    col = db[MONGO_COLLECTION]

    for i in range(0, len(portfolios), BATCH):
        col.insert_many([dict(p) for p in portfolios[i:i + BATCH]])

    col.create_index([("studentId", ASCENDING)], unique=True)
    col.create_index([("achievements.type", ASCENDING)])
    return col.count_documents({})

def main():
    conn = sql_connect()
    ensure_test_students(conn)

    cur = conn.cursor()
    cur.execute("SELECT ID FROM Student WHERE IsDeleted = 0 ORDER BY ID")
    student_ids = [r[0] for r in cur.fetchall()]
    print("Активних студентів у SQL:", len(student_ids))

    portfolios = [make_portfolio(sid) for sid in student_ids]

    t = time.perf_counter()
    docs = load_mongo(portfolios)
    print(f"MongoDB: записано документів {docs} за {time.perf_counter() - t:.1f} с")

    t = time.perf_counter()
    n_p, a, sk = load_sql(conn, portfolios)
    print(f"SQL: Portfolio {n_p}, Achievement {a}, PortfolioSkill {sk} за {time.perf_counter() - t:.1f} с")

    conn.close()
    print("Готово.")


if __name__ == "__main__":
    main()
