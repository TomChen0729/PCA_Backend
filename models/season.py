from extensions import db
from datetime import datetime

class Season(db.Model):
    __tablename__ = 'seasons'
    __table_args__ = {'comment': '大季節分類表 (春、夏、秋、冬)'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='季節唯一識別碼')
    name = db.Column(db.String(20), nullable=False, unique=True, comment='季節名稱 (例如：春季型)')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, comment='建立時間戳記')

    # 關聯到色彩型別 (One-to-Many)
    types = db.relationship('Type', backref='season_category', lazy=True)

    def __repr__(self):
        return f'<Season {self.name}>'