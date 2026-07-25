from extensions import db
from datetime import datetime

class ColorForType(db.Model):
    __tablename__ = 'colors_for_type'
    __table_args__ = {'comment': '色彩庫 (定義各型別適合的具體顏色)'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='顏色識別碼')
    tid = db.Column(db.Integer, db.ForeignKey('types.id'), nullable=False, comment='對應的色彩型別 ID')
    label = db.Column(db.String(50), nullable=True, comment='適合的顏色值（色碼標籤）')
    color = db.Column(db.String(30), nullable=False, comment='適合的顏色值 (HEX 或 RGB)')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, comment='建立時間戳記')
    
    def __repr__(self):
        return f'<ColorForType tid={self.tid} color={self.color}>'