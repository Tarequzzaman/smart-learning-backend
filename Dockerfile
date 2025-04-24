FROM python:3.13

# set work directory
WORKDIR /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies

COPY requirements.txt .
COPY [ "requirements.txt",  "./"]

RUN pip install --upgrade pip
RUN pip install -r requirements.txt 
# copy project
COPY . .