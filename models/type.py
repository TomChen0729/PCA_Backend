from extensions import db
from datetime import datetime

class Type(db.Model):
    __tablename__ = 'types'
    __table_args__ = {'comment': '色彩型別表 (季節下的細分)'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='型別唯一識別碼')
    sid = db.Column(db.Integer, db.ForeignKey('seasons.id'), nullable=False, comment='隸屬的大季節 ID')
    name = db.Column(db.String(50), nullable=False, comment='型別名稱 (例如：淺春型)')
    eng_name = db.Column(db.String(50), nullable=True, comment='英文型別名稱 (例如：Light Spring)')
    description = db.Column(db.Text, nullable=True, comment='該型別的特徵描述與穿搭建議')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, comment='建立時間戳記')

    # 關聯到專屬色彩庫 (One-to-Many)
    colors = db.relationship('ColorForType', backref='type_category', lazy=True)
    # 關聯到分析結果 (One-to-Many)
    analysis_results = db.relationship('AnalysisResult', backref='type_result', lazy=True)

    def __repr__(self):
        return f'<Type {self.name}>'