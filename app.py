# Kamar AI Mode – نسخة نهائية جاهزة
# المفتاح مدمج .. فقط شغّل python app.py
import os, requests, json, textwrap, re
from collections import Counter
from urllib.parse import urlparse
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_babel import Babel, gettext as _

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kamar.db'
app.config['BABEL_DEFAULT_LOCALE'] = 'ar'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
babel = Babel(app)

# ==================== المفتاح مدمج جاهز ====================
API_BASE = "https://api.openwebninja.com/google-ai-mode/ai-mode"
API_KEY  = "ak_is7pbn7gl4g8mbaupwynpkfbr6lm9yfh8iurpdpuk4noou1"
# =========================================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    keyword = db.Column(db.String(200))
    lang = db.Column(db.String(5))
    data = db.Column(db.Text)

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@babel.localeselector
def get_locale():
    return session.get('lang', 'ar')

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash(_('Email already registered'))
            return redirect(url_for('register'))
        user = User(email=email, password=password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for('dashboard'))
        flash(_('Invalid credentials'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/set_lang/<lang>')
def set_lang(lang):
    session['lang'] = lang
    return redirect(request.referrer)

def fetch_ai_data(prompt, lang='ar', gl='sa'):
    params = {'prompt': prompt, 'hl': lang, 'gl': gl, 'x-api-key': API_KEY}
    r = requests.get(API_BASE, params=params)
    if r.status_code != 200:
        return None
    return r.json()

STOP_FLAIR = {"تعرف","تعلم","اكتشف","احصل","لا تفوّت","سرّ","خدعة","مذهل","رائع","أفضل 10","best","discover","amazing","top 10","secret","trick"}
def clean_flair(text):
    words = text.split()
    return " ".join(w for w in words if w.lower() not in STOP_FLAIR)

def build_meta(text):
    return textwrap.shorten(clean_flair(text), 155, placeholder="...")

def build_snippet(text):
    sent = re.split(r'[.؟!]', text)[0]
    return textwrap.shorten(clean_flair(sent), 155, placeholder="...")

def nlp_keywords(text):
    bigrams = re.findall(r'\b\w+\s\w+\b', text.lower())
    freq = Counter(bigrams)
    cleaned = [b for b in freq if not any(f in b for f in STOP_FLAIR)]
    return "، ".join(cleaned[:12])

def suggest_title(text):
    words = text.split()
    top = Counter(words).most_common(3)
    return f"{top[0][0]} {top[1][0]} {top[2][0]}: اختيارك حسب الاختبار والتجربة"

def extract_outline(text):
    sentences = re.split(r'[.؟!]', text)
    outline = []
    for sent in sentences[:6]:
        if len(sent.strip()) > 20:
            outline.append({"tag": "h3", "text": sent.strip()[:70]})
    return outline

@app.route('/analyze', methods=['POST'])
@login_required
def analyze():
    keyword = request.json.get('keyword')
    lang = session.get('lang', 'ar')
    gl_map = {'ar':'sa','en':'us','es':'es','pt':'br'}
    data = fetch_ai_data(keyword, lang, gl_map.get(lang,'sa'))
    if not data:
        return jsonify({'error': _('API error')}), 500

    answer = data.get('answer','')
    refs   = data.get('references',[])

    result = {
        'focus_keyword': keyword,
        'ai_overview_sources': list({urlparse(r).hostname for r in refs}),
        'featured_snippets': [answer],
        'suggested_title': clean_flair(suggest_title(answer)),
        'nlp_keywords': nlp_keywords(answer),
        'meta_description': build_meta(answer),
        'snippet_text': build_snippet(answer),
        'outline': extract_outline(answer)
    }

    save = Result(user_id=current_user.id, keyword=keyword, lang=lang, data=json.dumps(result, ensure_ascii=False))
    db.session.add(save)
    db.session.commit()

    return jsonify(result)

@app.route('/history')
@login_required
def history():
    records = Result.query.filter_by(user_id=current_user.id).order_by(Result.id.desc()).all()
    return render_template('history.html', records=records)

if __name__ == '__main__':
    app.run(debug=True)