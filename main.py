import math
import M5
from M5 import *
import time
import machine
import network
from hardware import *
from Secrets import WIFI_SSID, WIFI_PASSWORD, LAT_DOM, LON_DOM, RAYON_PLANE
import requests as requests
import _thread as th


def get_airport_name(code):
    global airport_name

    if code=="":
        return "N/A"

    if code in airport_name:
        return airport_name[code]
    else:
        headers = {
        "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "cache-control": "max-age=0",
        "origin": "https://www.flightradar24.com",
        "referer": "https://www.flightradar24.com/",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"}

        URL='https://www.flightradar24.com/airports/traffic-stats/?airport='+code
        try:
            reponse=requests.get(URL,headers=headers).json()
            airport_name[code]=reponse['details']['name']
        except Exception:
            airport_name[code]=code
        return airport_name[code]

def bound_calculation(lat,lon,rayon):
    R = 6378137
    angle=0
    lat_max = math.asin(math.sin(math.radians(lat)) * math.cos( rayon / R ) + math.cos( math.radians(lat) ) * math.sin( rayon / R ) * math.cos( angle ))
    angle=180
    lat_min = math.asin(math.sin(math.radians(lat)) * math.cos( rayon / R ) + math.cos( math.radians(lat) ) * math.sin( rayon / R ) * math.cos( angle ))

    angle=math.radians(90)
    lon_max = math.radians(lon) + math.atan2(math.sin(angle)*math.sin(rayon/R)*math.cos(math.radians(lat)), math.cos(rayon / R )-(math.sin(math.radians(lat)) * math.sin( math.radians(lat))))

    angle=math.radians(270)
    lon_min = math.radians(lon) + math.atan2(math.sin(angle)*math.sin(rayon/R)*math.cos(math.radians(lat)), math.cos(rayon / R )-(math.sin(math.radians(lat)) * math.sin( math.radians(lat))))

    return math.degrees(lat_min),math.degrees(lat_max),math.degrees(lon_min),math.degrees(lon_max)

def distanceGPS(latA, longA, latB, longB):
    RT = 6378137
    S = math.acos(math.sin(math.radians(latA))*math.sin(math.radians(latB)) + math.cos(math.radians(latA))*math.cos(math.radians(latB))*math.cos(abs(math.radians(longB)-math.radians(longA))))
    return S*RT

def angle_bearing(latA,longA,latB,longB):
    latA=math.radians(latA)
    longA=math.radians(longA)
    latB=math.radians(latB)
    longB=math.radians(longB)

    longDelta = longB - longA

    y = math.sin(longDelta) * math.cos(latB)
    x = math.cos(latA)*math.sin(latB) - math.sin(latA)*math.cos(latB)*math.cos(longDelta)
    Angle = math.degrees(math.atan2(y, x));
    if Angle<0:
      Angle+=360

    return Angle

def refresh_data(lat_min,lat_max,lon_min,lon_max):
    global tab_data

    headers = {
            "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "cache-control": "max-age=0",
            "origin": "https://www.flightradar24.com",
            "referer": "https://www.flightradar24.com/",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"}

    URL='https://data-cloud.flightradar24.com/zones/fcgi/feed.js?faa=1&satellite=1&mlat=1&flarm=1&adsb=1&gnd=0&air=1&vehicles=1&estimated=1&maxage=14400&gliders=1&stats=1&limit=5000&bounds='+str(lat_max)+'%2C'+str(lat_min)+'%2C'+str(lon_min)+'%2C'+str(lon_max)
    try:
        reponse=requests.get(URL,headers=headers).json()
    except Exception:
        return

    tab_data=[]
    for cle,valeur in reponse.items():
        if cle!="full_count" and cle!="version" and cle!="stats":
            dist = distanceGPS(valeur[1],valeur[2], LAT_DOM, LON_DOM)
            angle=angle_bearing(LAT_DOM, LON_DOM,valeur[1],valeur[2])
            if dist<RAYON_PLANE:
                tab_point=[]
                tab_point.append(valeur[16])
                tab_point.append(valeur[1])
                tab_point.append(valeur[2])
                tab_point.append(valeur[3])
                tab_point.append(angle)
                tab_point.append(dist)
                tab_point.append(int(valeur[4]*0.3048))
                tab_point.append(int(valeur[5]*1.852))
                tab_point.append(valeur[9])
                tab_point.append(valeur[13])
                tab_point.append(valeur[11])
                tab_point.append(valeur[12])
                tab_point.append(valeur[8])
                tab_data.append(tab_point)

def txt_mode(item):
    global mode
    if mode==0:
        return item[0]
    elif mode==1:
        return str(round(item[1],2))+':'+str(round(item[2],2))
    elif mode==2:
        return str(int(item[3]))+"°"
    elif mode==3:
        return str(int(item[5]))+'m'
    elif mode==4:
        return str(round(item[6],2))+'m'
    elif mode==5:
        return str(round(item[7],2))+'km/h'
    elif mode==6:
        return item[8]
    elif mode==7:
        return item[9]
    elif mode==8:
        return get_airport_name(item[10])
    elif mode==9:
        return get_airport_name(item[11])
    elif mode==10:
        return item[12]
    elif mode==11:
        return ""
    else:
        return "N/A"

class Rotary:
    def __init__(self, pin_a=40, pin_b=41):
        self._count = 0
        self._a = machine.Pin(pin_a, machine.Pin.IN, machine.Pin.PULL_UP)
        self._b = machine.Pin(pin_b, machine.Pin.IN, machine.Pin.PULL_UP)
        self._last_a = self._a.value()
        self._a.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING,
                    handler=self._handle)

    def _handle(self, _):
        a = self._a.value()
        if a != self._last_a:
            self._last_a = a
            if a == 0:
                self._count += 1 if self._b.value() else -1

    def get_rotary_value(self):
        return self._count

def th_button():
    global continuer,mode,tab_mode
    rotary = Rotary()
    r_count=0
    M5.update()
    while continuer:
        if M5.Touch.getCount()>0 and M5.Touch.getDetail()[4]==True:
            print("Touched")
            time.sleep_ms(200)
        rot_temp=rotary.get_rotary_value()
        if rot_temp<r_count:
            mode-=1
            if mode<0:
                mode=len(tab_mode)-1
            r_count=rot_temp
            print("Mode",mode,'-',tab_mode[mode])
        elif rot_temp>r_count:
            mode+=1
            if mode>len(tab_mode)-1:
                mode=0
            r_count=rot_temp
            print("Mode",mode,'-',tab_mode[mode])
        elif BtnA.wasSingleClicked():
            print("Clic")

        time.sleep_ms(10)
        M5.update()

def loading_screen():
    Lcd.clear()
    Lcd.drawCircle(x=120, y=120, r=110, color=0x002200)

    Lcd.setFont(Lcd.FONTS.EFontCN24)
    Lcd.setTextSize(0.5)
    Lcd.setTextColor(0x006600)
    Lcd.drawCenterString(text='BUILT BY', x=120, y=82)

    Lcd.drawLine(x0=70, y0=97, x1=170, y1=97, color=0x003300)

    Lcd.setTextSize(0.85)
    Lcd.setTextColor(0xffffff)
    Lcd.drawCenterString(text='MIL / VUS', x=120, y=106)
    Lcd.drawCenterString(text='WORKS', x=120, y=129)

    for step in range(30):
        px = 60 + (step + 1) * 4
        Lcd.drawLine(x0=60, y0=172, x1=px, y1=172, color=0x003300)
        Lcd.fillCircle(x=px, y=172, r=2, color=0x00cc00)
        time.sleep_ms(100)

    Lcd.clear()

def draw_compass():
    CX, CY, R = 120, 120, 110
    Lcd.drawCircle(x=CX, y=CY, r=R, color=0x004400)

    cardinals     = [(0,'N'), (90,'E'), (180,'S'), (270,'W')]
    intercardinals= [(45,'NE'),(135,'SE'),(225,'SW'),(315,'NW')]

    for deg, label in cardinals:
        rad = math.radians(90 - deg)
        c, s = math.cos(rad), math.sin(rad)
        Lcd.drawLine(x0=int(CX+c*100), y0=int(CY-s*100),
                     x1=int(CX+c*R),   y1=int(CY-s*R),   color=0x00aa00)
        Lcd.setFont(Lcd.FONTS.EFontCN24)
        Lcd.setTextSize(0.6)
        Lcd.setTextColor(0x00cc00)
        Lcd.drawCenterString(text=label, x=int(CX+c*88), y=int(CY-s*88)-4)

    for deg, label in intercardinals:
        rad = math.radians(90 - deg)
        c, s = math.cos(rad), math.sin(rad)
        Lcd.drawLine(x0=int(CX+c*105), y0=int(CY-s*105),
                     x1=int(CX+c*R),   y1=int(CY-s*R),   color=0x005500)
        Lcd.setTextSize(0.45)
        Lcd.setTextColor(0x007700)
        Lcd.drawCenterString(text=label, x=int(CX+c*93), y=int(CY-s*93)-4)

    for deg in range(30, 360, 30):
        if deg % 45 != 0:
            rad = math.radians(90 - deg)
            c, s = math.cos(rad), math.sin(rad)
            Lcd.drawLine(x0=int(CX+c*107), y0=int(CY-s*107),
                         x1=int(CX+c*R),   y1=int(CY-s*R),   color=0x003300)

    Lcd.setTextColor(0xffffff)

def draw_plane(x,y,cap):
    size=5
    cap=90-cap

    x1=x+math.cos(math.radians(cap))*size
    y1=y-math.sin(math.radians(cap))*size

    x2=x+math.cos(math.radians(cap+90+45))*size
    y2=y-math.sin(math.radians(cap+90+45))*size

    x3=x+math.cos(math.radians(cap-90-45))*size
    y3=y-math.sin(math.radians(cap-90-45))*size

    Lcd.fillTriangle(x0=int(x1),y0=int(y1),x1=int(x2),y1=int(y2),x2=int(x3),y2=int(y3),color=0xff0000)
    Lcd.fillTriangle(x0=int(x),y0=int(y),x1=int(x2),y1=int(y2),x2=int(x3),y2=int(y3),color=0x000000)

    return

def launch():
    global continuer, tab_data,mode,tab_mode,airport_name
    continuer = True
    rayon=110
    machine.freq(240000000)
    tab_data=[]
    loading_screen()
    th.start_new_thread(th_button,())

    tab_mode=['Callsign','Coord','Cap','Distance','Alt','Speed','Registration','Flight number','Origine','Destination','Aircraft','']
    mode=0

    airport_name={'CDG':'Paris Charles de Gaulle Airport','LBG':'Paris Le Bourget Airport','ORY':'Paris Orly Airport'}

    wlan = network.WLAN(network.STA_IF)

    if wlan.isconnected():
        wlan.disconnect()

    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    while not wlan.isconnected():
     time.sleep_ms(100)

    lat_min,lat_max,lon_min,lon_max=bound_calculation(LAT_DOM,LON_DOM,RAYON_PLANE)

    while continuer:
        refresh_data(lat_min,lat_max,lon_min,lon_max)
        Lcd.clear()
        draw_compass()

        Lcd.fillTriangle(x0=120,y0=113, x1=127,y1=127, x2=113,y2=127, color=0x00cc00)
        Lcd.fillTriangle(x0=120,y0=117, x1=124,y1=126, x2=116,y2=126, color=0x001a00)

        Lcd.setTextColor(0x444444)
        Lcd.drawCenterString(text=tab_mode[mode], x=120, y=185)
        Lcd.setTextColor(0xffffff)

        for item in tab_data:
            angle_trace=90-item[4]
            x=120+math.cos(math.radians(angle_trace))*(item[5]*rayon/RAYON_PLANE)
            y=120-math.sin(math.radians(angle_trace))*(item[5]*rayon/RAYON_PLANE)
            draw_plane(x,y,item[3])
            Lcd.setFont(Lcd.FONTS.EFontCN24)
            Lcd.setTextSize(0.6)
            Lcd.drawString(text=txt_mode(item),x=int(x)+5,y=int(y)+5)

        time.sleep_ms(2000)


    wlan.disconnect()
    Lcd.clear()

if __name__ == '__main__':
    launch()
