
### Project Description:
-----
Fast API Project for CRUD Operation & API serving using sqlalchemy. <br>
DB: PostgreSQL- 17.4


### Installation & Run: 
-----
Rename .env.example to .env

```
docker-compose build 
```

Then 

```
docker-compose up   
```
or to run demon mode

```
docker-compose up   -d
```



Visit: 
http://127.0.0.1:8004/docs


Log in API: 

make sure you must give grant_type=password

```
curl -X 'POST' \
  'http://0.0.0.0:8004/log_in' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=password&username=tareqcse12%40gmail.com&password=admin123&scope=&client_id=&client_secret='

```

Create Topic API

```
curl --location 'http://0.0.0.0:8004/topics' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0YXJlcWNzZTEyQGdtYWlsLmNvbSIsImV4cCI6MTc0NTQ5MjExOX0.QfkL7NQkzG-gL7KupkYLzptefRBsy9iFTk0XiAmzuzg' \
--data '{
  "title": "string",
  "description": "string",
  "created_by": 0
}'
```