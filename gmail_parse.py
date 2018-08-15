import imaplib
import email
import email.utils
import datetime
import base64
import re
import os, sys
import requests
import urllib
import unicodedata #NFD to NFC
import csv
import hashlib
import pymysql

today = str(datetime.datetime.today().date())# YYYY-MM-DD
#today = '2018-08-11'
#day_from = '11-Aug-2018'
#day_to = '12-Aug-2018'
image_dir = 'C:\\Users\\hanch\\Desktop\\image_dir\\'
file_name =""
get_email = list()
url_list= list()
csv_line = 0 # csv Number행 넘버링을 위한 변수

#튜플 중복제거
def remove_dup(li):
    temp_set = set()
    ret_list = list()
    for i in li:
        if i not in temp_set:
            ret_list.append(i)
            temp_set.add(i)
    return ret_list

#mail Login
def gmail_login(g_id,g_pw):
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(g_id,g_pw)
    return mail

#Mail 본문만 가져오기
def get_text(email_message_instance):
    maintype = email_message_instance.get_content_maintype()
    for part in email_message_instance.get_payload():
         return part.get_payload()
#Mail 날짜 가져오기
def get_date(email_message_instance):
    msg = email.message_from_bytes(email_message_instance)
    date_tuple = email.utils.parsedate_tz(msg['Date'])
    if date_tuple: 
        local_date = datetime.datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
        return local_date
    return False

#바이너리 저장
def down_image(image_url,binary): 
    if not os.path.isdir(image_dir):
        os.mkdir(image_dir)
    if not os.path.isdir(image_dir+today):
        os.mkdir(image_dir+today)
    global file_name
    file_name= image_url.replace('http://fl0ckfl0ck.info/',"") #전체 url에서 파일 이름만 골라내기
    with open(image_dir+today+'\\'+file_name,'wb') as f:
        f.write(binary)
        
def get_gps(file_name): #gps 데이터 파싱
    from GPSPhoto import gpsphoto
    gps_data = gpsphoto.getGPSData(file_name)
    try:
        return gps_data['Latitude'],gps_data['Longitude']
    except:
        return [] #exif 파일이 아닐 경우 빈 값 리턴

def compare_csv(url): #email 모듈 에러처리
#몇몇 메일이 그전 메일 본문을 같이 포함하고 있는 경우가 있음.(중복제거)
    try:
        with open(image_dir+today+'\\'+'result.csv', mode='r', encoding='utf-8') as read_file:
            reader = csv.reader(read_file)
            for i in reader:
                if url in i[2]:
                    return True
        return False
    except FileNotFoundError:
        return False

#CSV에 그날 데이터 기록
def write_csv(date,short_url,ori_url,file_name,gps,image_MD5,image_SHA1):
    exist_flag = 0
    global csv_line
    line=0
    if gps == []: # gps가 없는 이미지의 경우
        gps.append(None)
        gps.append(None)
    try:
        #기존에 파일이 있을때
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
        #파일이 없을때
        with open(image_dir+today+'\\'+'result.csv', mode='w', encoding='utf-8',newline='') as write_file:
            writer = csv.writer(write_file)
            writer.writerow(['Number','Date','Shortened URL','Full URL','FileName','Latitude','Longitude','MD5','SHA1'])                
            csv_line +=1
            writer.writerow([csv_line,date,short_url,ori_url,file_name,gps[0],gps[1],image_MD5,image_SHA1])
            csv_line +=1

#GPS정보 파싱하여 GoogleMap에 표시
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

#DB에 데이터 삽입
def input_db(date,short_url,ori_url,file_name,gps,image_MD5,image_SHA1):
    db = pymysql.connect(host='127.0.0.1',port=3306,user='root',passwd='root',db='mail_parse',charset='utf8mb4')
    cursor = db.cursor()
    sql = '''INSERT INTO mail_data (Date,Shortened_URL,Full_URL,FileName,Latitude,Longitude,MD5,SHA1)
VALUES(%s,%s,%s,%s,%s,%s,%s,%s)'''
    cursor.execute(sql,(date,short_url,ori_url,file_name,gps[0],gps[1],image_MD5,image_SHA1))
    db.commit()
    db.close()

user_id = sys.argv[1]
user_pw = sys.argv[2]
mail = gmail_login(user_id,user_pw)
mail.select('inbox')
##오늘날짜에서 읽지않은 메일 가져오기
#result, data = mail.uid('search', None, '(SENTSINCE {day_from} UNSEEN SENTBEFORE {day_to} FROM "fl0ckfl0ck@hotmail.com")'.format(day_from=day_from,day_to=day_to))
#특정 주소지로부터 온 메일 중 안읽은 메일만 불러오기
result, data = mail.uid('search', None, '(UNSEEN FROM "fl0ckfl0ck@hotmail.com")')


#메일에서 URL 파싱하기
for latest_email_uid in data[0].split():
    result, data = mail.uid('fetch', latest_email_uid, '(RFC822)')
    raw_email = data[0][1]
    email_message = email.message_from_string(raw_email.decode())
    try:
        get_email.append(base64.b64decode(get_text(email_message)).decode('euc-kr'))          
    except:
        get_email.append((get_text(email_message))) #일부 이메일이 base64로 인코딩 되지 않음
p = re.compile('https://bit.ly/\w{7}|http://bitly.kr/\w{4}|https://hoy.kr/\w{4}')
#파싱된URL 리스트에 넣기(메일 순서 지키며 중복제거)
for i in get_email:
    string = p.findall(i)
    if len(string)>1:
        for j in string:
            url_list.append(j)
    else:
        url_list.append("".join(string))
url_list = remove_dup(url_list)
#URL 리스트에서 데이터 뽑기
for short_url in url_list:
    if compare_csv(short_url):
        continue # 메일 로딩 오류로 이전 메일 본문이 같이 로딩되는 경우 건너뜀
    res = requests.get(short_url)
    ori_url = urllib.parse.unquote(res.url) # URL Decode
    image_url = unicodedata.normalize('NFC',ori_url) # NFD to NFC
    down_image(image_url,res.content) # Image download
    gps = get_gps(image_dir+today+'\\'+file_name)
    date = get_date(data[0][1])
    image_MD5 = hashlib.md5(res.content).hexdigest()
    image_SHA1 = hashlib.sha1(res.content).hexdigest()
    write_csv(str(date.date())+" "+str(date.time())[:5],short_url,ori_url,file_name,gps,image_MD5,image_SHA1)
    draw_gmap(image_dir+today+'\\'+'result.csv')
    input_db(str(date.date())+" "+str(date.time())[:5],short_url,ori_url,file_name,gps,image_MD5,image_SHA1)
