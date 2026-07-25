from extensions import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    __table_args__ = {'comment': '使用者基本資料表 (管理帳號密碼與個人資訊)'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='使用者唯一識別碼')
    username = db.Column(db.String(50), nullable=False, comment='登入帳號名稱')
    mail = db.Column(db.String(120), unique=True, nullable=False, comment='聯絡與註冊信箱')
    pwd = db.Column(db.String(255), nullable=False, comment='加密後的密碼 (Hash)')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, comment='紀錄建立時間')

    # --- 關聯設定 (Relationships) ---
    # 關聯到衣櫥單品 (One-to-Many)
    wardrobe_items = db.relationship('WardrobeItem', backref='owner', lazy=True, cascade="all, delete-orphan")
    # 關聯到測色結果 (One-to-Many)
    analysis_results = db.relationship('AnalysisResult', backref='user', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<User {self.username}>'