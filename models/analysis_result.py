from extensions import db
from datetime import datetime

class AnalysisResult(db.Model):
    __tablename__ = 'analysis_results'
    __table_args__ = {'comment': 'PCA 診斷紀錄表 (儲存使用者每次的測色結果)'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='診斷紀錄唯一識別碼')
    uid = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='受測使用者 ID')
    faceImg = db.Column(db.String(255), nullable=False, comment='使用者用於分析的臉部照片路徑')
    tid = db.Column(db.Integer, db.ForeignKey('types.id'), nullable=False, comment='分析結果隸屬的色彩型別 ID')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, comment='測色時間戳記')

    def __repr__(self):
        return f'<AnalysisResult uid={self.uid} tid={self.tid}>'