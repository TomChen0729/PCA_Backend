from extensions import db
from datetime import datetime
from sqlalchemy.dialects.mysql import ENUM # 讓 SQLAlchemy 支援 MySQL 的 ENUM

class WardrobeItem(db.Model):
    __tablename__ = 'wardrobe_items'
    __table_args__ = {'comment': '衣櫥單品資料表 (儲存使用者上傳並去背的衣服)'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='單品唯一識別碼')
    uid = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='擁有此衣服的使用者 ID')
    
    # 使用 ENUM 來限制標籤只能是特定幾種
    tag = db.Column(ENUM('top', 'bottom', name='wardrobe_tags'), nullable=False, comment='衣服分類標籤')
    
    imgPath = db.Column(db.String(255), nullable=False, comment='圖片儲存路徑 (實體檔案路徑或雲端網址)')
    previewPath = db.Column(db.String(255), nullable=True, comment='衣物縮圖路徑；AI 試穿仍使用原圖')
    recycling_status = db.Column(ENUM('active', 'planned', 'recycled', name='wardrobe_recycling_status'), nullable=False, default='active', server_default='active', comment='單品狀態：衣櫥中、待回收、已回收')
    recycle_site_id = db.Column(db.String(32), nullable=True, comment='選擇的舊衣回收據點核准編號')
    recycle_district = db.Column(db.String(30), nullable=True, comment='回收據點行政區')
    recycle_address = db.Column(db.String(255), nullable=True, comment='回收據點地址')
    recycle_organization = db.Column(db.String(255), nullable=True, comment='回收據點設置團體')
    recycle_phone = db.Column(db.String(50), nullable=True, comment='回收據點聯絡電話')
    recycle_latitude = db.Column(db.Float, nullable=True, comment='回收據點緯度')
    recycle_longitude = db.Column(db.Float, nullable=True, comment='回收據點經度')
    recycling_planned_at = db.Column(db.DateTime, nullable=True, comment='安排回收時間')
    recycled_at = db.Column(db.DateTime, nullable=True, comment='使用者確認完成回收時間')
    color_1 = db.Column(db.String(30), nullable=True, comment='KMeans 抓出的主要顏色 1 (RGB)')
    color_2 = db.Column(db.String(30), nullable=True, comment='KMeans 抓出的主要顏色 2 (RGB)')
    color_3 = db.Column(db.String(30), nullable=True, comment='KMeans 抓出的主要顏色 3 (RGB)')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, comment='建立時間戳記')

    def __repr__(self):
        return f'<WardrobeItem uid={self.uid} tag={self.tag}>'
