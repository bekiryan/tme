@echo off
python -m pip install --upgrade pip
python -m pip install scrapy scrapy-xlsx pandas selenium-profiles selenium-wire

cd ipneumatics
scrapy crawl mycrawler -o ..\output.xlsx -o ..\output.json --nolog

cd ..
python parse_to_excel.py
echo Process finished !!!
pause

