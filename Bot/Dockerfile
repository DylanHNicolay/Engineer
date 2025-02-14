FROM python:3.12-slim

WORKDIR /EngineerBot

COPY requirements.txt ./

RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "-u", "main.py"]