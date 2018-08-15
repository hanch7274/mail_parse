from selenium import webdriver
from time import sleep
import os,sys
import datetime
import re
import requests
import urllib
import unicodedata
import csv
import hashlib
import pymysql
import collections

def get_kor_today(): #ex) 8월 1일, 8월 10일, 10월 3일~
    today = datetime.datetime.now().strftime('%m-%e').replace('-','월 ')+'일'
    if(int(today[:2])<10):
       today=today[1:]
       return today

def down_image(image_url,binary):
    if not os.path.isdir(image_dir):
        os.mkdir(image_dir)
    if not os.path.isdir(image_dir+today):
        os.mkdir(image_dir+today)
    global file_name
    file_name= image_url.replace('http://fl0ckfl0ck.info/',"")
    with open(image_dir+today+'\\'+file_name,'wb') as f:
        f.write(binary)

def get_gps(file_name):
    from GPSPhoto import gpsphoto
    gps_data = gpsphoto.getGPSData(file_name)
    try:
        return gps_data['Latitude'],gps_data['Longitude']
    except:
        return [] #exif 파일이 아닐 경우 빈 값 리턴

def write_csv(date,short_url,ori_url,file_name,gps,image_MD5,image_SHA1):
    exist_flag = 0
    global csv_line
    line=0
    if gps == []: # gps가 없는 이미지의 경우
        gps.append(None)
        gps.append(None)
    try:
        #기존에 파일이 있을때(오후)
        with open(image_dir+today+'\\'+'result.csv', mode='r', encoding='utf-8') as read_file:
            reader = csv.reader(read_file)
            for i in reader:
                line+=1
            csv_line = line
        with open(image_dir+today+'\\'+'result.csv', mode='a', encoding='utf-8',newline='') as write_file:
            writer = csv.writer(write_file)
            writer.writerow([csv_line,date,short_url,ori_url,file_name,gps[0],gps[1],image_MD5,image_SHA1])
            csv_line+=1
    except FileNotFoundError:
        #파일이 없을때(오전)
        with open(image_dir+today+'\\'+'result.csv', mode='w', encoding='utf-8',newline='') as write_file:
            writer = csv.writer(write_file)
            writer.writerow(['Number','Date','Shortened URL','Full URL','FileName','Latitude','Longitude','MD5','SHA1'])                
            csv_line +=1
            writer.writerow([csv_line,date,short_url,ori_url,file_name,gps[0],gps[1],image_MD5,image_SHA1])
            csv_line +=1
            
def draw_gmap(file_handle):
    from gmplot import gmplot
    lat = []
    lon = []
    with open(file_handle, mode='r', encoding='utf-8') as read_file:
        reader = csv.reader(read_file)
        read_list = list(reader)
        read_list.pop(0)
        for i in read_list: #gps정보를 읽고, gps가없는 사진은 건너뜀
            if i[5] != '':
                lat.append(float(i[5]))
            else:
                continue 
        for i in read_list:
            if i[6] !='':
                lon.append(float(i[6]))
            else:
                continue
    if lat == []:
        return None
    gmap = gmplot.GoogleMapPlotter(lat[0], lon[0], 8)
    gmap.plot(lat, lon, 'cornflowerblue', edge_width=7)
    for i, j in zip(lat,lon):
        gmap.marker(i,j, 'red')
    gmap.draw(image_dir+today+'\\'+'map('+today+').html')

def input_db(date,short_url,ori_url,file_name,gps,image_MD5,image_SHA1):
    db = pymysql.connect(host='127.0.0.1',port=3306,user='root',passwd='root',db='mail_parse',charset='utf8mb4')
    cursor = db.cursor()
    sql = '''INSERT INTO mail_data (Date,Shortened_URL,Full_URL,FileName,Latitude,Longitude,MD5,SHA1)
VALUES(%s,%s,%s,%s,%s,%s,%s,%s)'''
    cursor.execute(sql,(date,short_url,ori_url,file_name,gps[0],gps[1],image_MD5,image_SHA1))
    db.commit()
    db.close()

#더러운 변수들 저장용
mail_url = ('https://gmail.com')
inbox_url = ('https://mail.google.com/mail/u/0/h/1pq68r75kzvdr/?v%3Dlui') #Javascript버전 Gmail은 xPath값이 랜덤값이어서 HTML버전으로 파싱
xpath_sender = '/html/body/table[2]/tbody/tr/td[2]/table[1]/tbody/tr/td[2]/form/table[2]/tbody/tr[{}]/td[2]' #i번째 행 2번째 열(보낸이)
xpath_date = '/html/body/table[2]/tbody/tr/td[2]/table[1]/tbody/tr/td[2]/form/table[2]/tbody/tr[{}]/td[4]' #i번째 행 4번째 열(보낸 날짜)
xpath_body = '/html/body/table[2]/tbody/tr/td[2]/table[1]/tbody/tr/td[2]/form/table[2]/tbody/tr[{}]/td[3]/a/span/font[2]' #i번째 행 3번째 열(본문)
p = re.compile('https://bit.ly/\w{7}|http://bitly.kr/\w{4}|https://hoy.kr/\w{4}')

link_dict = collections.OrderedDict()#딕셔너리 순회를 위해 OrderedDict 객체 생성
image_dir = 'C:\\Users\\hanch\\Desktop\\image_dir\\'
file_name =""
today = str(datetime.datetime.today().date())
#today = '2018-08-04'
csv_line = 0

#지메일 
driver = webdriver.Chrome("C:\\Users\\hanch\\Desktop\\chromedriver")
driver.get(mail_url)
driver.switch_to_default_content()
driver.find_element_by_xpath('//*[@id="identifierId"]').send_keys(sys.argv]1])
driver.find_element_by_xpath('//*[@id="identifierNext"]').click()
sleep(2)
driver.find_element_by_xpath('//*[@id="password"]/div[1]/div/div[1]/input').send_keys(sys.argv[2])
driver.find_element_by_xpath('//*[@id="passwordNext"]/content').click()
sleep(2)
driver.get(inbox_url)
sleep(2)

# 야매로 메일 갯수 구하기 (하루에 온 메일 50개 넘어가면 오류)
mail_count=0
try:
    for i in range(1,51):
        if driver.find_element_by_xpath('/html/body/table[2]/tbody/tr/td[2]/table[1]/tbody/tr/td[2]/form/table[2]/tbody/tr[{}]'.format(i)).text:
            mail_count+=1
except:
    pass #인덱싱오류 발생시 종료
	
#메일 송신자, 오늘날짜 비교하여 본문 파싱
try:
    for i in range(mail_count-1,0,-1):
        if driver.find_element_by_xpath(xpath_sender.format(i)).text == 'Kyle Choi':
            if driver.find_element_by_xpath(xpath_date.format(i)).text == get_kor_today():
                mail_body = driver.find_element_by_xpath(xpath_body.format(i)).text
                parse_mail_body = p.findall(mail_body)
                link = ''.join(parse_mail_body)
                driver.find_element_by_xpath(xpath_body.format(i)).click()
                date = driver.find_element_by_xpath('/html/body/table[2]/tbody/tr/td[2]/table[1]/tbody/tr/td[2]/table[4]/tbody/tr/td/table[1]/tbody/tr[1]/td[2]').text
                #메일 본문으로 들어가서 날짜 파싱.
                link_dict[link] = date #link는 고유하지만 date는 여러개이기 때문에
                driver.back()
except:
    pass
	
#딕셔너리 순회
for link, date in link_dict.items():
    res = requests.get(link)
    ori_url = urllib.parse.unquote(res.url)
    image_url = unicodedata.normalize('NFC',ori_url)
    print('image_url = '+ image_url)
    down_image(image_url,res.content)
    gps = get_gps(image_dir+today+'\\'+file_name)
    image_MD5 = hashlib.md5(res.content).hexdigest()
    image_SHA1 = hashlib.sha1(res.content).hexdigest()
    write_csv(date,link,ori_url,file_name,gps,image_MD5,image_SHA1) #날짜값에 시간정보 포함x
    draw_gmap(image_dir+today+'\\'+'result.csv')
    input_db(date,link,ori_url,file_name,gps,image_MD5,image_SHA1)
