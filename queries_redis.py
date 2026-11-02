import time
import fakeredis
r = fakeredis.FakeRedis(decode_responses=True)
# SET / GET

r.set("demo:student:1", "Тарас Гончар")
print(r.get("demo:student:1"))

# SET ... EX:

r.set("demo:portfolio:1", '{"skills": ["Python", "SQL"]}', ex=2)
print(r.get("demo:portfolio:1"))
time.sleep(3)
print(r.get("demo:portfolio:1"))

# INCR
r.incr("demo:views:1")
r.incr("demo:views:1")
print(r.get("demo:views:1"))

# HSET / HGETALL
r.hset("demo:skills:1", mapping={"Python": 4, "SQL": 5})
print(r.hgetall("demo:skills:1"))

# DEL / EXISTS
r.delete("demo:student:1")
print(r.exists("demo:student:1"))   
